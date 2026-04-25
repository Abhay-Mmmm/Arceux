import React, { useState, useEffect, useCallback } from 'react';
import { fetchAgentStatus, triggerAgentPipeline, AgentStatus } from '../services/api';
import {
    Target, ShieldAlert, BrainCircuit, GitBranch, FileText, Zap,
    Activity, Cpu, RefreshCw, Play, Clock, CheckCircle, AlertCircle, Loader2
} from 'lucide-react';
import { cn } from '../lib/utils';

const AGENT_META: Record<string, { icon: React.ElementType; description: string; shortRole: string }> = {
    'Orchestrator Agent': {
        icon: Target,
        description: 'Coordinates the incident response lifecycle and manages global incident context. Directs specialized agents and ensures no steps are skipped.',
        shortRole: 'Commander',
    },
    'Alert Handler Agent': {
        icon: ShieldAlert,
        description: 'Triages incoming signals, reduces noise, and correlates related events into a single cohesive alert narrative.',
        shortRole: 'Triage',
    },
    'Threat Analyzer Agent': {
        icon: BrainCircuit,
        description: 'Classifies behavior against MITRE ATT&CK and determines attacker intent. Maps TTPs to specific technique IDs.',
        shortRole: 'Analyst',
    },
    'Root Cause Agent': {
        icon: GitBranch,
        description: 'Reconstructs the attack timeline and identifies the initial entry point. Defines the blast radius of the incident.',
        shortRole: 'Forensics',
    },
    'Compliance Agent': {
        icon: FileText,
        description: 'Evaluates incident against GDPR, IRDAI, and SOC 2 requirements. Determines reportable incidents and deadlines.',
        shortRole: 'GRC',
    },
    'Response Automation Agent': {
        icon: Zap,
        description: 'Drafts safe, effective containment and remediation plans. Proposes actions like block IP, revoke token, or isolate host.',
        shortRole: 'SOAR',
    },
};

const STATUS_STYLES = {
    idle:      { dot: 'bg-zinc-500',   badge: 'text-zinc-400',   label: 'IDLE',      pulse: false },
    running:   { dot: 'bg-amber-400',  badge: 'text-amber-400',  label: 'RUNNING',   pulse: true  },
    completed: { dot: 'bg-green-500',  badge: 'text-green-400',  label: 'COMPLETE',  pulse: false },
    error:     { dot: 'bg-red-500',    badge: 'text-red-400',    label: 'ERROR',     pulse: false },
};

function formatRelativeTime(iso: string | null): string {
    if (!iso) return 'Never';
    const date = new Date(iso);
    if (isNaN(date.getTime())) return 'Unknown';
    const diffMs = Date.now() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
}

