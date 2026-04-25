import { Alert, SystemComponent, Agent, ComplianceItem } from '../types';

export const MOCK_ALERTS: Alert[] = [
    {
        id: 'ALT-1024',
        severity: 'critical',
        title: 'Privilege Escalation Detected',
        description: 'Anomalous sudo usage detected on production-db-01. User "jenkins" attempted to modify /etc/shadow.',
        timestamp: '2 min ago',
        status: 'investigating',
        confidence: 98,
        user: 'jenkins',
        asset: 'production-db-01',
        recommendedActions: ['Isolate Host', 'Revoke API Keys', 'Notify Admin'],
        trace: [
            { agent: 'Ingestion Agent', action: 'Parsed auth.log stream', timestamp: '10:01:12' },
            { agent: 'Threat Analyst', action: 'Matched T1068 (Exploitation for Privilege Escalation)', timestamp: '10:01:13' },
            { agent: 'Context Agent', action: 'Correlated with recent deployment 403 errors', timestamp: '10:01:15' },
            { agent: 'SOC Manager', action: 'raised severity to CRITICAL', timestamp: '10:01:16' }
        ]
    },
    {
        id: 'ALT-1025',
        severity: 'high',
        title: 'Lateral Movement Activity',
        description: 'Suspicious SMB connections from workstation-04 to backup-server. Pattern matches BloodHound mapping.',
        timestamp: '15 min ago',
        status: 'open',
        confidence: 85,
        user: 'SYSTEM',
        asset: 'workstation-04',
        recommendedActions: ['Block SMB Port', 'Scan for Mimikatz'],
        trace: []
    },
    {
        id: 'ALT-1026',
        severity: 'medium',
        title: 'Data Exfiltration Attempt',
        description: 'Unusual outbound traffic spike (450MB) to unknown IP 192.0.2.14 over port 443.',
        timestamp: '42 min ago',
        status: 'resolved',
        confidence: 72,
        user: 'm.scott',
        asset: 'gateway-02',
        recommendedActions: ['Block IP', 'Deep Packet Inspection'],
        trace: []
    },
    {
        id: 'ALT-1027',
        severity: 'low',
        title: 'New Admin Account Created',
        description: 'User "d.jacks" created a new administrator account "backup_admin".',
        timestamp: '1 hour ago',
        status: 'open',
        confidence: 100,
        user: 'd.jacks',
        asset: 'iam-service',
        recommendedActions: ['Verify Change Request'],
        trace: []
    },
    {
        id: 'ALT-1028',
        severity: 'critical',
        title: 'Ransomware Beaconing',
        description: 'Periodic C2 traffic detected matching known Cobalt Strike profile.',
        timestamp: '3 hours ago',
        status: 'investigating',
        confidence: 99,
        user: 'unknown',
        asset: 'finance-files-01',
        recommendedActions: ['Isolate Network Segment', 'Initiate Incident Response'],
        trace: []
    }
];

export const MOCK_SYSTEM_COMPONENTS: SystemComponent[] = [
    { id: '1', name: 'Log Collector', status: 'healthy', latency: 45, history: [40, 42, 45, 44, 46, 45, 43, 45, 44, 45] },
    { id: '2', name: 'Threat Intelligence', status: 'healthy', latency: 120, history: [110, 115, 120, 118, 122, 120, 119, 120, 121, 120] },
    { id: '3', name: 'SIEM Engine', status: 'healthy', latency: 85, history: [80, 82, 85, 84, 86, 85, 83, 85, 84, 85] },
    { id: '4', name: 'Alert Pipeline', status: 'degraded', latency: 245, history: [150, 180, 210, 230, 245, 250, 245, 240, 245, 248] },
    { id: '5', name: 'Analytics Engine', status: 'healthy', latency: 310, history: [300, 305, 310, 308, 312, 310, 309, 310, 311, 310] },
    { id: '6', name: 'Database', status: 'healthy', latency: 12, history: [10, 11, 12, 11, 13, 12, 11, 12, 12, 12] },
];

export const MOCK_AGENTS: Agent[] = [
    {
        id: 'agt-1',
        name: 'Ingestion Analyst',
        role: 'Data Normalization & Parsing',
        description: 'Continuously monitors raw logs from 500+ sources. Identifies formats, parses fields, and filters noise before data hits the SIEM.',
        decisions: ['Discarded 45% of logs as noise', 'Normalized timestamps to UTC', 'Tagged PII data fields'],
        exampleOutput: 'Detected unknown log format from firewall-03. Auto-generated regex parser pattern #421. Integrity verified.',
        status: 'active'
    },
    {
        id: 'agt-2',
        name: 'Threat Analyst',
        role: 'Signature & Behavior Matching',
        description: 'Scans normalized events against 50,000+ threat signatures and behavioral baselines. Maps events to MITRE ATT&CK framework.',
        decisions: ['Matched IOC: 192.168.1.5', 'Identified T1110 (Brute Force)', 'Flagged impossible travel login'],
        exampleOutput: 'High confidence match for CVE-2023-44487 in web-server traffic. Correlated with threat feed Intel-42.',
        status: 'active'
    },
    {
        id: 'agt-3',
        name: 'Context Enrichment',
        role: 'Asset & Identity Correlation',
        description: 'Enriches alerts with user data (LDAP), asset criticality (CMDB), and past incident history to calculate true risk scores.',
        decisions: ['Retrieved User Role: DevOps Admin', 'Asset Criticality: High (PCI Scope)', 'Added GeoIP: Moscow, RU'],
        exampleOutput: 'User "admin" has never logged in from IP region "South America". escalating risk score +30.',
        status: 'active'
    },
    {
        id: 'agt-4',
        name: 'Explanation Agent',
        role: 'Natural Language Summarization',
        description: 'Synthesizes complex technical data into human-readable narratives for analysts and executives.',
        decisions: ['Generated executive summary', 'Simplified technical jargon', 'Created timeline view'],
        exampleOutput: 'This alert represents a likely credential theft followed by an attempt to dump database tables. Immediate action recommended.',
        status: 'active'
    },
    {
        id: 'agt-5',
        name: 'SOC Manager',
        role: 'Orchestration & Response',
        description: 'Oversees the entire pipeline. Prioritizes alerts based on resource availability and business impact. Suggests playbooks.',
        decisions: ['Assigned to Analyst: Sarah', 'Triggered Playbook: P_Isolate_Host', 'Escalated to P1'],
        exampleOutput: 'Orchestrating response for Critical Incident #992. Waiting for human approval to isolate host.',
        status: 'active'
    }
];

export const MOCK_COMPLIANCE: ComplianceItem[] = [
    { name: 'SOC 2 Type II', status: 'compliant' },
    { name: 'ISO 27001', status: 'compliant' },
    { name: 'GDPR', status: 'review_needed', details: 'due in 5 days' },
    { name: 'IRDAI', status: 'action_required', details: 'Audit pending' },
    { name: 'PCI DSS', status: 'compliant' },
];
