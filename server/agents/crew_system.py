"""
Arceux Agentic System - Specialized SOC Agents
Signal-type routed, per-agent API keys, output-limited.
"""

import os
import time
from datetime import datetime, timezone
from crewai import Agent, Task, Crew, Process
from typing import Dict, Any, List, Tuple, Optional

from models import DetectionSignal


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Configuration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_FALLBACK_KEY = os.getenv("GROQ_API_KEY")
_MODEL_AGENTS = os.getenv("GROQ_MODEL_AGENTS", "llama-3.3-70b-versatile")

_AGENT_KEYS: Dict[str, Optional[str]] = {
    "Orchestrator Agent":        os.getenv("GROQ_API_KEY_ORCHESTRATOR") or _FALLBACK_KEY,
    "Alert Handler Agent":       os.getenv("GROQ_API_KEY_ALERT_HANDLER") or _FALLBACK_KEY,
    "Threat Analyzer Agent":     os.getenv("GROQ_API_KEY_THREAT_ANALYZER") or _FALLBACK_KEY,
    "Root Cause Agent":          os.getenv("GROQ_API_KEY_ROOT_CAUSE") or _FALLBACK_KEY,
    "Compliance Agent":          os.getenv("GROQ_API_KEY_COMPLIANCE") or _FALLBACK_KEY,
    "Response Automation Agent": os.getenv("GROQ_API_KEY_RESPONSE") or _FALLBACK_KEY,
}

for _name, _key in _AGENT_KEYS.items():
    if _key:
        print(f"[AGENT] {_name} using key: {_key[:8]}...")
    else:
        print(f"[AGENT] {_name}: no key — template fallback active")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Signal-Type Routing Table
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_ROUTING: Dict[str, List[str]] = {
    "BRUTE_FORCE":      ["Alert Handler Agent", "Threat Analyzer Agent", "Response Automation Agent"],
    "SUSPICIOUS_LOGIN": ["Alert Handler Agent", "Threat Analyzer Agent", "Compliance Agent"],
    "INSIDER_THREAT":   [
        "Orchestrator Agent", "Alert Handler Agent", "Threat Analyzer Agent",
        "Root Cause Agent", "Compliance Agent", "Response Automation Agent",
    ],
    "ANOMALOUS_ACCESS": ["Alert Handler Agent", "Root Cause Agent", "Compliance Agent"],
    "DEFAULT":          ["Alert Handler Agent", "Threat Analyzer Agent"],
}

ALL_AGENT_NAMES = [
    "Orchestrator Agent",
    "Alert Handler Agent",
    "Threat Analyzer Agent",
    "Root Cause Agent",
    "Compliance Agent",
    "Response Automation Agent",
]


