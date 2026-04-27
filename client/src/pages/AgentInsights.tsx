import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { fetchAgentStatus, AgentStatus } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';
import {
    Target, ShieldAlert, BrainCircuit, GitBranch, FileText, Zap,
    Cpu, RefreshCw, Clock, CheckCircle, WifiOff,
} from 'lucide-react';
import { cn } from '../lib/utils';

// ─── Static metadata ──────────────────────────────────────────────────────────

const AGENT_META: Record<string, { icon: React.ElementType; shortRole: string; description: string }> = {
    'Orchestrator Agent': {
        icon: Target,
        shortRole: 'Commander',
        description: 'Coordinates the incident response lifecycle and manages global incident context. Directs specialized agents and ensures no steps are skipped.',
    },
    'Alert Handler Agent': {
        icon: ShieldAlert,
        shortRole: 'Triage',
        description: 'Triages incoming signals, reduces noise, and correlates related events into a single cohesive alert narrative.',
    },
    'Threat Analyzer Agent': {
        icon: BrainCircuit,
        shortRole: 'Analyst',
        description: 'Classifies behavior against MITRE ATT&CK and determines attacker intent. Maps TTPs to specific technique IDs.',
    },
    'Root Cause Agent': {
        icon: GitBranch,
        shortRole: 'Forensics',
        description: 'Reconstructs the attack timeline and identifies the initial entry point. Defines the blast radius of the incident.',
    },
    'Compliance Agent': {
        icon: FileText,
        shortRole: 'GRC',
        description: 'Evaluates incident against GDPR, IRDAI, and SOC 2 requirements. Determines reportable incidents and deadlines.',
    },
    'Response Automation Agent': {
        icon: Zap,
        shortRole: 'SOAR',
        description: 'Drafts safe, effective containment and remediation plans. Proposes actions like block IP, revoke token, or isolate host.',
    },
};

// Stable status config — defined outside component so it's never recreated
const STATUS_CFG = {
    idle:      { dot: 'bg-zinc-600',    text: 'text-zinc-500',      badgeBg: 'bg-zinc-800/60',    label: 'IDLE',    pulse: false },
    running:   { dot: 'bg-amber-400',   text: 'text-amber-300',     badgeBg: 'bg-amber-400/10',   label: 'RUNNING', pulse: true  },
    completed: { dot: 'bg-emerald-500', text: 'text-emerald-400',   badgeBg: 'bg-emerald-500/10', label: 'DONE',    pulse: false },
    error:     { dot: 'bg-red-400',     text: 'text-red-400/80',    badgeBg: 'bg-red-500/10',     label: 'FAILED',  pulse: false },
} as const;

type AgentStatusKey = keyof typeof STATUS_CFG;

// Structural comparator for agent lists — avoids JSON.stringify on the whole
// object, which can break on reordered keys or non-JSON-safe values.
// Only compares the fields that are actually rendered.
function compareAgentLists(prev: AgentStatus[], next: AgentStatus[]): boolean {
    if (prev.length !== next.length) return false;
    for (let i = 0; i < prev.length; i++) {
        const p = prev[i], n = next[i];
        if (
            p.name !== n.name ||
            p.status !== n.status ||
            p.last_run !== n.last_run ||
            p.tasks_completed !== n.tasks_completed ||
            p.execution_count !== n.execution_count ||
            p.avg_execution_time_ms !== n.avg_execution_time_ms ||
            JSON.stringify(p.last_execution_trace) !== JSON.stringify(n.last_execution_trace)
        ) return false;
    }
    return true;
}

function formatRelativeTime(iso: string | null): string {
    if (!iso) return '—';
    const date = new Date(iso);
    if (isNaN(date.getTime())) return '—';
    const diffMins = Math.floor((Date.now() - date.getTime()) / 60000);
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    return `${Math.floor(diffMins / 60)}h ago`;
}

// ─── Memoized card — only re-renders when its own agent data changes ──────────

interface AgentCardProps {
    agent: AgentStatus;
    isSelected: boolean;
    onSelect: (name: string) => void;
}

