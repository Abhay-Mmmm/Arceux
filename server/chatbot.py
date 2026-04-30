"""
Intelligent AI Chatbot — Groq LLM + Data-Driven Fallback

Uses Groq API (llama-3.1-8b-instant via GROQ_MODEL_CHAT) for live AI
responses. Falls back to data-driven responses using real storage
data when Groq is unavailable.
"""

import os
from typing import Dict, List, Optional

GROQ_AVAILABLE = False
_groq_client = None
_model_name = os.getenv("GROQ_MODEL_CHAT", "llama-3.1-8b-instant")
_api_key = os.getenv("GROQ_API_KEY_CHAT") or os.getenv("GROQ_API_KEY")

try:
    from groq import Groq

    if _api_key:
        _groq_client = Groq(api_key=_api_key)
        GROQ_AVAILABLE = True
        print(f"Groq chatbot initialised ({_model_name}, key: {_api_key[:8]}...)")
    else:
        print("No chat API key set — chatbot using data fallback")
except ImportError:
    print("groq not installed — chatbot using data fallback")
except Exception as e:
    print(f"Groq init error: {e} — chatbot using data fallback")


_SYSTEM_PROMPT = """You are Arceux AI, a senior Security Operations Center analyst assistant for a financial institution. You have deep expertise in:
- Threat detection and incident response
- MITRE ATT&CK framework (tactics, techniques, procedures)
- Financial sector attack patterns (insider threats, account takeover, data exfiltration, credential abuse)
- Regulatory compliance: IRDAI 6-hour reporting, GDPR 72-hour breach notification, SOC 2, PCI DSS
- Behavioral anomaly detection and ML-based threat scoring

BEHAVIOR RULES:
- Always be concise and actionable — analysts are busy
- When explaining alerts, always include: what happened, why it's suspicious, MITRE ATT&CK technique if applicable, and recommended immediate actions
- When assessing compliance, always mention applicable regulations and deadlines
- For CRITICAL severity alerts, always recommend immediate escalation
- Never say you don't have access to data — the current system state is always injected into your context
- Use markdown formatting (bold, bullet points, headers) — the UI renders it correctly
- Keep responses under 200 words unless the analyst asks for detail"""


QUICK_ACTION_PROMPTS = {
    "explain_last": "Based on the system state above, explain the most recent alert in detail. Include: what happened, the likely attack vector, which MITRE ATT&CK technique this maps to, affected user and asset, and your top 3 recommended immediate actions.",
    "threat_summary": "Based on the system state above, provide a threat summary for the SOC team. Identify the most dangerous ongoing situation, note any patterns across multiple alerts (same user, same asset, coordinated activity), and assess the overall security posture as: CRITICAL / ELEVATED / GUARDED / NORMAL with a one-sentence justification.",
    "recommend_actions": "Based on the system state above, provide prioritized response actions for the SOC team right now. Rank by urgency: IMMEDIATE (do in next 5 minutes), SHORT-TERM (do in next hour), MONITOR (watch but no action yet). Be specific — name the users, assets, and actions.",
    "system_status": "Based on the system state above, give a brief system status report: overall security posture, how many alerts need attention, whether the AI pipeline is functioning, and any compliance deadlines that may be approaching based on CRITICAL alerts detected (IRDAI = 6 hours, GDPR = 72 hours).",
}


