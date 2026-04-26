/**
 * API Service for Arceux Frontend
 * 
 * Handles all communication with the backend API
 */

import { Alert } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Types matching backend API
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interface BackendAlert {
    alert_id: string;
    timestamp: string;
    user: string;
    threat_type: string;
    severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
    explanation: string;
    recommendation: string;
    agent_trace: string[];
    raw_events: any[];
    metadata: Record<string, any>;
    status?: string; // 'open' | 'investigating' | 'resolved'
}

interface Metrics {
    total_logs: number;
    total_alerts: number;
    alerts_by_severity: {
        LOW: number;
        MEDIUM: number;
        HIGH: number;
        CRITICAL: number;
    };
    recent_activity: any[];
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Helper Functions
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/**
 * Convert backend alert to frontend format
 */
function transformBackendAlert(backendAlert: BackendAlert): Alert {
    // Map severity
    const severityMap: Record<string, 'critical' | 'high' | 'medium' | 'low'> = {
        'CRITICAL': 'critical',
        'HIGH': 'high',
        'MEDIUM': 'medium',
        'LOW': 'low'
    };

    // Format timestamp
    const formatTimestamp = (isoString: string): string => {
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 1) return 'just now';
        if (diffMins < 60) return `${diffMins} min ago`;
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        return date.toLocaleDateString();
    };

    // Extract asset and user from raw events
    const firstEvent = backendAlert.raw_events?.[0] || {};
    const asset = firstEvent.asset || backendAlert.metadata?.asset || 'unknown';

    // Confidence: River ML score takes priority; fall back to severity-based estimate
    const mappedSeverity = severityMap[backendAlert.severity] || 'medium';
    const severityConfidence: Record<string, number> = { critical: 95, high: 80, medium: 60, low: 40 };
    const confidence =
        backendAlert.metadata?.river_ml === true && backendAlert.metadata?.anomaly_score != null
            ? Math.max(0, Math.min(100, Math.round(backendAlert.metadata.anomaly_score * 100)))
            : severityConfidence[mappedSeverity];

    // Build trace from agent_trace
    const trace = backendAlert.agent_trace.map((agent, index) => {
        let action = 'Processed step';
        const actions = [
            'Orchestrated incident response strategy',    // Index 0: Orchestrator
            'Triaged and normalized detection signal',    // Index 1: Alert Handler
            'Classified threat using MITRE ATT&CK',       // Index 2: Threat Analyzer
            'Reconstructed attack timeline & root cause', // Index 3: Root Cause
            'Evaluated regulatory & compliance impact',   // Index 4: Compliance
            'Drafted automated remediation plan'          // Index 5: Response
        ];

        if (index < actions.length) {
            action = actions[index];
        } else if (agent.includes('Fallback')) {
            action = 'Rule-based detection fallback';
        }

        return {
            agent,
            action,
            timestamp: `+${index * 250}ms`
        };
    });

    // Parse recommended actions from recommendation text
    const recommendedActions = backendAlert.recommendation
        .split(/[.\n]/)
        .map(s => s.trim())
        .filter(s => s.length > 0)
        .slice(0, 3);