const AgentCard = React.memo(function AgentCard({ agent, isSelected, onSelect }: AgentCardProps) {
    const meta = AGENT_META[agent.name] ?? { icon: Target, shortRole: '?', description: '' };
    const Icon = meta.icon;
    const cfg = STATUS_CFG[agent.status as AgentStatusKey] ?? STATUS_CFG.idle;

    return (
        <button
            onClick={() => onSelect(agent.name)}
            className={cn(
                'h-full flex flex-col rounded-lg bg-card border overflow-hidden shadow-sm text-left',
                isSelected ? 'border-primary/50' : 'border-border/40 hover:border-border/70',
            )}
        >
            {/* Header */}
            <div className="shrink-0 p-3 border-b border-border/40 flex items-center gap-2.5">
                <div className="h-8 w-8 shrink-0 rounded-lg bg-background border border-border/60 flex items-center justify-center">
                    <Icon className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="flex-1 min-w-0">
                    <div className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider leading-none mb-0.5">
                        {meta.shortRole}
                    </div>
                    <div className="text-[11px] font-bold truncate leading-none">
                        {agent.name.replace(' Agent', '')}
                    </div>
                </div>
                {/* Status dot — isolated in its own element so ping doesn't affect layout */}
                <div className="relative shrink-0 w-2.5 h-2.5">
                    <div className={cn('w-2.5 h-2.5 rounded-full', cfg.dot)} />
                    {cfg.pulse && (
                        <div className={cn('absolute inset-0 rounded-full animate-ping opacity-40', cfg.dot)} />
                    )}
                </div>
            </div>

            {/* Status badge */}
            <div className={cn('shrink-0 px-3 py-1.5 border-b border-border/30', cfg.badgeBg)}>
                <span className={cn('text-[9px] font-bold uppercase tracking-widest', cfg.text)}>
                    {cfg.label}
                </span>
            </div>

            {/* Stats */}
            <div className="shrink-0 px-3 py-2 space-y-1.5">
                <div className="flex items-center justify-between text-[9px] text-muted-foreground">
                    <span className="flex items-center gap-1">
                        <CheckCircle className="h-2.5 w-2.5 text-emerald-500/70" /> Tasks
                    </span>
                    <span className="font-mono text-foreground/80">{agent.tasks_completed}</span>
                </div>
                <div className="flex items-center justify-between text-[9px] text-muted-foreground">
                    <span className="flex items-center gap-1">
                        <Clock className="h-2.5 w-2.5 text-primary/60" /> Avg
                    </span>
                    <span className="font-mono text-foreground/80">{agent.avg_execution_time_ms}ms</span>
                </div>
                <div className="flex items-center justify-between text-[9px] text-muted-foreground">
                    <span className="flex items-center gap-1">
                        <RefreshCw className="h-2.5 w-2.5" /> Last
                    </span>
                    <span className="font-mono text-foreground/80">{formatRelativeTime(agent.last_run)}</span>
                </div>
            </div>

            {/* Terminal */}
            <div className="flex-1 min-h-0 flex flex-col bg-zinc-950/90 border-t border-border/30">
                <div className="flex items-center gap-1 px-2 py-1 border-b border-white/5 bg-white/[0.02]">
                    <div className="flex gap-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-red-500/50" />
                        <div className="w-1.5 h-1.5 rounded-full bg-yellow-500/50" />
                        <div className="w-1.5 h-1.5 rounded-full bg-green-500/50" />
                    </div>
                    <span className="ml-1 text-[8px] font-mono text-zinc-500">output.log</span>
                </div>
                <div className="flex-1 p-2 font-mono text-[8px] overflow-hidden">
                    {agent.last_execution_trace.length > 0 ? (
                        agent.last_execution_trace.slice(0, 5).map((line, i) => (
                            <div key={i} className="leading-relaxed text-green-400/75 truncate">{line}</div>
                        ))
                    ) : agent.status === 'running' ? (
                        <div className="text-amber-400/60">Processing signal…</div>
                    ) : (
                        <div className="text-zinc-600">Awaiting signal</div>
                    )}
                </div>
            </div>

            {/* Footer */}
            <div className="shrink-0 px-3 py-2 border-t border-border/30 bg-muted/10 flex items-center justify-between">
                <span className="text-[9px] font-mono text-muted-foreground">
                    {agent.execution_count > 0 ? `${agent.execution_count}× run` : 'no runs'}
                </span>
                <div className="flex items-center gap-1.5">
                    <Cpu className="h-2.5 w-2.5 text-muted-foreground/40" />
                    <div className="h-1 w-10 rounded-full bg-muted/50 overflow-hidden">
                        <div
                            className={cn(
                                'h-full rounded-full',
                                agent.status === 'running'   ? 'bg-amber-400' :
                                agent.status === 'completed' ? 'bg-emerald-500' :
                                agent.status === 'error'     ? 'bg-red-400/70' :
                                'bg-zinc-600',
                            )}
                            style={{
                                width: agent.status === 'idle'    ? '5%' :
                                       agent.status === 'running' ? '75%' : '40%',
                            }}
                        />
                    </div>
                </div>
            </div>
        </button>
    );
});