def build_context(storage) -> str:
    all_alerts = storage.get_all_alerts()
    recent_alerts = all_alerts[-10:] if len(all_alerts) >= 10 else all_alerts
    agent_states = storage.agent_states
    pipeline_running = storage.pipeline_running
    last_signal_type = storage.last_signal_type
    total_alerts = len(all_alerts)

    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for a in all_alerts:
        sev = a.get("severity", "MEDIUM")
        if sev in severity_counts:
            severity_counts[sev] += 1

    context_lines = [
        "=== CURRENT SYSTEM STATE ===",
        f"Total alerts: {total_alerts}",
        f"By severity: CRITICAL={severity_counts.get('CRITICAL', 0)}, "
        f"HIGH={severity_counts.get('HIGH', 0)}, "
        f"MEDIUM={severity_counts.get('MEDIUM', 0)}, "
        f"LOW={severity_counts.get('LOW', 0)}",
        f"Pipeline running: {pipeline_running}",
        f"Last signal type: {last_signal_type or 'none'}",
        "",
        "=== RECENT ALERTS (most recent first) ===",
    ]

    for i, alert_dict in enumerate(reversed(recent_alerts)):
        severity = alert_dict.get("severity", "UNKNOWN")
        threat_type = alert_dict.get("threat_type", "Unknown")
        user = alert_dict.get("user", "unknown")
        status = alert_dict.get("status", "open")
        timestamp = alert_dict.get("timestamp", "unknown")

        asset = "unknown"
        raw_events = alert_dict.get("raw_events", [])
        if raw_events and len(raw_events) > 0:
            asset = raw_events[0].get("asset", "unknown")

        explanation = alert_dict.get("explanation", "")

        context_lines.append(
            f"{i+1}. [{severity}] {threat_type} | "
            f"User: {user} | Asset: {asset} | "
            f"Status: {status} | "
            f"Detected: {timestamp}"
        )
        if explanation:
            context_lines.append(f"   Analysis: {explanation[:200]}")

    context_lines.append("")
    context_lines.append("=== AGENT PIPELINE STATUS ===")
    for agent_name, state in agent_states.items():
        context_lines.append(
            f"{agent_name}: {state.get('status', 'unknown')} | "
            f"Tasks: {state.get('tasks_completed', 0)} | "
            f"Last run: {state.get('last_run', 'never')}"
        )

    return "\n".join(context_lines)


def _call_groq(messages: List[Dict[str, str]]) -> str:
    """Call Groq and return the response text. Raises on failure."""
    completion = _groq_client.chat.completions.create(
        model=_model_name,
        messages=messages,
        temperature=0.3,
        max_tokens=400,
    )
    return completion.choices[0].message.content


def _build_messages(
    system_prompt: str,
    context: str,
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, str]]:
    """Build the messages list for a Groq call."""
    messages = [{"role": "system", "content": system_prompt + "\n\n" + context}]

    if conversation_history:
        for msg in conversation_history[-12:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})
    return messages


def _get_fallback_explain_last(storage) -> str:
    """Data-driven fallback for explain_last action."""
    if not storage.alerts:
        return "No alerts in system."
    all_alerts = storage.get_all_alerts()
    if not all_alerts:
        return "No alerts in system."
    alert = all_alerts[-1]
    asset = "unknown"
    raw_events = alert.get("raw_events", [])
    if raw_events and len(raw_events) > 0:
        asset = raw_events[0].get("asset", "unknown")
    user = alert.get("user", "unknown")
    severity = alert.get("severity", "UNKNOWN")
    alert_type = alert.get("threat_type", "Unknown")
    detected_at = alert.get("timestamp", "unknown")
    status = alert.get("status", "open")

    return (
        f"Latest alert: [{severity}] {alert_type} on {asset} by {user}. "
        f"Detected {detected_at}. Status: {status}. "
        f"[AI explanation unavailable — Groq rate limit or key missing]"
    )


def _get_fallback_threat_summary(storage) -> str:
    """Data-driven fallback for threat_summary action."""
    all_alerts = storage.get_all_alerts()
    if not all_alerts:
        return "No alerts in system."

    total = len(all_alerts)

    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for a in all_alerts:
        sev = a.get("severity", "MEDIUM")
        if sev in severity_counts:
            severity_counts[sev] += 1

    critical = severity_counts.get('CRITICAL', 0)
    high = severity_counts.get('HIGH', 0)
    medium = severity_counts.get('MEDIUM', 0)

    most_recent = all_alerts[-1]
    recent_type = most_recent.get('threat_type', 'Unknown')
    recent_asset = "unknown"
    raw_events = most_recent.get("raw_events", [])
    if raw_events and len(raw_events) > 0:
        recent_asset = raw_events[0].get("asset", "unknown")

    return (
        f"Current threat posture: {critical} critical, {high} high, "
        f"{medium} medium alerts. Most recent: {recent_type} on {recent_asset}. "
        f"[AI summary unavailable — Groq rate limit or key missing]"
    )


