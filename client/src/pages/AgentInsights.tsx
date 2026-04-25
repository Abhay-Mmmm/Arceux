import React from 'react';
import { MOCK_AGENTS } from '../data/mock';
import { Database, ShieldAlert, BrainCircuit, FileText, UserCog, Activity, Cpu } from 'lucide-react';
import { cn } from '../lib/utils';

const AGENT_ICONS = {
    'agt-1': Database,
    'agt-2': ShieldAlert,
    'agt-3': BrainCircuit,
    'agt-4': FileText,
    'agt-5': UserCog,
};

const AgentInsights: React.FC = () => {
    return (
        <div className="h-full flex flex-col gap-4 animate-fade-in overflow-hidden">
            {/* Header - Compact */}
            <div className="shrink-0 flex items-center justify-between">
                <div>
                    <h1 className="text-xl font-bold tracking-tight">Agent Architecture</h1>
                    <p className="text-muted-foreground text-xs mt-0.5">Visualize the autonomous threat processing pipeline</p>
                </div>
            </div>

            {/* Flow Visualization - Compact */}
            <div className="shrink-0 bg-card border border-border rounded-lg p-4 shadow-sm">
                <div className="flex justify-between items-center relative max-w-full">
                    {/* Connection Line */}
                    <div className="absolute top-1/2 left-0 right-0 h-px bg-border -translate-y-1/2 -z-10"></div>

                    {MOCK_AGENTS.map((agent) => {
                        const Icon = AGENT_ICONS[agent.id as keyof typeof AGENT_ICONS] || Database;
                        return (
                            <div key={agent.id} className="relative flex flex-col items-center gap-2 bg-card px-4 z-10">
                                <div className={cn(
                                    "w-12 h-12 rounded-xl flex items-center justify-center border-2 shadow-sm transition-all duration-300",
                                    agent.status === 'active' ? "bg-background border-primary shadow-primary/20 scale-110" : "bg-muted border-border"
                                )}>
                                    <Icon className={cn("h-5 w-5", agent.status === 'active' ? "text-primary" : "text-muted-foreground")} />
                                </div>
                                <div className="text-center">
                                    <div className="font-semibold text-[10px]">{agent.name}</div>
                                    <div className="text-[8px] text-muted-foreground uppercase tracking-wide font-medium">{agent.role.split(' ')[0]}</div>
                                </div>
                                {/* Status Dot */}
                                <div className={cn(
                                    "absolute top-0 right-3 w-2.5 h-2.5 rounded-full border-2 border-card",
                                    agent.status === 'active' ? "bg-green-500" : "bg-zinc-500"
                                )}>
                                    {agent.status === 'active' && <span className="absolute inset-0 rounded-full bg-green-500 animate-ping opacity-75"></span>}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Agent Details Grid - Fill Remaining Space */}
            <div className="flex-1 min-h-0 grid grid-cols-5 gap-3">
                {MOCK_AGENTS.map((agent) => {
                    const Icon = AGENT_ICONS[agent.id as keyof typeof AGENT_ICONS] || Database;
                    return (
                        <div key={agent.id} className="h-full flex flex-col border border-border/50 rounded-lg bg-card hover:border-primary/50 transition-all overflow-hidden shadow-sm">
                            {/* Header - Fixed Height */}
                            <div className="shrink-0 h-14 p-3 border-b border-border/50 bg-secondary/10 flex items-center gap-2.5">
                                <div className="h-8 w-8 shrink-0 rounded-lg bg-background border border-border flex items-center justify-center shadow-sm">
                                    <Icon className="h-4 w-4 text-primary" />
                                </div>
                                <div className="flex-1 min-w-0 flex flex-col justify-center">
                                    <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider leading-none mb-1">{agent.role}</div>
                                    <div className="text-xs font-bold truncate leading-none">{agent.name}</div>
                                </div>
                            </div>

                            {/* Description - Fixed Height */}
                            <div className="shrink-0 h-16 px-3 py-2 border-b border-border/30">
                                <p className="text-[10px] text-muted-foreground leading-relaxed line-clamp-3">
                                    {agent.description}
                                </p>
                            </div>

                            {/* Recent Decisions - Fixed Height */}
                            <div className="shrink-0 h-24 px-3 py-2 border-b border-border/30 bg-background/50">
                                <div className="text-[9px] uppercase font-bold text-muted-foreground mb-1.5 flex items-center gap-1">
                                    <Activity className="h-3 w-3 text-primary" /> Recent Activity
                                </div>
                                <div className="space-y-1">
                                    {agent.decisions.slice(0, 3).map((decision, i) => (
                                        <div key={i} className="flex items-start gap-1.5 text-[9px] text-foreground/90">
                                            <div className="w-1 h-1 rounded-full bg-primary shrink-0 mt-1"></div>
                                            <span className="leading-snug line-clamp-1">{decision}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Terminal Output - Flexible Fill */}
                            <div className="flex-1 min-h-0 p-1 flex flex-col bg-zinc-950/95">
                                {/* Fake Tabs */}
                                <div className="flex items-center gap-1 px-2 py-1 border-b border-white/10 bg-white/5">
                                    <div className="flex gap-1">
                                        <div className="w-2 h-2 rounded-full bg-red-500/80"></div>
                                        <div className="w-2 h-2 rounded-full bg-yellow-500/80"></div>
                                        <div className="w-2 h-2 rounded-full bg-green-500/80"></div>
                                    </div>
                                    <div className="ml-2 text-[8px] font-mono text-zinc-400">output.log</div>
                                </div>
                                <div className="flex-1 p-2 font-mono text-[9px] text-green-400 overflow-y-auto">
                                    <div className="opacity-50 text-xs mb-1">
                                        <span className="text-blue-400">~</span> <span className="text-zinc-500">$</span> ./start_process.sh
                                    </div>
                                    <div className="mb-2">
                                        <span className="text-zinc-500">[INFO]</span> Initializing modules... <span className="text-green-500">OK</span><br />
                                        <span className="text-zinc-500">[INFO]</span> Loading checkpoints...
                                    </div>

                                    <div className="opacity-90">
                                        <span className="text-zinc-500">$</span> {agent.exampleOutput}
                                        <span className="animate-pulse inline-block w-1.5 h-3 bg-green-400 ml-1 align-middle"></span>
                                    </div>
                                </div>
                            </div>

                            {/* Bottom Metric Fill */}
                            <div className="shrink-0 h-10 border-t border-border/30 bg-muted/20 px-3 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Cpu className="h-3 w-3 text-muted-foreground" />
                                    <div className="h-1.5 w-16 bg-muted rounded-full overflow-hidden">
                                        <div className="h-full bg-primary/70" style={{ width: `${Math.floor(Math.random() * 40) + 40}%` }}></div>
                                    </div>
                                </div>
                                <div className="text-[9px] font-mono text-muted-foreground">
                                    {Math.floor(Math.random() * 300) + 50}MB
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default AgentInsights;