// ─── Memoized pipeline node ───────────────────────────────────────────────────

interface PipelineNodeProps {
    agent: AgentStatus;
    isSelected: boolean;
    onSelect: (name: string) => void;
}

const PipelineNode = React.memo(function PipelineNode({ agent, isSelected, onSelect }: PipelineNodeProps) {
    const meta = AGENT_META[agent.name] ?? { icon: Target, shortRole: '?' };
    const Icon = meta.icon;
    const cfg = STATUS_CFG[agent.status as AgentStatusKey] ?? STATUS_CFG.idle;
    const isActive = agent.status === 'running' || agent.status === 'completed';
    const isRunning = agent.status === 'running';

    return (
        <button
            onClick={() => onSelect(agent.name)}
            className="relative flex flex-col items-center gap-2 bg-card px-4 z-10 group"
        >
            <div className={cn(
                'w-12 h-12 rounded-xl flex items-center justify-center border-2 shadow-sm',
                isSelected   ? 'bg-background border-primary scale-110 shadow-primary/20' :
                isActive     ? 'bg-background border-primary/50' :
                agent.status === 'error' ? 'bg-red-950/30 border-red-500/30' :
                'bg-muted border-border group-hover:border-border/80',
            )}>
                <Icon className={cn(
                    'h-5 w-5',
                    isRunning           ? 'text-amber-400' :
                    agent.status === 'completed' ? 'text-emerald-400' :
                    agent.status === 'error'     ? 'text-red-400/70' :
                    'text-muted-foreground',
                )} />
            </div>
            <div className="text-center">
                <div className="font-semibold text-[10px] leading-none">
                    {agent.name.replace(' Agent', '')}
                </div>
                <div className="text-[8px] text-muted-foreground uppercase tracking-wide mt-0.5">
                    {meta.shortRole}
                </div>
            </div>
            {/* Status dot */}
            <div className="absolute top-0 right-3">
                <div className={cn('w-2.5 h-2.5 rounded-full border-2 border-card', cfg.dot)} />
                {cfg.pulse && (
                    <div className={cn('absolute inset-0 rounded-full animate-ping opacity-40', cfg.dot)} />
                )}
            </div>
        </button>
    );
});

// ─── Main page ────────────────────────────────────────────────────────────────

