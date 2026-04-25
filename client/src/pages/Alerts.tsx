import React, { useState, useEffect, useCallback } from 'react';
import { Alert } from '../types';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { X, Bot, Shield, FileText, Search, Filter, Loader2, RefreshCw } from 'lucide-react';
import { cn } from '../lib/utils';
import { fetchAlerts } from '../services/api';

const Alerts: React.FC = () => {
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
    const [refreshing, setRefreshing] = useState(false);

    // Track local modifications that haven't been synced to backend yet
    // Key: alert ID, Value: partial alert updates
    const [localModifications, setLocalModifications] = useState<Record<string, Partial<Alert>>>({});

    // Derive selectedAlert from alerts array to ensure it's always in sync
    const selectedAlert = selectedAlertId ? alerts.find(a => a.id === selectedAlertId) || null : null;

    // Filter states
    const [severityFilter, setSeverityFilter] = useState<string | null>(null);
    const [statusFilter, setStatusFilter] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState('');

    // Helper to format timestamps
    const formatTimestamp = (timestamp: string) => {
        if (!timestamp) return 'Unknown';

        const date = new Date(timestamp);

        // Check if date is invalid
        if (isNaN(date.getTime())) {
            return timestamp; // Return original if can't parse
        }

        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'just now';
        if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
        if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

        try {
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        } catch (e) {
            return timestamp;
        }
    };

    // Handle take ownership
    const handleTakeOwnership = async () => {
        if (!selectedAlert) return;

        // Track this modification locally so it persists across backend refreshes
        setLocalModifications(prev => ({
            ...prev,
            [selectedAlert.id]: { status: 'investigating' as const }
        }));

        // Update local state immediately for optimistic UI
        const updatedAlerts = alerts.map(a =>
            a.id === selectedAlert.id ? { ...a, status: 'investigating' as const } : a
        );
        setAlerts(updatedAlerts);
        // No need to update selectedAlert separately - it's derived from alerts!

        // TODO: Send update to backend API
        // await updateAlertStatus(selectedAlert.id, 'investigating');
        // On success, remove from localModifications:
        // setLocalModifications(prev => { const {[selectedAlert.id]: _, ...rest} = prev; return rest; });
    };

    // Fetch alerts from API
    const loadAlerts = useCallback(async () => {
        setRefreshing(true);
        try {
            const data = await fetchAlerts({ limit: 100 });

            // Merge backend data with local modifications
            const mergedAlerts = data.map(alert => {
                const localMod = localModifications[alert.id];
                return localMod ? { ...alert, ...localMod } : alert;
            });

            setAlerts(mergedAlerts);
            setError(null);
        } catch (err) {
            console.error('Failed to load alerts:', err);
            setError('Failed to load alerts from backend');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [localModifications]);

    // Filter and search alerts
    const filteredAlerts = alerts.filter(alert => {
        // Severity filter
        if (severityFilter && alert.severity.toLowerCase() !== severityFilter.toLowerCase()) {
            return false;
        }

        // Status filter
        if (statusFilter && alert.status.toLowerCase() !== statusFilter.toLowerCase()) {
            return false;
        }

        // Search filter
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            return (
                alert.title?.toLowerCase().includes(query) ||
                alert.user?.toLowerCase().includes(query) ||
                alert.asset?.toLowerCase().includes(query) ||
                alert.description?.toLowerCase().includes(query)
            );
        }

        return true;
    });

    useEffect(() => {
        loadAlerts();

        // Auto-refresh every 10 seconds
        const interval = setInterval(loadAlerts, 10000);
        return () => clearInterval(interval);
    }, [loadAlerts]);

    return (
        <div className="space-y-6 animate-fade-in relative h-[calc(100vh-4rem)] flex flex-col">
            <div className="flex items-center justify-between shrink-0">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Security Alerts</h1>
                    <p className="text-muted-foreground mt-1">
                        {loading ? 'Loading alerts...' : `${filteredAlerts.length} of ${alerts.length} ${alerts.length === 1 ? 'alert' : 'alerts'} ${severityFilter || statusFilter || searchQuery ? 'shown' : 'detected'}`}
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => loadAlerts()}
                        disabled={refreshing}
                        className="gap-2"
                    >
                        <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
                        Refresh
                    </Button>
                    <Button variant="outline">Export CSV</Button>
                    <Button>Run Playbook</Button>
                </div>
            </div>

            <div className="flex gap-4 items-center shrink-0">
                <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <input
                        type="text"
                        placeholder="Search alerts..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 pl-9 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    />
                </div>
                <div className="relative">
                    <Button
                        variant={severityFilter ? "default" : "outline"}
                        size="sm"
                        className="h-9 gap-2"
                        onClick={() => {
                            // Cycle: null -> critical -> high -> medium -> low -> null
                            if (!severityFilter) {
                                setSeverityFilter('critical');
                            } else if (severityFilter === 'critical') {
                                setSeverityFilter('high');
                            } else if (severityFilter === 'high') {
                                setSeverityFilter('medium');
                            } else if (severityFilter === 'medium') {
                                setSeverityFilter('low');
                            } else {
                                setSeverityFilter(null);
                            }
                        }}
                    >
                        <Filter className="h-4 w-4" />
                        {severityFilter ? `Severity: ${severityFilter}` : 'Severity'}
                    </Button>
                </div>
                <div className="relative">
                    <Button
                        variant={statusFilter ? "default" : "outline"}
                        size="sm"
                        className="h-9 gap-2"
                        onClick={() => {
                            // Cycle: null -> open -> investigating -> resolved -> null
                            if (!statusFilter) {
                                setStatusFilter('open');
                            } else if (statusFilter === 'open') {
                                setStatusFilter('investigating');
                            } else if (statusFilter === 'investigating') {
                                setStatusFilter('resolved');
                            } else {
                                setStatusFilter(null);
                            }
                        }}
                    >
                        <Filter className="h-4 w-4" />
                        {statusFilter ? `Status: ${statusFilter}` : 'Status'}
                    </Button>
                </div>
            </div>

            <div className="rounded-md border border-border bg-card flex-1 overflow-auto">
                <table className="w-full caption-bottom text-sm text-left">
                    <thead className="[&_tr]:border-b">
                        <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                            <th className="h-10 px-4 align-middle font-medium text-muted-foreground">Severity</th>
                            <th className="h-10 px-4 align-middle font-medium text-muted-foreground">Alert Name</th>
                            <th className="h-10 px-4 align-middle font-medium text-muted-foreground">Asset / User</th>
                            <th className="h-10 px-4 align-middle font-medium text-muted-foreground">Confidence</th>
                            <th className="h-10 px-4 align-middle font-medium text-muted-foreground">Status</th>
                            <th className="h-10 px-4 align-middle font-medium text-muted-foreground">Time Detected</th>
                        </tr>
                    </thead>
                    <tbody className="[&_tr:last-child]:border-0">
                        {loading ? (
                            <tr>
                                <td colSpan={6} className="p-8 text-center">
                                    <div className="flex flex-col items-center justify-center gap-3">
                                        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                                        <p className="text-sm text-muted-foreground">Loading alerts from CrewAI...</p>
                                    </div>
                                </td>
                            </tr>
                        ) : error ? (
                            <tr>
                                <td colSpan={6} className="p-8 text-center">
                                    <div className="flex flex-col items-center justify-center gap-3">
                                        <p className="text-sm text-destructive">{error}</p>
                                        <Button variant="outline" size="sm" onClick={() => loadAlerts()}>
                                            Try Again
                                        </Button>
                                    </div>
                                </td>
                            </tr>
                        ) : alerts.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="p-8 text-center">
                                    <div className="flex flex-col items-center justify-center gap-3">
                                        <p className="text-sm text-muted-foreground">No alerts detected yet</p>
                                        <p className="text-xs text-muted-foreground">Waiting for CrewAI to analyze security signals...</p>
                                    </div>
                                </td>
                            </tr>
                        ) : (
                            filteredAlerts.map((alert: Alert) => (
                                <tr
                                    key={alert.id}
                                    onClick={() => setSelectedAlertId(alert.id)}
                                    className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted cursor-pointer"
                                >
                                    <td className="p-4 align-middle"><Badge variant={alert.severity}>{alert.severity}</Badge></td>
                                    <td className="p-4 align-middle">
                                        <div className="font-semibold">{alert.title}</div>
                                        <div className="text-xs text-muted-foreground">{alert.id}</div>
                                    </td>
                                    <td className="p-4 align-middle">
                                        <div className="text-sm">{alert.asset}</div>
                                        <div className="text-xs text-muted-foreground">{alert.user}</div>
                                    </td>
                                    <td className="p-4 align-middle">
                                        <div className="flex items-center gap-2">
                                            <div className="h-1.5 w-16 bg-secondary rounded-full overflow-hidden">
                                                <div className="h-full bg-green-500" style={{ width: `${alert.confidence}%` }}></div>
                                            </div>
                                            <span className="text-xs font-mono">{alert.confidence}%</span>
                                        </div>
                                    </td>
                                    <td className="p-4 align-middle">
                                        <Badge variant={alert.status === 'open' ? 'down' : alert.status === 'investigating' ? 'degraded' : 'healthy'} className="capitalize bg-transparent border">
                                            {alert.status}
                                        </Badge>
                                    </td>
                                    <td className="p-4 align-middle font-mono text-xs text-muted-foreground">{formatTimestamp(alert.timestamp)}</td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Detail Overlay */}
            {selectedAlert && (
                <div className="absolute inset-0 bg-background/80 backdrop-blur-sm z-40" onClick={() => setSelectedAlertId(null)}></div>
            )}

            <div className={cn(
                "fixed top-0 right-0 bottom-0 w-[600px] border-l border-border bg-card shadow-2xl z-50 p-6 transition-transform duration-300 ease-in-out transform flex flex-col",
                selectedAlert ? "translate-x-0" : "translate-x-full"
            )}>
                {selectedAlert && (
                    <>
                        <div className="flex justify-between items-start mb-6 border-b border-border pb-4">
                            <div>
                                <div className="flex items-center gap-2 mb-2">
                                    <Badge variant={selectedAlert.severity} className="uppercase">{selectedAlert.severity}</Badge>
                                    <span className="text-xs font-mono text-muted-foreground">{selectedAlert.id}</span>
                                </div>
                                <h2 className="text-2xl font-bold tracking-tight mb-1">{selectedAlert.title}</h2>
                            </div>
                            <Button variant="ghost" size="icon" onClick={() => setSelectedAlertId(null)}>
                                <X className="h-5 w-5" />
                            </Button>
                        </div>

                        <div className="flex-1 overflow-y-auto pr-4 space-y-8">
                            <section>
                                <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
                                    <FileText className="h-4 w-4" /> Summary
                                </h3>
                                <div className="bg-muted/50 p-4 rounded-lg border border-border text-sm leading-relaxed">
                                    {selectedAlert.description}
                                </div>
                            </section>

                            <section>
                                <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
                                    <Bot className="h-4 w-4" /> AI Agent Trace
                                </h3>
                                <div className="bg-muted/30 p-4 rounded-lg border border-border relative">
                                    {selectedAlert.trace && selectedAlert.trace.length > 0 ? (
                                        <>
                                            <div className="absolute left-6 top-6 bottom-6 w-0.5 bg-border"></div>
                                            <div className="space-y-6 relative">
                                                {selectedAlert.trace.map((step, index) => (
                                                    <div key={index} className="flex gap-4">
                                                        <div className="h-8 w-8 shrink-0 rounded-full bg-primary/10 border-2 border-primary flex items-center justify-center text-xs font-bold z-10">
                                                            {index + 1}
                                                        </div>
                                                        <div>
                                                            <div className="text-sm font-semibold text-primary">{step.agent}</div>
                                                            <div className="text-xs text-muted-foreground mt-0.5">{step.action}</div>
                                                            <div className="text-[10px] text-muted-foreground/60 mt-1 font-mono">{step.timestamp}</div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </>
                                    ) : (
                                        <div className="text-sm text-muted-foreground text-center py-4">
                                            No agent trace available
                                        </div>
                                    )}
                                </div>
                            </section>

                            <section>
                                <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
                                    <Shield className="h-4 w-4" /> Recommended Actions
                                </h3>
                                <div className="flex flex-col gap-2">
                                    {selectedAlert.recommendedActions?.map((action, i) => (
                                        <div key={i} className="flex items-center justify-between p-3 rounded-md bg-background border border-border">
                                            <span className="text-sm font-medium">{action}</span>
                                            <Button size="sm" variant="secondary">Execute</Button>
                                        </div>
                                    ))}
                                </div>
                            </section>
                        </div>

                        <div className="pt-4 border-t border-border mt-auto flex justify-end gap-3 sticky bottom-0 bg-card">
                            <Button variant="outline" onClick={() => setSelectedAlertId(null)}>Close</Button>
                            <Button
                                onClick={handleTakeOwnership}
                                disabled={selectedAlert?.status !== 'open'}
                            >
                                {selectedAlert?.status === 'investigating' ? 'Already Investigating' : 'Take Ownership'}
                            </Button>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default Alerts;
