"""
Arxis Agentic System - Specialized SOC Agents
"""

from crewai import Agent, Task, Crew, Process
from typing import Dict, Any, List
from models import DetectionSignal


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1️⃣ Orchestrator Agent (The Coordinator)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_orchestrator_agent() -> Agent:
    """
    Ensures the right agents run at the right time.
    Role: Incident Commander & Coordinator.
    """
    return Agent(
        role="Orchestrator Agent",
        goal="Coordinate the incident response lifecycle and manage global incident context",
        backstory="""You are the SOC Incident Commander. You do not analyze raw logs yourself; 
        instead, you direct your team of specialized agents. You ensure no steps are skipped, 
        resources are not wasted, and the final output is a cohesive incident narrative. 
        You see the big picture.""",
        verbose=True,
        allow_delegation=True,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2️⃣ Alert Handler Agent (Tier-1 Analyst)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_alert_handler_agent() -> Agent:
    """
    Reduces noise and decides what deserves attention.
    Role: Tier-1 Triage & Correlation.
    """
    return Agent(
        role="Alert Handler Agent",
        goal="Triages incoming signals, reduces noise, and correlates related events",
        backstory="""You are an expert Tier-1 Security Analyst. Your job is to filter out the noise. 
        You receive thousands of signals but only pass on the ones that matter. You look for 
        related events to group them into a single incident context, preventing alert fatigue.""",
        verbose=True,
        allow_delegation=False,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3️⃣ Threat Analyzer Agent (Threat Understanding)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_threat_analyzer_agent() -> Agent:
    """
    Understands WHAT kind of attack is happening.
    Role: Threat Classification & MITRE Mapping.
    """
    return Agent(
        role="Threat Analyzer Agent",
        goal="Classify the behavior against MITRE ATT&CK and determine attacker intent",
        backstory="""You are a Threat Intelligence Specialist. You don't just see 'failed login'; 
        you see 'Brute Force (T1110)'. You understand the attacker's playbook. You identify 
        Tactics, Techniques, and Procedures (TTPs) and explain the intent behind the events.""",
        verbose=True,
        allow_delegation=False,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4️⃣ Root Cause Agent (Forensic Investigator)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_root_cause_agent() -> Agent:
    """
    Explains HOW and WHY the incident happened.
    Role: Forensic Reconstruction.
    """
    return Agent(
        role="Root Cause Agent",
        goal="Reconstruct the attack timeline and identify the initial entry point",
        backstory="""You are a Senior Forensic Investigator. You walk backwards through time. 
        You connect the dots between the alert and the initial breach. You identify the 
        'Blast Radius' of the attack and determine exactly how the adversary gained access.""",
        verbose=True,
        allow_delegation=False,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5️⃣ Compliance Agent (Regulatory Gatekeeper)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_compliance_agent() -> Agent:
    """
    Ensures regulatory obligations are met.
    Role: Legal & Policy Compliance.
    """
    return Agent(
        role="Compliance Agent",
        goal="Evaluate incident against GDPR, IRDAI, and SOC 2 requirements",
        backstory="""You are the Governance, Risk, and Compliance (GRC) Officer. You don't care about 
        IP addresses; you care about PII, reporting deadlines (72h), and legal exposure. 
        You ensure every incident response aligns with regulatory frameworks.""",
        verbose=True,
        allow_delegation=False,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6️⃣ Response Automation Agent (Controlled SOAR)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_response_automation_agent() -> Agent:
    """
    Executes containment and remediation safely.
    Role: Remediation Planner.
    """
    return Agent(
        role="Response Automation Agent",
        goal="Draft safe, effective containment and remediation plans",
        backstory="""You are the SOAR (Security Orchestration, Automation, and Response) Specialist. 
        You define the counter-measures. You propose actions like 'Isolate Host', 'Revoke Token', 
        or 'Block IP'. You prioritize speed but strictly adhere to safety protocols to avoid business disruption.""",
        verbose=True,
        allow_delegation=False,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Task Definitions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_tasks(signal: DetectionSignal) -> List[Task]:
    """Create the sequential workflow tasks."""
    
    # 1. Orchestration
    orchestrator_task = Task(
        description=f"""
        Analyze the incoming signal context for User: {signal.user}, Type: {signal.signal_type}.
        Determine the scope of the incident response required.
        Identify which specialized agents are needed for this investigation.
        """,
        agent=create_orchestrator_agent(),
        expected_output="Incident Response Plan outlining the investigation strategy."
    )

    # 2. Alert Handling
    triage_task = Task(
        description=f"""
        Review the raw signal events (Count: {len(signal.events)}).
        Extract critical entities (User, Asset, Location, IP).
        Correlate these events into a single cohesive alert narrative.
        Filter out potential false positives or irrelevant noise.
        """,
        agent=create_alert_handler_agent(),
        expected_output="Structured Alert Summary with key entities and noise filtered out."
    )

    # 3. Threat Analysis
    analysis_task = Task(
        description=f"""
        Map the observed behaviors to the MITRE ATT&CK framework.
        Identify the specific Technique ID (e.g., T1078).
        Explain the Attacker's Intent (e.g., Credential Access, Exfiltration).
        Assign a confidence score to this classification.
        """,
        agent=create_threat_analyzer_agent(),
        expected_output="Threat Classification including MITRE mapping and Attacker Intent."
    )

    # 4. Root Cause Analysis
    forensics_task = Task(
        description=f"""
        Trace the attack path backwards from the alert.
        Identify the likely Root Cause (e.g., Phishing, Misconfiguration, Compromised Credential).
        Construct a timeline of the attack progression.
        Define the Blast Radius (what other systems might be affected?).
        """,
        agent=create_root_cause_agent(),
        expected_output="Forensic Timeline and Root Cause Analysis."
    )

    # 5. Compliance Check
    compliance_task = Task(
        description=f"""
        Evaluate if this incident involves PII or sensitive data.
        Check against GDPR and IRDAI reporting requirements.
        Determine if this is a 'Reportable Incident'.
        Calculate the reporting deadline (e.g., T-72 hours).
        """,
        agent=create_compliance_agent(),
        expected_output="Compliance Assessment Report with deadlines and regulatory obligations."
    )

    # 6. Response Planning
    response_task = Task(
        description=f"""
        Based on the analysis, propose specific Remediation Actions.
        Prioritize actions by 'Immediate Containment' vs 'Long-term Eradication'.
        Draft the formal Incident Note for the ticketing system (ServiceNow).
        """,
        agent=create_response_automation_agent(),
        expected_output="Actionable Remediation Plan and Incident Ticket Draft."
    )

    return [
        orchestrator_task,
        triage_task,
        analysis_task,
        forensics_task,
        compliance_task,
        response_task
    ]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Crew Orchestration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_agent_analysis(signal: DetectionSignal) -> Dict[str, Any]:
    """
    Run the full Arxis Agentic System workflow.
    """
    tasks = create_tasks(signal)
    
    crew = Crew(
        agents=[
            create_orchestrator_agent(),
            create_alert_handler_agent(),
            create_threat_analyzer_agent(),
            create_root_cause_agent(),
            create_compliance_agent(),
            create_response_automation_agent()
        ],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )
    
    try:
        result = crew.kickoff()
        
        return {
            "success": True,
            "agent_trace": [
                "Orchestrator Agent",
                "Alert Handler Agent",
                "Threat Analyzer Agent",
                "Root Cause Agent",
                "Compliance Agent",
                "Response Automation Agent"
            ],
            "result": str(result),
            "signal_id": signal.signal_id
        }
    
    except Exception as e:
        print(f"❌ Agent workflow failed: {e}")
        
        # Fallback to rule-based output (Simulate agent path for UI)
        return {
            "success": False,
            "agent_trace": [
                "Orchestrator Agent",
                "Alert Handler Agent",
                "Threat Analyzer Agent",
                "Root Cause Agent",
                "Compliance Agent",
                "Response Automation Agent"
            ],
            "result": f"Alert generated by detection rule: {signal.signal_type}",
            "signal_id": signal.signal_id,
            "error": str(e)
        }