const AgentInsights: React.FC = () => {
    const [agents, setAgents] = useState<AgentStatus[]>([]);
    const [lastSignalType, setLastSignalType] = useState<string | null>(null);
    const [initialLoading, setInitialLoading] = useState(true);
    const [hardError, setHardError] = useState<string | null>(null);
    const [pollFailed, setPollFailed] = useState(false);
    const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

    const everLoadedRef = useRef(false);

    // WebSocket push — agent states and pipeline events arrive instantly
    const { connected: wsConnected } = useWebSocket<{ agents: AgentStatus[]; last_signal_type: string | null }>(
        'agent_status_updated',
        (msg) => {
            setAgents(prev => compareAgentLists(prev, msg.agents) ? prev : msg.agents);
            setLastSignalType(msg.last_signal_type);
            everLoadedRef.current = true;
            setPollFailed(false);
        }
    );

    useWebSocket<{ signal_type: string; agents_ran: number; elapsed_ms: number }>(
        'pipeline_completed',
        (msg) => setLastSignalType(msg.signal_type)
    );

    const loadAgents = useCallback(async () => {
        try {
            const data = await fetchAgentStatus();
            // Only update state when rendered fields actually changed — prevents re-render flicker
            setAgents(prev => compareAgentLists(prev, data.agents) ? prev : data.agents);
            setLastSignalType(data.last_signal_type);
            everLoadedRef.current = true;
            setPollFailed(false);
        } catch (err) {
            setPollFailed(true);
            // Only surface a hard error when we have no data to show
            if (!everLoadedRef.current) {
                setHardError(err instanceof Error ? err.message : 'Cannot reach backend');
            }
        } finally {
            setInitialLoading(false);
        }
    }, []); // Stable reference — never recreated

    useEffect(() => {
        loadAgents();
        const id = setInterval(loadAgents, 15000);
        return () => clearInterval(id);
    }, [loadAgents]);

    const selected = useMemo(() => agents.find(a => a.name === selectedAgent) ?? null, [agents, selectedAgent]);

    const handleSelectAgent = useCallback((name: string) => {
        setSelectedAgent(prev => (prev === name ? null : name));
    }, []);

    // Derive pipeline activity state from current agent states
    type ActivityState =
        | { kind: 'idle' }
        | { kind: 'active'; agentName: string }
        | { kind: 'completed'; secondsAgo: number; agentsRan: number }
        | { kind: 'error'; agentName: string };

    const pipelineActivity = useMemo((): ActivityState => {
        const runningAgent = agents.find(a => a.status === 'running');
        if (runningAgent) return { kind: 'active', agentName: runningAgent.name };

        const errorAgent = agents.find(a => a.status === 'error');
        if (errorAgent) return { kind: 'error', agentName: errorAgent.name };

        const now = Date.now();
        const recentAgent = agents
            .filter(a => a.last_run !== null)
            .sort((a, b) => new Date(b.last_run!).getTime() - new Date(a.last_run!).getTime())[0];

        if (recentAgent && recentAgent.last_run) {
            const secondsAgo = Math.floor((now - new Date(recentAgent.last_run).getTime()) / 1000);
            if (secondsAgo < 30) {
                const agentsRan = agents.filter(a => a.status === 'completed').length;
                return { kind: 'completed', secondsAgo, agentsRan };
            }
        }

        return { kind: 'idle' };
    }, [agents]);

    // ── Skeleton (first load only) ──────────────────────────────────────────
    if (initialLoading) {
        return (
            <div className="h-full flex flex-col gap-4">
                <div className="shrink-0 h-8 w-48 bg-muted rounded animate-pulse" />
                <div className="shrink-0 h-8 bg-card border border-border/50 rounded-lg animate-pulse" />
                <div className="shrink-0 bg-card border border-border rounded-lg p-4 h-24 animate-pulse" />
                <div className="flex-1 grid grid-cols-6 gap-3">
                    {Array.from({ length: 6 }).map((_, i) => (
                        <div key={i} className="h-full border border-border/50 rounded-lg bg-card animate-pulse" />
                    ))}
                </div>
            </div>
        );
    }

    // ── Hard error (backend never responded) ────────────────────────────────
    if (hardError) {
        return (
            <div className="h-full flex items-center justify-center">
                <div className="text-center space-y-3">
                    <p className="text-sm text-red-400">{hardError}</p>
                    <p className="text-xs text-muted-foreground">Make sure the backend is running on port 8000</p>
                    <button
                        onClick={loadAgents}
                        className="text-xs text-primary hover:underline"
                    >
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    // ── Normal render ───────────────────────────────────────────────────────
    return (
        <div className="h-full flex flex-col gap-4 overflow-hidden">

            {/* Header */}
            <div className="shrink-0 flex items-center justify-between">
                <div>
                    <h1 className="text-xl font-bold tracking-tight">Agent Architecture</h1>
                    <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1.5">
                        Autonomous threat processing pipeline — 15 s polling
                        <span className="flex items-center gap-1">
                            <span className={wsConnected ? 'text-green-500' : 'text-yellow-500'}>●</span>
                            {wsConnected ? 'Live' : 'Reconnecting…'}
                        </span>
                        {pollFailed && (
                            <span className="flex items-center gap-1 text-red-400/60">
                                <WifiOff className="h-2.5 w-2.5" /> backend unreachable
                            </span>
                        )}
                    </p>
                </div>
            </div>

            {/* Activity bar */}
            <div className="shrink-0 flex items-center gap-2.5 px-3 py-2 rounded-lg bg-card border border-border/50 text-xs">
                {pipelineActivity.kind === 'active' && (
                    <>
                        <span className="relative flex h-2 w-2 shrink-0">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-60" />
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-400" />
                        </span>
                        <span className="text-amber-300 font-medium">Pipeline active</span>
                        {lastSignalType && (
                            <span className="text-muted-foreground">
                                — {lastSignalType.replace(/_/g, ' ')} signal
                            </span>
                        )}
                        <span className="text-muted-foreground">
                            — {pipelineActivity.agentName} is analyzing…
                        </span>
                    </>
                )}
                {pipelineActivity.kind === 'completed' && (
                    <>
                        <span className="text-emerald-500 shrink-0">✓</span>
                        <span className="text-emerald-400 font-medium">
                            Last run completed {pipelineActivity.secondsAgo}s ago
                        </span>
                        {lastSignalType && (
                            <span className="text-muted-foreground">
                                — {lastSignalType.replace(/_/g, ' ')}
                            </span>
                        )}
                        <span className="text-muted-foreground">
                            — {pipelineActivity.agentsRan} agent{pipelineActivity.agentsRan !== 1 ? 's' : ''} ran
                        </span>
                    </>
                )}
                {pipelineActivity.kind === 'error' && (
                    <>
                        <span className="text-red-400 shrink-0">✗</span>
                        <span className="text-red-400 font-medium">Last run encountered an error</span>
                        <span className="text-muted-foreground">— {pipelineActivity.agentName} failed</span>
                    </>
                )}
                {pipelineActivity.kind === 'idle' && (
                    <>
                        <span className="h-2 w-2 rounded-full bg-zinc-500 shrink-0" />
                        <span className="text-zinc-500">Pipeline idle — waiting for next signal</span>
                    </>
                )}
            </div>

            {/* Pipeline flow */}
            <div className="shrink-0 bg-card border border-border rounded-lg p-4 shadow-sm">
                <div className="flex justify-between items-center relative">
                    <div className="absolute top-1/2 left-0 right-0 h-px bg-border -translate-y-1/2 -z-10" />
                    {agents.map(agent => (
                        <PipelineNode
                            key={agent.name}
                            agent={agent}
                            isSelected={selectedAgent === agent.name}
                            onSelect={handleSelectAgent}
                        />
                    ))}
                </div>
            </div>

            {/* Detail panel */}
            {selected && (
                <div className="shrink-0 bg-card border border-primary/20 rounded-lg p-4 shadow-sm">
                    <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                                <span className="text-sm font-bold">{selected.name}</span>
                                <span className={cn(
                                    'text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded',
                                    STATUS_CFG[selected.status as AgentStatusKey]?.badgeBg,
                                    STATUS_CFG[selected.status as AgentStatusKey]?.text,
                                )}>
                                    {STATUS_CFG[selected.status as AgentStatusKey]?.label}
                                </span>
                            </div>
                            <p className="text-[11px] text-muted-foreground mb-3">
                                {AGENT_META[selected.name]?.description}
                            </p>
                            <div className="flex items-center gap-6 text-[10px] text-muted-foreground">
                                <span className="flex items-center gap-1">
                                    <CheckCircle className="h-3 w-3 text-emerald-400" />
                                    {selected.tasks_completed} tasks
                                </span>
                                <span className="flex items-center gap-1">
                                    <Clock className="h-3 w-3 text-primary/70" />
                                    avg {selected.avg_execution_time_ms}ms
                                </span>
                                <span className="flex items-center gap-1">
                                    <RefreshCw className="h-3 w-3" />
                                    last: {formatRelativeTime(selected.last_run)}
                                </span>
                            </div>
                        </div>
                        {selected.last_execution_trace.length > 0 && (
                            <div className="w-80 shrink-0 bg-zinc-950 rounded-lg p-2 font-mono text-[9px] text-green-400/80 max-h-28 overflow-y-auto">
                                {selected.last_execution_trace.map((line, i) => (
                                    <div key={i} className="leading-relaxed">{line}</div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Agent cards grid */}
            <div className="flex-1 min-h-0 grid grid-cols-6 gap-3">
                {agents.map(agent => (
                    <AgentCard
                        key={agent.name}
                        agent={agent}
                        isSelected={selectedAgent === agent.name}
                        onSelect={handleSelectAgent}
                    />
                ))}
            </div>
        </div>
    );
};

export default AgentInsights;