def _get_fallback_recommend_actions(storage) -> str:
    """Data-driven fallback for recommend_actions action."""
    all_alerts = storage.get_all_alerts()
    if not all_alerts:
        return "No alerts requiring action."

    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for a in all_alerts:
        sev = a.get("severity", "MEDIUM")
        if sev in severity_counts:
            severity_counts[sev] += 1

    priority_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
    for sev in priority_order:
        if severity_counts.get(sev, 0) > 0:
            alerts_of_sev = [a for a in all_alerts if a.get('severity') == sev]
            if alerts_of_sev:
                alert = alerts_of_sev[-1]
                user = alert.get('user', 'unknown')
                alert_type = alert.get('threat_type', 'Unknown')
                asset = "unknown"
                raw_events = alert.get("raw_events", [])
                if raw_events and len(raw_events) > 0:
                    asset = raw_events[0].get("asset", "unknown")
                return (
                    f"Priority action: Investigate [{sev}] {alert_type} — "
                    f"{user} on {asset}. Take ownership and run playbook. "
                    f"[AI recommendations unavailable — Groq rate limit or key missing]"
                )

    return "No open alerts requiring immediate action."


def _get_fallback_system_status(storage) -> str:
    """Data-driven fallback for system_status action."""
    total = len(storage.alerts)
    pipeline = 'running' if storage.pipeline_running else 'idle'
    last_signal = storage.last_signal_type or 'none'

    return (
        f"System operational. {total} total alerts. Pipeline: {pipeline}. Last signal: {last_signal}. "
        f"[AI analysis unavailable — Groq rate limit or key missing]"
    )


def _get_fallback_freeform(storage, user_message: str) -> str:
    """Data-driven fallback for free-form messages."""
    total = len(storage.alerts)
    last_signal = storage.last_signal_type or 'none'

    return (
        f"I cannot process your question right now (Groq unavailable). "
        f"Current state: {total} alerts, last signal: {last_signal}."
    )


def get_ai_response(
    user_message: str,
    storage,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Get AI response for a free-form user message.
    Uses Groq when available, falls back to data-driven response.
    """
    context = build_context(storage)

    if GROQ_AVAILABLE:
        try:
            messages = _build_messages(
                _SYSTEM_PROMPT,
                context,
                user_message,
                conversation_history,
            )
            return _call_groq(messages)
        except Exception as e:
            print(f"Groq error: {e} — using data fallback")

    return _get_fallback_freeform(storage, user_message)


def get_quick_action_response(
    action_type: str,
    storage,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Handle predefined quick actions.
    Uses Groq with focused prompts when available; falls back to data-driven responses.
    """
    if action_type not in QUICK_ACTION_PROMPTS:
        return f"Unknown action type: {action_type}"

    context = build_context(storage)
    focused_question = QUICK_ACTION_PROMPTS[action_type]

    if GROQ_AVAILABLE:
        try:
            messages = _build_messages(
                _SYSTEM_PROMPT,
                context,
                focused_question,
                conversation_history,
            )
            return _call_groq(messages)
        except Exception as e:
            print(f"Groq error for quick action '{action_type}': {e} — using data fallback")

    if action_type == "explain_last":
        return _get_fallback_explain_last(storage)
    elif action_type == "threat_summary":
        return _get_fallback_threat_summary(storage)
    elif action_type == "recommend_actions":
        return _get_fallback_recommend_actions(storage)
    elif action_type == "system_status":
        return _get_fallback_system_status(storage)

    return f"Cannot process action: {action_type}"