    return {
        id: backendAlert.alert_id,
        severity: mappedSeverity,
        title: backendAlert.threat_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        description: backendAlert.explanation,
        timestamp: backendAlert.timestamp, // Return raw ISO timestamp, let UI format it
        status: (backendAlert.status as 'open' | 'investigating' | 'resolved') || 'open',
        confidence,
        user: backendAlert.user,
        asset,
        recommendedActions,
        trace
    };
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// API Functions
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/**
 * Fetch all alerts from backend
 */
export async function fetchAlerts(options?: {
    severity?: string;
    limit?: number;
}): Promise<Alert[]> {
    try {
        const params = new URLSearchParams();
        if (options?.severity) params.append('severity', options.severity);
        if (options?.limit) params.append('limit', options.limit.toString());

        const url = `${API_BASE_URL}/alerts${params.toString() ? '?' + params.toString() : ''}`;

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const backendAlerts: BackendAlert[] = await response.json();
        return backendAlerts.map(transformBackendAlert);
    } catch (error) {
        console.error('Failed to fetch alerts:', error);
        throw error;
    }
}

/**
 * Fetch a specific alert by ID
 */
export async function fetchAlertById(alertId: string): Promise<Alert> {
    try {
        const response = await fetch(`${API_BASE_URL}/alerts/${alertId}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const backendAlert: BackendAlert = await response.json();
        return transformBackendAlert(backendAlert);
    } catch (error) {
        console.error(`Failed to fetch alert ${alertId}:`, error);
        throw error;
    }
}

/**
 * Fetch system metrics
 */
export async function fetchMetrics(): Promise<Metrics> {
    try {
        const response = await fetch(`${API_BASE_URL}/metrics`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Failed to fetch metrics:', error);
        throw error;
    }
}

/**
 * Health check
 */
export async function checkHealth(): Promise<{ status: string; timestamp: string }> {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Health check failed:', error);
        throw error;
    }
}

/**
 * Real-time system component data for heartbeat visualization
 */
export interface RealtimeComponent {
    id: string;
    name: string;
    status: 'healthy' | 'degraded' | 'down';
    latency: number;
    history: number[];
    activity: number;
}

export interface RealtimeMetrics {
    timestamp: string;
    components: RealtimeComponent[];
    summary: {
        total_logs: number;
        total_alerts: number;
        pending_signals: number;
    };
}

/**
 * Fetch real-time system metrics for heartbeat visualization
 */
export async function fetchRealtimeMetrics(): Promise<RealtimeMetrics> {
    try {
        const response = await fetch(`${API_BASE_URL}/metrics/realtime`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Failed to fetch realtime metrics:', error);
        throw error;
    }
}

/**
 * Ingest a log (for testing)
 */
export async function ingestLog(log: {
    timestamp: string;
    user: string;
    event_type: string;
    ip: string;
    location: string;
    asset: string;
}): Promise<{ status: string }> {
    try {
        const response = await fetch(`${API_BASE_URL}/logs`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(log),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Failed to ingest log:', error);
        throw error;
    }
}

/**
 * Update the status of an alert (open | investigating | resolved)
 */
export async function updateAlertStatus(
    alertId: string,
    status: 'open' | 'investigating' | 'resolved'
): Promise<Alert> {
    const response = await fetch(`${API_BASE_URL}/alerts/${alertId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    const backendAlert: BackendAlert = await response.json();
    return transformBackendAlert(backendAlert);
}

/**
 * Execute a security response action against an alert
 */
export async function executeAction(payload: {
    action_type: string;
    alert_id: string;
    parameters?: Record<string, any>;
}): Promise<{ success: boolean; message: string; action_type: string }> {
    const response = await fetch(`${API_BASE_URL}/actions/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
}

/**
 * Agent status returned by GET /agents/status
 */
export interface AgentStatus {
    name: string;
    status: 'idle' | 'running' | 'completed' | 'error';
    last_run: string | null;
    tasks_completed: number;
    execution_count: number;
    avg_execution_time_ms: number;
    last_execution_trace: string[];
}

export interface AgentStatusResponse {
    agents: AgentStatus[];
    last_signal_type: string | null;
}

/**
 * Fetch the current status of all AI agents
 */
export async function fetchAgentStatus(): Promise<AgentStatusResponse> {
    try {
        const response = await fetch(`${API_BASE_URL}/agents/status`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('Failed to fetch agent status:', error);
        throw error;
    }
}

/**
 * Trigger the agent pipeline on a specific alert (or the latest alert if no ID given)
 */
export async function triggerAgentPipeline(alertId?: string): Promise<{ success: boolean; message: string }> {
    try {
        const response = await fetch(`${API_BASE_URL}/agents/trigger`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ alert_id: alertId ?? null }),
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('Failed to trigger agent pipeline:', error);
        throw error;
    }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// React Hooks (Optional)
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/**
 * Hook for polling alerts
 * Usage: const alerts = useAlerts({ pollInterval: 5000 });
 */
export function useAlerts(options?: {
    pollInterval?: number;
    severity?: string;
    limit?: number;
}) {
    const [alerts, setAlerts] = React.useState<Alert[]>([]);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState<Error | null>(null);

    React.useEffect(() => {
        let intervalId: number | undefined;

        const loadAlerts = async () => {
            try {
                const data = await fetchAlerts({
                    severity: options?.severity,
                    limit: options?.limit || 100
                });
                setAlerts(data);
                setError(null);
            } catch (err) {
                setError(err as Error);
            } finally {
                setLoading(false);
            }
        };

        // Initial load
        loadAlerts();

        // Setup polling if interval specified
        if (options?.pollInterval) {
            intervalId = setInterval(loadAlerts, options.pollInterval);
        }

        return () => {
            if (intervalId) clearInterval(intervalId);
        };
    }, [options?.pollInterval, options?.severity, options?.limit]);

    return { alerts, loading, error, refetch: () => fetchAlerts(options) };
}

// Prevent React import error if used without React
import * as React from 'react';
