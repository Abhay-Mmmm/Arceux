import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { MOCK_COMPLIANCE } from '../data/mock';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Cell } from 'recharts';
import { ArrowRight, Send, Loader2, CheckCircle2, AlertTriangle, Shield } from 'lucide-react';
import { Modal } from '../components/ui/Modal';
import { Alert } from '../types';
import { cn } from '../lib/utils';
import { fetchRealtimeMetrics, RealtimeComponent, fetchAlerts } from '../services/api';

// Dynamic Heartbeat Visualization - generates SVG path from history data
const HeartbeatLine = ({ color, history }: { color: string; history?: number[] }) => {
    // Generate SVG path from history data
    const pathData = useMemo(() => {
        if (!history || history.length === 0) {
            // Default static pulse if no data
            return "M0 12 H20 L30 3 L40 21 L50 12 H60 L70 6 L80 18 L90 12 H120 L130 1 L140 23 L150 12 H300";
        }

        // Normalize history values to SVG Y coordinates (0-24 range)
        const minVal = Math.min(...history);
        const maxVal = Math.max(...history);
        const range = maxVal - minVal || 1;

        // Map each history point to Y coordinate (inverted: higher value = lower Y)
        const points = history.map((val, i) => {
            const normalizedY = 2 + ((val - minVal) / range) * 20; // Y between 2-22
            const x = (i / (history.length - 1)) * 300; // X spreads across 0-300
            return { x, y: normalizedY };
        });

        // Create smooth SVG path with interpolation
        let path = `M0 ${points[0]?.y || 12}`;

        for (let i = 0; i < points.length; i++) {
            const curr = points[i];
            const next = points[i + 1];

            if (next) {
                // Add some heartbeat spikes between data points
                const midX = (curr.x + next.x) / 2;
                const spikeAmplitude = Math.abs(next.y - curr.y) * 0.8;
                const spikeDir = Math.random() > 0.5 ? 1 : -1;

                path += ` L${curr.x} ${curr.y}`;
                path += ` L${midX - 5} ${12 - spikeAmplitude * spikeDir}`;
                path += ` L${midX + 5} ${12 + spikeAmplitude * spikeDir}`;
            } else {
                path += ` L${curr.x} ${curr.y}`;
            }
        }

        path += ` L300 ${points[points.length - 1]?.y || 12}`;

        return path;
    }, [history]);

    return (
        <div className="relative w-full h-full overflow-hidden">
            <svg viewBox="0 0 300 24" className="w-full h-full" preserveAspectRatio="none">
                {/* Background Grid Line */}
                <path d="M0 12 H300" stroke={color} strokeOpacity="0.1" strokeWidth="1" />

                {/* Dynamic Pulse */}
                <path
                    d={pathData}
                    fill="none"
                    stroke={color}
                    strokeWidth="2"
                    vectorEffect="non-scaling-stroke"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="transition-all duration-500"
                />

                {/* Gradient Overlay for Fade Effect */}
                <defs>
                    <linearGradient id="fade" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="transparent" />
                        <stop offset="10%" stopColor="white" />
                        <stop offset="90%" stopColor="white" />
                        <stop offset="100%" stopColor="transparent" />
                    </linearGradient>
                </defs>
            </svg>
        </div>
    );
};

const SEVERITY_DATA = [
    { name: 'Crit', value: 2, color: 'hsl(0 84% 60%)' },
    { name: 'High', value: 5, color: 'hsl(25 95% 53%)' },
    { name: 'Med', value: 12, color: 'hsl(48 96% 53%)' },
    { name: 'Low', value: 24, color: 'hsl(217 91% 60%)' },
];

