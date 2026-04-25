export type Severity = 'critical' | 'high' | 'medium' | 'low';
export type Status = 'healthy' | 'degraded' | 'down';
export type AlertStatus = 'open' | 'investigating' | 'resolved';

export interface Alert {
    id: string;
    severity: Severity;
    title: string;
    description: string;
    timestamp: string; // ISO string or relative time string for display
    status: AlertStatus;
    confidence: number;
    user?: string;
    asset?: string;
    recommendedActions?: string[];
    trace?: {
        agent: string;
        action: string;
        timestamp: string;
    }[];
}

export interface SystemComponent {
    id: string;
    name: string;
    status: Status;
    latency: number;
    history: number[]; // Array of latency values for heartbeat
}

export interface Agent {
    id: string;
    name: string;
    role: string;
    description: string;
    decisions: string[];
    exampleOutput: string;
    status: 'active' | 'inactive';
}

export interface ComplianceItem {
    name: string;
    status: 'compliant' | 'review_needed' | 'action_required';
    details?: string;
}