def get_agents_for_signal(signal_type: str) -> List[str]:
    """Return the agent names to run for this signal type."""
    return _ROUTING.get(signal_type, _ROUTING["DEFAULT"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LLM Factory
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _make_llm(agent_name: str):
    """Build an LLM instance for a specific agent using its dedicated key."""
    key = _AGENT_KEYS.get(agent_name)
    if not key:
        return None
    try:
        from crewai import LLM
        return LLM(model=f"groq/{_MODEL_AGENTS}", api_key=key)
    except Exception:
        # Older CrewAI without LLM class — string format (uses GROQ_API_KEY from env)
        return f"groq/{_MODEL_AGENTS}"


def _llm_kwargs(agent_name: str) -> Dict[str, Any]:
    llm = _make_llm(agent_name)
    return {"llm": llm} if llm else {}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent + Task Factories
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _build_orchestrator(signal: DetectionSignal) -> Tuple[Agent, Task]:
    name = "Orchestrator Agent"
    agent = Agent(
        role=name,
        goal="Coordinate the incident response lifecycle and manage global incident context",
        backstory="SOC Incident Commander. Direct the team efficiently. See the big picture.",
        verbose=True,
        allow_delegation=True,
        max_iter=1,
        memory=False,
        **_llm_kwargs(name),
    )
    task = Task(
        description=(
            f"Incident for User: {signal.user}, Type: {signal.signal_type}. "
            "Determine scope and which agents are needed."
        ),
        agent=agent,
        expected_output=(
            "Max 60 words. JSON with keys: incident_id, priority, assigned_agents, coordination_notes"
        ),
    )
    return agent, task


def _build_alert_handler(signal: DetectionSignal) -> Tuple[Agent, Task]:
    name = "Alert Handler Agent"
    agent = Agent(
        role=name,
        goal="Triages incoming signals, reduces noise, and correlates related events",
        backstory="Expert Tier-1 Security Analyst. Filter noise, extract signal. Group related events.",
        verbose=True,
        allow_delegation=False,
        max_iter=1,
        memory=False,
        **_llm_kwargs(name),
    )
    task = Task(
        description=(
            f"Review {len(signal.events)} events for User: {signal.user} "
            f"(Signal: {signal.signal_type}). Extract entities. Correlate and filter noise."
        ),
        agent=agent,
        expected_output=(
            "Max 80 words. Bullet points only: severity, deduplicated_count, top_indicators, noise_assessment"
        ),
    )
    return agent, task


def _build_threat_analyzer(signal: DetectionSignal) -> Tuple[Agent, Task]:
    name = "Threat Analyzer Agent"
    agent = Agent(
        role=name,
        goal="Classify the behavior against MITRE ATT&CK and determine attacker intent",
        backstory="Threat Intelligence Specialist. Map behaviors to MITRE. Identify attacker TTPs.",
        verbose=True,
        allow_delegation=False,
        max_iter=1,
        memory=False,
        **_llm_kwargs(name),
    )
    task = Task(
        description=(
            f"Map {signal.signal_type} behavior for User: {signal.user} to MITRE ATT&CK. "
            "Identify technique ID and attacker intent."
        ),
        agent=agent,
        expected_output=(
            "Max 100 words. MITRE tactic, technique ID, attacker_intent, "
            "confidence_score, key_evidence (3 bullets max)"
        ),
    )
    return agent, task


def _build_root_cause(signal: DetectionSignal) -> Tuple[Agent, Task]:
    name = "Root Cause Agent"
    agent = Agent(
        role=name,
        goal="Reconstruct the attack timeline and identify the initial entry point",
        backstory="Senior Forensic Investigator. Walk backwards through time. Connect the dots.",
        verbose=True,
        allow_delegation=False,
        max_iter=1,
        memory=False,
        **_llm_kwargs(name),
    )
    task = Task(
        description=(
            f"Trace attack path for {signal.signal_type} incident affecting User: {signal.user}. "
            "Identify root cause, blast radius, and affected assets."
        ),
        agent=agent,
        expected_output=(
            "Max 100 words. Timeline: initial_vector, propagation_steps (max 3), "
            "affected_assets, blast_radius"
        ),
    )
    return agent, task


def _build_compliance(signal: DetectionSignal) -> Tuple[Agent, Task]:
    name = "Compliance Agent"
    agent = Agent(
        role=name,
        goal="Evaluate incident against GDPR, IRDAI, and SOC 2 requirements",
        backstory="GRC Officer. Focus on PII, reporting deadlines (72h), and legal exposure.",
        verbose=True,
        allow_delegation=False,
        max_iter=1,
        memory=False,
        **_llm_kwargs(name),
    )
    task = Task(
        description=(
            f"Evaluate {signal.signal_type} incident for User: {signal.user} "
            "against GDPR, IRDAI, and SOC 2. Determine reportability and deadlines."
        ),
        agent=agent,
        expected_output=(
            "Max 80 words. Bullet points: applicable_regulations, reportable (yes/no), "
            "deadline, required_actions (2 max)"
        ),
    )
    return agent, task


def _build_response_automation(signal: DetectionSignal) -> Tuple[Agent, Task]:
    name = "Response Automation Agent"
    agent = Agent(
        role=name,
        goal="Draft safe, effective containment and remediation plans",
        backstory="SOAR Specialist. Define counter-measures. Prioritize speed with safety protocols.",
        verbose=True,
        allow_delegation=False,
        max_iter=1,
        memory=False,
        **_llm_kwargs(name),
    )
    task = Task(
        description=(
            f"Propose containment and remediation actions for {signal.signal_type} "
            f"affecting User: {signal.user}. Distinguish immediate vs. short-term actions."
        ),
        agent=agent,
        expected_output=(
            "Max 80 words. Prioritized actions: immediate (1-2 items), "
            "short_term (1-2 items), escalate_to_human (yes/no)"
        ),
    )
    return agent, task


_AGENT_BUILDERS: Dict[str, Any] = {
    "Orchestrator Agent":        _build_orchestrator,
    "Alert Handler Agent":       _build_alert_handler,
    "Threat Analyzer Agent":     _build_threat_analyzer,
    "Root Cause Agent":          _build_root_cause,
    "Compliance Agent":          _build_compliance,
    "Response Automation Agent": _build_response_automation,
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Crew Orchestration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_agent_analysis(signal: DetectionSignal) -> Dict[str, Any]:
    """
    Run the Arceux agent pipeline for the given signal.
    Routes to a subset of agents based on signal type.
    Only updates storage state for agents that actually ran.
    """
    signal_type = signal.signal_type.value
    selected_names = get_agents_for_signal(signal_type)

    print(f"[CREW] Signal: {signal_type} → Running {len(selected_names)} agents: {selected_names}")

    try:
        from storage import storage as _storage
        _has_storage = True
    except Exception:
        _has_storage = False

    start_time = time.time()
    start_iso = datetime.now(timezone.utc).isoformat()

    if _has_storage:
        # Reset stale error states on agents NOT selected for this run (routing skipped them).
        # Prevents non-participant agents from showing "error" from a previous failed run.
        for name in ALL_AGENT_NAMES:
            if name not in selected_names:
                if _storage.agent_states.get(name, {}).get("status") == "error":
                    _storage.update_agent_state(name, {"status": "idle"})
        for name in selected_names:
            _storage.update_agent_state(name, {"status": "running", "last_run": start_iso})

    try:
        agents: List[Agent] = []
        tasks: List[Task] = []
        for name in selected_names:
            agent, task = _AGENT_BUILDERS[name](signal)
            agents.append(agent)
            tasks.append(task)

        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=False,
        )

        result = crew.kickoff()
        elapsed_ms = int((time.time() - start_time) * 1000)
        result_str = str(result)

        if _has_storage:
            trace_lines = [line.strip() for line in result_str.splitlines() if line.strip()][:8]
            for name in selected_names:
                state = _storage.agent_states.get(name, {})
                _storage.update_agent_state(name, {
                    "status": "completed",
                    "tasks_completed": state.get("tasks_completed", 0) + 1,
                    "execution_count": state.get("execution_count", 0) + 1,
                    "total_execution_time_ms": state.get("total_execution_time_ms", 0) + elapsed_ms,
                    "last_execution_trace": trace_lines,
                })

        return {
            "success": True,
            "agent_trace": selected_names,
            "result": result_str,
            "signal_id": signal.signal_id,
        }

    except Exception as e:
        print(f"Agent workflow failed: {e}")
        if _has_storage:
            for name in selected_names:
                _storage.update_agent_state(name, {"status": "error"})
        return {
            "success": False,
            "agent_trace": selected_names,
            "result": f"Alert generated by detection rule: {signal.signal_type}",
            "signal_id": signal.signal_id,
            "error": str(e),
        }