const Dashboard: React.FC = () => {
    const [chatInput, setChatInput] = useState('');
    const [messages, setMessages] = useState<{ role: 'user' | 'ai', content: React.ReactNode }[]>([
        { role: 'ai', content: <>Checking system logs... Detected anomalous root access attempt on <strong>db-shard-04</strong>. Suggest immediate isolation.</> }
    ]);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [showSystemCheck, setShowSystemCheck] = useState(false);
    const [checkProgress, setCheckProgress] = useState(0);
    const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
    const [selectedServiceId, setSelectedServiceId] = useState<string | null>(null);

    // Real-time system components from backend
    const [realtimeComponents, setRealtimeComponents] = useState<RealtimeComponent[]>([]);
    const [isLive, setIsLive] = useState(false);

    // Live high-priority alerts
    const [liveAlerts, setLiveAlerts] = useState<Alert[]>([]);
    const [alertsLoading, setAlertsLoading] = useState(true);

    // Derive active service from real-time data
    const selectedService = useMemo(() =>
        realtimeComponents.find(c => c.id === selectedServiceId) || null,
        [realtimeComponents, selectedServiceId]);

    // Poll real-time metrics from backend
    useEffect(() => {
        let isMounted = true;

        const pollMetrics = async () => {
            try {
                const data = await fetchRealtimeMetrics();
                if (isMounted) {
                    setRealtimeComponents(data.components);
                    setIsLive(true);
                }
            } catch (err) {
                console.warn('Failed to fetch realtime metrics, using mock data');
                setIsLive(false);
            }
        };

        // Initial fetch
        pollMetrics();

        // Poll every 2 seconds for real-time updates
        const interval = setInterval(pollMetrics, 2000);

        return () => {
            isMounted = false;
            clearInterval(interval);
        };
    }, []);

    // Poll high-priority alerts from backend
    useEffect(() => {
        let isMounted = true;

        const pollAlerts = async () => {
            try {
                // Fetch only high and critical alerts
                const allAlerts = await fetchAlerts({ limit: 50 });
                if (isMounted) {
                    const highPriority = allAlerts.filter(a => ['critical', 'high'].includes(a.severity));
                    setLiveAlerts(highPriority);
                    setAlertsLoading(false);
                }
            } catch (err) {
                console.warn('Failed to fetch alerts, using mock data');
                setAlertsLoading(false);
            }
        };

        // Initial fetch
        pollAlerts();

        // Poll every 5 seconds for new alerts
        const interval = setInterval(pollAlerts, 5000);

        return () => {
            isMounted = false;
            clearInterval(interval);
        };
    }, []);

    const handleRefresh = useCallback(() => {
        setIsRefreshing(true);
        setTimeout(() => setIsRefreshing(false), 1500);
    }, []);

    const handleSystemCheck = () => {
        setShowSystemCheck(true);
        setCheckProgress(0);
        const interval = setInterval(() => {
            setCheckProgress(prev => {
                if (prev >= 100) {
                    clearInterval(interval);
                    return 100;
                }
                return prev + 10;
            });
        }, 200);
    };

    const handleSendMessage = async () => {
        if (!chatInput.trim()) return;
        const userMessage = chatInput;
        setMessages(prev => [...prev, { role: 'user' as const, content: userMessage }]);
        setChatInput('');

        // Show loading state
        setMessages(prev => [...prev, {
            role: 'ai',
            content: <>Thinking<Loader2 className="h-3 w-3 animate-spin inline ml-1" />...</>
        }]);

        try {
            const response = await fetch('http://localhost:8000/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userMessage })
            });

            const data = await response.json();

            // Add 1 second delay for realistic feel
            await new Promise(resolve => setTimeout(resolve, 1000));

            // Replace loading message with actual response
            setMessages(prev => {
                const msgs = [...prev];
                msgs[msgs.length - 1] = { role: 'ai', content: data.response };
                return msgs;
            });
        } catch (error) {
            console.error('Chat error:', error);
            await new Promise(resolve => setTimeout(resolve, 1000));
            setMessages(prev => {
                const msgs = [...prev];
                msgs[msgs.length - 1] = {
                    role: 'ai',
                    content: 'Sorry, I couldn\'t connect to the backend. Please check the API is running.'
                };
                return msgs;
            });
        }
    };

    const handleQuickAction = async (action: string) => {
        // Show loading
        setMessages(prev => [...prev, {
            role: 'ai',
            content: <>Analyzing<Loader2 className="h-3 w-3 animate-spin inline ml-1" />...</>
        }]);

        try {
            const response = await fetch('http://localhost:8000/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: '',
                    quick_action: action
                })
            });

            const data = await response.json();

            // Add 1 second delay for realistic feel
            await new Promise(resolve => setTimeout(resolve, 1000));

            // Replace loading with response
            setMessages(prev => {
                const msgs = [...prev];
                msgs[msgs.length - 1] = { role: 'ai', content: data.response };
                return msgs;
            });
        } catch (error) {
            console.error('Quick action error:', error);
            await new Promise(resolve => setTimeout(resolve, 1000));
            setMessages(prev => {
                const msgs = [...prev];
                msgs[msgs.length - 1] = {
                    role: 'ai',
                    content: 'Sorry, I couldn\'t process that action. Please check the backend.'
                };
                return msgs;
            });
        }
    };

    const handleActionClick = (action: string) => {
        setMessages(prev => [...prev, {
            role: 'ai',
            content: `Executing recommended action: "${action}"...`
        }]);
    };

    return (
        <div className="h-full flex flex-col gap-2 animate-fade-in overflow-hidden p-1">
            {/* Dense Header */}
            <div className="flex items-center justify-between shrink-0 h-8 px-1">
                <div>
                    <h1 className="text-lg font-bold tracking-tight">Dashboard</h1>
                    <p className="text-[10px] text-muted-foreground">
                        <span className="text-green-500">● Online</span> • {new Date().toLocaleDateString()}
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button
                        size="sm"
                        variant="outline"
                        className="h-7 text-[10px] px-2 gap-1.5"
                        onClick={handleRefresh}
                        disabled={isRefreshing}
                    >
                        {isRefreshing ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Refresh'}
                    </Button>
                    <Button
                        size="sm"
                        className="h-7 text-[10px] px-2"
                        onClick={handleSystemCheck}
                    >
                        System Check
                    </Button>
                </div>
            </div>

            {/* Main Grid: Full Height */}
            <div className="flex-1 min-h-0 grid grid-cols-12 grid-rows-12 gap-2">

                {/* ROW 1: Heartbeat (Extra Wide) & AI */}
                <div className="col-span-8 row-span-7 flex flex-col min-h-0">
                    <Card
                        title="System Heartbeat"
                        className="flex-1 flex flex-col min-h-0 overflow-hidden"
                        noPadding
                    >
                        {/* Single Column Layout - Top to Bottom - Fixed Height Dist */}
                        <div className="flex-1 px-4 py-2 flex flex-col min-h-0">

                            {/* Header Row - Fixed */}
                            <div className="grid grid-cols-12 text-[9px] text-muted-foreground border-b border-border/50 pb-2 mb-1 uppercase tracking-wider shrink-0">
                                <div className="col-span-3">Service Name</div>
                                <div className="col-span-7 pl-4">Real-time Latency Stream</div>
                                <div className="col-span-2 text-right">Status / Ping</div>
                            </div>

                            {/* List - Flex Fill */}
                            <div className="flex-1 flex flex-col min-h-0 justify-between">
                                {realtimeComponents.length > 0 ? (
                                    realtimeComponents.map((comp) => {
                                        const isHealthy = comp.status === 'healthy';
                                        const statusColor = isHealthy ? 'hsl(142 71% 45%)' : comp.status === 'degraded' ? 'hsl(48 96% 53%)' : 'hsl(0 84% 60%)';
                                        return (
                                            <div
                                                key={comp.id}
                                                className="group relative grid grid-cols-12 items-center gap-4 py-1 flex-1 min-h-0 border-b border-border/10 last:border-0 hover:bg-muted/10 transition-colors cursor-pointer"
                                                onClick={() => setSelectedServiceId(comp.id)}
                                            >
                                                {/* Col 1: Name */}
                                                <div className="col-span-3">
                                                    <div className="flex items-center gap-2">
                                                        <div className={cn(
                                                            "w-1.5 h-1.5 rounded-full shrink-0 transition-all duration-500",
                                                            isHealthy ? "bg-green-500" : comp.status === 'degraded' ? "bg-yellow-500" : "bg-red-500 shadow-[0_0_10px_red]"
                                                        )}></div>
                                                        <div className="min-w-0">
                                                            <div className="text-xs font-semibold truncate">{comp.name}</div>
                                                            <div className="text-[9px] text-muted-foreground font-mono truncate">
                                                                {isLive ? `Activity: ${comp.activity}` : 'Uptime: 99.9%'}
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* Col 2: Wide Waveform - Flexible Height */}
                                                <div className="col-span-7 h-full bg-secondary/10 rounded-md border border-border/30 group-hover:border-primary/30 transition-colors overflow-hidden relative">
                                                    <div className="absolute inset-x-0 bottom-0 top-0 opacity-80">
                                                        <HeartbeatLine color={statusColor} history={comp.history} />
                                                    </div>
                                                </div>

                                                {/* Col 3: Stats */}
                                                <div className="col-span-2 text-right">
                                                    <div className="font-mono text-xs font-bold text-foreground">{comp.latency}ms</div>
                                                    <Badge variant={comp.status === 'down' ? 'critical' : comp.status} className="h-3.5 px-1.5 text-[8px] uppercase mt-0.5">{comp.status}</Badge>
                                                </div>
                                            </div>
                                        );
                                    })
                                ) : (
                                    <div className="flex-1 flex items-center justify-center text-muted-foreground text-xs">
                                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                                        Connecting to backend...
                                    </div>
                                )}
                            </div>
                        </div>
                    </Card>
                </div>


                <div className="col-span-4 row-span-7 flex flex-col min-h-0">
                    <Card title="AI Analyst" className="flex-1 min-h-0 flex flex-col overflow-hidden" noPadding>
                        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
                            {/* Chat Messages - Scrollable */}
                            <div className="flex-1 overflow-y-auto overflow-x-hidden p-3 space-y-3 min-h-0">
                                {messages.map((msg, idx) => (
                                    <div key={idx} className={cn("flex gap-2 items-start", msg.role === 'user' ? "justify-end" : "")}>
                                        {msg.role === 'ai' && (
                                            <div className="h-6 w-6 rounded-full bg-primary/10 flex items-center justify-center shrink-0 text-xs">🤖</div>
                                        )}
                                        <div className={cn(
                                            "rounded-lg p-2.5 text-[11px] leading-relaxed shadow-sm max-w-[85%] whitespace-pre-wrap break-words",
                                            msg.role === 'ai'
                                                ? "bg-accent text-foreground"
                                                : "bg-primary/10 text-foreground border border-primary/20"
                                        )}>
                                            {typeof msg.content === 'string' ? (
                                                // Format markdown-style text
                                                <div dangerouslySetInnerHTML={{
                                                    __html: msg.content
                                                        // Headers (## text -> bold larger text)
                                                        .replace(/^## (.+)$/gm, '<div class="font-bold text-[13px] mt-2 mb-1">$1</div>')
                                                        .replace(/^### (.+)$/gm, '<div class="font-semibold text-[12px] mt-1 mb-0.5">$1</div>')
                                                        // Bold (**text** -> <strong>)
                                                        .replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold">$1</strong>')
                                                        // Code (`text` -> <code>)
                                                        .replace(/`([^`]+)`/g, '<code class="bg-muted/50 px-1 py-0.5 rounded text-[10px] font-mono">$1</code>')
                                                        // Line breaks
                                                        .replace(/\n/g, '<br/>')
                                                }} />
                                            ) : (
                                                msg.content
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Quick Actions */}
                            <div className="px-2 pb-2 border-t border-border/50 pt-2 shrink-0">
                                <div className="grid grid-cols-2 gap-1.5">
                                    <button
                                        className="text-[9px] px-2 py-1.5 rounded border border-border/50 hover:bg-accent hover:border-primary/30 transition-colors text-left truncate"
                                        onClick={() => handleQuickAction('explain_last')}
                                    >
                                        💡 Explain last alert
                                    </button>
                                    <button
                                        className="text-[9px] px-2 py-1.5 rounded border border-border/50 hover:bg-accent hover:border-primary/30 transition-colors text-left truncate"
                                        onClick={() => handleQuickAction('threat_summary')}
                                    >
                                        🎯 Threat summary
                                    </button>
                                    <button
                                        className="text-[9px] px-2 py-1.5 rounded border border-border/50 hover:bg-accent hover:border-primary/30 transition-colors text-left truncate"
                                        onClick={() => handleQuickAction('recommend_actions')}
                                    >
                                        🚀 Recommend actions
                                    </button>
                                    <button
                                        className="text-[9px] px-2 py-1.5 rounded border border-border/50 hover:bg-accent hover:border-primary/30 transition-colors text-left truncate"
                                        onClick={() => handleQuickAction('system_status')}
                                    >
                                        📊 System status
                                    </button>
                                </div>
                            </div>

                            <div className="p-2 border-t border-border bg-card/50 shrink-0">
                                <div className="relative">
                                    <input
                                        className="w-full rounded-md border border-input bg-background/50 px-2.5 py-1.5 pr-8 text-[11px] shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                                        placeholder="Command Arxis..."
                                        value={chatInput}
                                        onChange={(e) => setChatInput(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                                    />
                                    <button
                                        className="absolute right-2 top-2 text-muted-foreground hover:text-primary"
                                        onClick={handleSendMessage}
                                    >
                                        <Send className="h-3 w-3" />
                                    </button>
                                </div>
                            </div>
                        </div>
                    </Card>
                </div>

                {/* ROW 2: Perf | Severity | Alerts | Compliance */}
                <div className="col-span-2 row-span-5 flex flex-col min-h-0">
                    <Card title="Perf" className="flex-1 min-h-0 overflow-hidden" noPadding>
                        <div className="p-3 h-full flex flex-col justify-between gap-1">
                            {[
                                { label: 'CPU', value: 78, color: 'bg-orange-500' },
                                { label: 'RAM', value: 45, color: 'bg-blue-500' },
                                { label: 'NET', value: 92, color: 'bg-green-500' },
                            ].map((item, idx) => (
                                <div key={idx} className="flex-1 flex flex-col justify-center gap-1">
                                    <div className="flex justify-between text-[10px] items-end">
                                        <span className="text-muted-foreground font-medium">{item.label}</span>
                                        <span className="font-mono font-bold">{item.value}%</span>
                                    </div>
                                    <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
                                        <div className={cn("h-full", item.color)} style={{ width: `${item.value}%` }} />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </Card>
                </div>

                <div className="col-span-3 row-span-5 flex flex-col min-h-0">
                    <Card title="Threats" className="flex-1 min-h-0 overflow-hidden" noPadding>
                        <div className="h-full w-full p-2">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={SEVERITY_DATA} margin={{ top: 10, right: 10, left: -25, bottom: 0 }} barSize={35}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                                    <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={9} tickLine={false} axisLine={false} dy={5} />
                                    <YAxis stroke="hsl(var(--muted-foreground))" fontSize={9} tickLine={false} axisLine={false} />
                                    <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                                        {SEVERITY_DATA.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={entry.color} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </Card>
                </div>

                <div className="col-span-5 row-span-5 flex flex-col min-h-0">
                    <Card title="High Priority Alerts" className="flex-1 min-h-0 flex flex-col overflow-hidden" noPadding>
                        <div className="flex-1 p-2 flex flex-col gap-1.5 min-h-0 overflow-y-auto">
                            {alertsLoading ? (
                                <div className="flex-1 flex items-center justify-center">
                                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                                </div>
                            ) : liveAlerts.length === 0 ? (
                                <div className="flex-1 flex items-center justify-center">
                                    <p className="text-xs text-muted-foreground">No high-priority alerts</p>
                                </div>
                            ) : liveAlerts.slice(0, 6).map(alert => (
                                <div
                                    key={alert.id}
                                    className="group flex flex-col gap-0.5 rounded-md border border-border/50 bg-muted/10 p-2 transition-all hover:bg-accent hover:border-primary/20 cursor-pointer justify-center shrink-0 min-h-[45px] animate-fade-in"
                                    onClick={() => setSelectedAlert(alert)}
                                >
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-1.5">
                                            <Badge variant={alert.severity} className="h-3.5 px-1 uppercase text-[8px]">{alert.severity}</Badge>
                                            <span className="text-[9px] text-muted-foreground">{alert.timestamp}</span>
                                        </div>
                                        <ArrowRight className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                                    </div>
                                    <h4 className="font-semibold text-xs truncate group-hover:text-primary transition-colors">{alert.title}</h4>
                                    <p className="text-[9px] text-muted-foreground line-clamp-1 opacity-80">{alert.description}</p>
                                </div>
                            ))}
                        </div>
                    </Card>
                </div>

                <div className="col-span-2 row-span-5 flex flex-col min-h-0">
                    <Card title="Compliance" className="flex-1 min-h-0 overflow-hidden" noPadding>
                        <div className="p-3 h-full flex flex-col justify-between">
                            {MOCK_COMPLIANCE.map((item, idx) => (
                                <div key={idx} className="flex flex-col gap-0.5 border-b border-border/30 last:border-0 pb-1 last:pb-0 flex-1 justify-center min-h-0">
                                    <span className="text-[10px] font-medium truncate leading-tight">{item.name}</span>
                                    <Badge
                                        variant={item.status === 'compliant' ? 'healthy' : item.status === 'review_needed' ? 'degraded' : 'down'}
                                        className="h-3.5 px-1.5 text-[8px] capitalize w-fit"
                                    >
                                        {item.status.replace('_', ' ')}
                                    </Badge>
                                </div>
                            ))}
                        </div>
                    </Card>
                </div>

            </div>

            {/* Modals */}
            <Modal
                isOpen={!!selectedAlert}
                onClose={() => setSelectedAlert(null)}
                title="Alert Intelligence"
                className="max-w-2xl"
            >
                {selectedAlert && (
                    <div className="space-y-6">
                        <div className="flex items-start gap-4 p-4 rounded-lg bg-muted/30 border border-border/50">
                            <div className="p-2 bg-red-500/10 rounded-full">
                                <AlertTriangle className="h-5 w-5 text-red-500" />
                            </div>
                            <div>
                                <h3 className="text-sm font-semibold">{selectedAlert.title}</h3>
                                <p className="text-xs text-muted-foreground mt-1">{selectedAlert.description}</p>
                                <div className="flex gap-2 mt-3">
                                    <Badge variant={selectedAlert.severity} className="uppercase">{selectedAlert.severity}</Badge>
                                    <Badge variant="outline" className="font-mono">{selectedAlert.asset}</Badge>
                                    <Badge variant="outline" className="font-mono">{selectedAlert.user}</Badge>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">AI Analysis Trace</h4>
                            <div className="relative pl-4 border-l-2 border-border/50 space-y-4">
                                {(selectedAlert.trace || []).map((t, i) => (
                                    <div key={i} className="relative">
                                        <div className="absolute -left-[21px] top-1.5 w-3 h-3 rounded-full bg-background border-2 border-primary" />
                                        <div className="flex flex-col gap-0.5">
                                            <span className="text-xs font-medium text-primary">{t.agent}</span>
                                            <p className="text-xs text-foreground/80">{t.action}</p>
                                            <span className="text-[10px] text-muted-foreground font-mono">{t.timestamp}</span>
                                        </div>
                                    </div>
                                ))}
                                {(!selectedAlert.trace || selectedAlert.trace.length === 0) && (
                                    <p className="text-xs text-muted-foreground italic">No trace data available.</p>
                                )}
                            </div>
                        </div>

                        <div className="space-y-2">
                            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Recommended Actions</h4>
                            <div className="grid grid-cols-2 gap-2">
                                {(selectedAlert.recommendedActions || []).map((action, i) => (
                                    <Button
                                        key={i}
                                        variant="outline"
                                        className="justify-start h-auto py-2 px-3 text-xs hover:bg-primary/10 hover:text-primary transition-colors"
                                        onClick={() => handleActionClick(action)}
                                    >
                                        <Shield className="h-3 w-3 mr-2" />
                                        {action}
                                    </Button>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </Modal>

            <Modal
                isOpen={!!selectedService}
                onClose={() => setSelectedServiceId(null)}
                title="Service Diagnostics"
            >
                {selectedService && (
                    <div className="space-y-4">
                        <div className="flex items-center gap-4">
                            <div className={cn(
                                "w-3 h-3 rounded-full shadow-[0_0_15px]",
                                selectedService.status === 'healthy' ? "bg-green-500 shadow-green-500/50" : "bg-red-500 shadow-red-500/50"
                            )} />
                            <div className="flex-1">
                                <h3 className="font-semibold">{selectedService.name}</h3>
                                <p className="text-xs text-muted-foreground font-mono">ID: {selectedService.id}</p>
                            </div>
                            <div className="text-right">
                                <div className="text-2xl font-bold font-mono">{selectedService.latency}ms</div>
                                <div className="text-xs text-muted-foreground">Current Latency</div>
                            </div>
                        </div>

                        <div className="h-32 bg-secondary/10 rounded-md border border-border/50 p-4 flex items-center justify-center relative overflow-hidden">
                            <HeartbeatLine color={selectedService.status === 'healthy' ? 'hsl(142 71% 45%)' : 'hsl(0 84% 60%)'} history={selectedService.history} />
                            <div className="absolute top-2 left-2 text-[9px] text-muted-foreground uppercase tracking-widest">Real-time Metrics</div>
                        </div>

                        <div className="grid grid-cols-3 gap-2 text-center">
                            <div className="p-2 rounded bg-muted/20">
                                <div className="text-xs text-muted-foreground">Uptime</div>
                                <div className="font-mono font-bold text-green-500">99.99%</div>
                            </div>
                            <div className="p-2 rounded bg-muted/20">
                                <div className="text-xs text-muted-foreground">Error Rate</div>
                                <div className="font-mono font-bold">0.001%</div>
                            </div>
                            <div className="p-2 rounded bg-muted/20">
                                <div className="text-xs text-muted-foreground">Load</div>
                                <div className="font-mono font-bold">45%</div>
                            </div>
                        </div>
                    </div>
                )}
            </Modal>

            <Modal
                isOpen={showSystemCheck}
                onClose={() => setShowSystemCheck(false)}
                title="System Diagnostic Check"
            >
                <div className="space-y-6 py-4">
                    <div className="flex flex-col items-center justify-center gap-4">
                        {checkProgress < 100 ? (
                            <Loader2 className="h-12 w-12 text-primary animate-spin" />
                        ) : (
                            <CheckCircle2 className="h-12 w-12 text-green-500 animate-in zoom-in-50 duration-300" />
                        )}
                        <div className="text-center">
                            <h3 className="font-semibold">{checkProgress < 100 ? 'Running Diagnostics...' : 'All Systems Operational'}</h3>
                            <p className="text-xs text-muted-foreground mt-1">
                                {checkProgress < 100 ? `Checking core services and network integrity...` : `Diagnostic completed successfully at ${new Date().toLocaleTimeString()}`}
                            </p>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                            <div
                                className="h-full bg-primary transition-all duration-200 ease-out"
                                style={{ width: `${checkProgress}%` }}
                            />
                        </div>
                        <div className="flex justify-between text-[10px] text-muted-foreground uppercase font-mono">
                            <span>Initializing</span>
                            <span>Verify Config</span>
                            <span>Check Latency</span>
                            <span>Done</span>
                        </div>
                    </div>

                    {checkProgress === 100 && (
                        <div className="flex justify-center">
                            <Button onClick={() => setShowSystemCheck(false)}>Close Report</Button>
                        </div>
                    )}
                </div>
            </Modal>

        </div>
    );
};

export default Dashboard;
