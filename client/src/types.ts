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

export interface ComplianceItemStatus {
    status: 'action_required' | 'review_needed' | 'compliant';
    reason: string;
    deadline_hours?: number | null;
    time_remaining_minutes?: number | null;
    triggered_by?: string | null;
}

export interface ComplianceStatus {
    irdai: ComplianceItemStatus;
    gdpr: ComplianceItemStatus;
    soc2: ComplianceItemStatus;
    iso27001: ComplianceItemStatus;
    pci_dss: ComplianceItemStatus;
    last_updated: string;
}