const AgentInsights: React.FC = () => {
    const [agents, setAgents] = useState<AgentStatus[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
    const [triggering, setTriggering] = useState(false);
    const [triggerMsg, setTriggerMsg] = useState<{ text: string; ok: boolean } | null>(null);

    const loadAgents = useCallback(async () => {
        try {
            const data = await fetchAgentStatus();
            setAgents(data);
        } catch {
            // silently keep last known state
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadAgents();
        const id = setInterval(loadAgents, 3000);
        return () => clearInterval(id);
    }, [loadAgents]);

    const handleTrigger = async () => {
        setTriggering(true);
        setTriggerMsg(null);
        try {
            const res = await triggerAgentPipeline();
            setTriggerMsg({ text: res.message, ok: res.success });
        } catch {
            setTriggerMsg({ text: 'Failed to trigger pipeline. Is the backend running?', ok: false });
        } finally {
            setTriggering(false);
            setTimeout(() => setTriggerMsg(null), 5000);
        }
    };

    const isAnyRunning = agents.some(a => a.status === 'running');
    const selected = agents.find(a => a.name === selectedAgent) ?? null;

    return (
        <div className="h-full flex flex-col gap-4 animate-fade-in overflow-hidden">
            {/* Header */}
            <div className="shrink-0 flex items-center justify-between">
                <div>
                    <h1 className="text-xl font-bold tracking-tight">Agent Architecture</h1>
                    <p className="text-muted-foreground text-xs mt-0.5">
                        Live autonomous threat processing pipeline — updates every 3 s
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    {triggerMsg && (
                        <span className={cn("text-xs font-medium", triggerMsg.ok ? "text-green-400" : "text-red-400")}>
                            {triggerMsg.text}
                        </span>
                    )}
                    <button
                        onClick={handleTrigger}
                        disabled={triggering || isAnyRunning}
                        className={cn(
                            "flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border",
                            isAnyRunning
                                ? "bg-amber-500/10 border-amber-500/30 text-amber-400 cursor-not-allowed"
                                : "bg-primary/10 border-primary/30 text-primary hover:bg-primary/20"
                        )}
                    >
                        {triggering ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : isAnyRunning ? (
                            <Activity className="h-3.5 w-3.5" />
                        ) : (
                            <Play className="h-3.5 w-3.5" />
                        )}
                        {isAnyRunning ? 'Pipeline Running…' : 'Run on Latest Alert'}
                    </button>
                </div>
            </div>

            {/* Pipeline Flow */}
            <div className="shrink-0 bg-card border border-border rounded-lg p-4 shadow-sm">
                <div className="flex justify-between items-center relative">
                    <div className="absolute top-1/2 left-0 right-0 h-px bg-border -translate-y-1/2 -z-10" />
                    {loading
                        ? Array.from({ length: 6 }).map((_, i) => (
                            <div key={i} className="flex flex-col items-center gap-2 bg-card px-4 z-10">
                                <div className="w-12 h-12 rounded-xl bg-muted animate-pulse" />
                                <div className="h-3 w-16 bg-muted rounded animate-pulse" />
                            </div>
                        ))
                        : agents.map((agent) => {
                            const meta = AGENT_META[agent.name] ?? { icon: Target, shortRole: '?' };
                            const Icon = meta.icon;
                            const style = STATUS_STYLES[agent.status] ?? STATUS_STYLES.idle;
                            const isActive = agent.status === 'running' || agent.status === 'completed';
                            return (
                                <button
                                    key={agent.name}
                                    onClick={() => setSelectedAgent(prev => prev === agent.name ? null : agent.name)}
                                    className="relative flex flex-col items-center gap-2 bg-card px-4 z-10 group"
                                >
                                    <div className={cn(
                                        "w-12 h-12 rounded-xl flex items-center justify-center border-2 shadow-sm transition-all duration-300",
                                        isActive
                                            ? "bg-background border-primary shadow-primary/20 scale-110"
                                            : "bg-muted border-border group-hover:border-primary/50"
                                    )}>
                                        <Icon className={cn("h-5 w-5", isActive ? "text-primary" : "text-muted-foreground")} />
                                    </div>
                                    <div className="text-center">
                                        <div className="font-semibold text-[10px]">{agent.name.replace(' Agent', '')}</div>
                                        <div className="text-[8px] text-muted-foreground uppercase tracking-wide font-medium">{meta.shortRole}</div>
                                    </div>
                                    {/* Status dot */}
                                    <div className={cn("absolute top-0 right-3 w-2.5 h-2.5 rounded-full border-2 border-card", style.dot)}>
                                        {style.pulse && (
                                            <span className={cn("absolute inset-0 rounded-full animate-ping opacity-75", style.dot)} />
                                        )}
                                    </div>
                                </button>
                            );
                        })
                    }
                </div>
            </div>

            {/* Detail Panel (shown when agent is selected) */}
            {selected && (
                <div className="shrink-0 bg-card border border-primary/30 rounded-lg p-4 shadow-md">
                    <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                                <span className="text-sm font-bold">{selected.name}</span>
                                <span className={cn("text-[9px] font-bold uppercase tracking-wider", STATUS_STYLES[selected.status]?.badge)}>
                                    {STATUS_STYLES[selected.status]?.label}
                                </span>
                            </div>
                            <p className="text-[11px] text-muted-foreground mb-3">{AGENT_META[selected.name]?.description}</p>
                            <div className="flex items-center gap-6 text-[10px] text-muted-foreground">
                                <span className="flex items-center gap-1"><CheckCircle className="h-3 w-3 text-green-400" /> {selected.tasks_completed} tasks</span>
                                <span className="flex items-center gap-1"><Clock className="h-3 w-3 text-primary" /> avg {selected.avg_execution_time_ms}ms</span>
                                <span className="flex items-center gap-1"><RefreshCw className="h-3 w-3" /> last: {formatRelativeTime(selected.last_run)}</span>
                            </div>
                        </div>
                        {selected.last_execution_trace.length > 0 && (
                            <div className="w-80 bg-zinc-950 rounded-lg p-2 font-mono text-[9px] text-green-400 max-h-28 overflow-y-auto">
                                {selected.last_execution_trace.map((line, i) => (
                                    <div key={i} className="leading-relaxed">{line}</div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Agent Cards Grid */}
            <div className="flex-1 min-h-0 grid grid-cols-6 gap-3">
                {loading
                    ? Array.from({ length: 6 }).map((_, i) => (
                        <div key={i} className="h-full border border-border/50 rounded-lg bg-card animate-pulse" />
                    ))
                    : agents.map((agent) => {
                        const meta = AGENT_META[agent.name] ?? { icon: Target, shortRole: '?', description: '' };
                        const Icon = meta.icon;
                        const style = STATUS_STYLES[agent.status] ?? STATUS_STYLES.idle;
                        const isSelected = selectedAgent === agent.name;

                        return (
                            <button
                                key={agent.name}
                                onClick={() => setSelectedAgent(prev => prev === agent.name ? null : agent.name)}
                                className={cn(
                                    "h-full flex flex-col border rounded-lg bg-card hover:border-primary/50 transition-all overflow-hidden shadow-sm text-left",
                                    isSelected ? "border-primary/60" : "border-border/50"
                                )}
                            >
                                {/* Card Header */}
                                <div className="shrink-0 h-14 p-3 border-b border-border/50 bg-secondary/10 flex items-center gap-2.5">
                                    <div className="h-8 w-8 shrink-0 rounded-lg bg-background border border-border flex items-center justify-center shadow-sm">
                                        <Icon className="h-4 w-4 text-primary" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider leading-none mb-1">{meta.shortRole}</div>
                                        <div className="text-[11px] font-bold truncate leading-none">{agent.name.replace(' Agent', '')}</div>
                                    </div>
                                </div>

                                {/* Status badge */}
                                <div className="shrink-0 px-3 py-2 border-b border-border/30 flex items-center gap-1.5">
                                    <div className={cn("w-1.5 h-1.5 rounded-full shrink-0", style.dot)}>
                                        {style.pulse && <span className={cn("absolute inset-0 rounded-full animate-ping opacity-75", style.dot)} />}
                                    </div>
                                    <span className={cn("text-[9px] font-bold uppercase tracking-wider", style.badge)}>{style.label}</span>
                                </div>

                                {/* Stats */}
                                <div className="shrink-0 px-3 py-2 border-b border-border/30 bg-background/50 space-y-1.5">
                                    <div className="flex items-center justify-between text-[9px] text-muted-foreground">
                                        <span className="flex items-center gap-1"><CheckCircle className="h-2.5 w-2.5 text-green-400" /> Tasks</span>
                                        <span className="font-mono text-foreground">{agent.tasks_completed}</span>
                                    </div>
                                    <div className="flex items-center justify-between text-[9px] text-muted-foreground">
                                        <span className="flex items-center gap-1"><Clock className="h-2.5 w-2.5 text-primary" /> Avg</span>
                                        <span className="font-mono text-foreground">{agent.avg_execution_time_ms}ms</span>
                                    </div>
                                    <div className="flex items-center justify-between text-[9px] text-muted-foreground">
                                        <span className="flex items-center gap-1"><RefreshCw className="h-2.5 w-2.5" /> Last</span>
                                        <span className="font-mono text-foreground">{formatRelativeTime(agent.last_run)}</span>
                                    </div>
                                </div>

                                {/* Terminal — last trace */}
                                <div className="flex-1 min-h-0 flex flex-col bg-zinc-950/95">
                                    <div className="flex items-center gap-1 px-2 py-1 border-b border-white/10 bg-white/5">
                                        <div className="flex gap-1">
                                            <div className="w-2 h-2 rounded-full bg-red-500/80" />
                                            <div className="w-2 h-2 rounded-full bg-yellow-500/80" />
                                            <div className="w-2 h-2 rounded-full bg-green-500/80" />
                                        </div>
                                        <div className="ml-2 text-[8px] font-mono text-zinc-400">output.log</div>
                                    </div>
                                    <div className="flex-1 p-2 font-mono text-[8px] text-green-400 overflow-y-auto">
                                        {agent.last_execution_trace.length > 0 ? (
                                            agent.last_execution_trace.slice(0, 6).map((line, i) => (
                                                <div key={i} className="leading-relaxed opacity-90">{line}</div>
                                            ))
                                        ) : agent.status === 'running' ? (
                                            <>
                                                <div className="text-zinc-500 mb-1">[INFO] Processing signal...</div>
                                                <div className="text-amber-400 flex items-center gap-1">
                                                    <span>Executing</span>
                                                    <span className="animate-pulse">...</span>
                                                </div>
                                            </>
                                        ) : (
                                            <>
                                                <div className="text-zinc-500 mb-1">[INFO] Waiting for signal</div>
                                                <div className="text-zinc-600">No trace yet — trigger pipeline to see output</div>
                                            </>
                                        )}
                                        {agent.status === 'running' && (
                                            <span className="inline-block w-1.5 h-3 bg-amber-400 ml-0.5 align-middle animate-pulse" />
                                        )}
                                    </div>
                                </div>

                                {/* Bottom metric */}
                                <div className="shrink-0 h-10 border-t border-border/30 bg-muted/20 px-3 flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <Cpu className="h-3 w-3 text-muted-foreground" />
                                        <div className="h-1.5 w-14 bg-muted rounded-full overflow-hidden">
                                            <div
                                                className={cn("h-full rounded-full transition-all", agent.status === 'running' ? 'bg-amber-400' : 'bg-primary/70')}
                                                style={{ width: agent.status === 'idle' ? '5%' : agent.status === 'running' ? '80%' : '40%' }}
                                            />
                                        </div>
                                    </div>
                                    <div className="text-[9px] font-mono text-muted-foreground">
                                        {agent.execution_count > 0 ? `${agent.execution_count} runs` : 'idle'}
                                    </div>
                                </div>
                            </button>
                        );
                    })
                }
            </div>
        </div>
    );
};

export default AgentInsights;
