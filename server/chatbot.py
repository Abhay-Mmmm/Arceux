"""
Intelligent AI Chatbot — Groq LLM + Smart Template Fallback

Uses Groq API (llama-3.3-70b-versatile) for live AI responses.
Falls back to template-based responses when Groq is unavailable.
"""

import os
import json
from typing import Dict

# Try to initialise Groq client
GROQ_AVAILABLE = False
_groq_client = None
_model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

try:
    from groq import Groq

    _api_key = os.getenv("GROQ_API_KEY")

    if _api_key:
        _groq_client = Groq(api_key=_api_key)
        GROQ_AVAILABLE = True
        print(f"Groq chatbot initialised ({_model_name})")
    else:
        print("GROQ_API_KEY not set — chatbot using template fallback")
except ImportError:
    print("groq not installed — chatbot using template fallback")
except Exception as e:
    print(f"Groq init error: {e} — chatbot using template fallback")


_SYSTEM_PROMPT = (
    "You are a senior SOC analyst with deep threat intelligence expertise working for Arceux, "
    "an AI-native security operations platform. You analyze security alerts and provide "
    "concise, actionable guidance to the security team. "
    "Use markdown formatting. Be professional and focus on security recommendations. "
    "Keep responses under 300 words unless deep analysis is requested."
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Groq Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _build_context_text(context: Dict) -> str:
    """Summarise alert context into text for the LLM."""
    stats = context.get("alert_stats", {})
    last_alert = context.get("last_alert", {})
    recent = context.get("recent_alerts", [])

    parts = [
        f"Alert stats: {stats.get('total', 0)} total — "
        f"{stats.get('critical', 0)} critical, {stats.get('high', 0)} high, "
        f"{stats.get('medium', 0)} medium, {stats.get('low', 0)} low."
    ]

    if last_alert:
        parts.append(
            f"Latest alert: {last_alert.get('title')} ({last_alert.get('severity')}) — "
            f"User: {last_alert.get('user')}, Asset: {last_alert.get('asset')}. "
            f"Details: {str(last_alert.get('description', ''))[:200]}"
        )

    if recent:
        recent_json = json.dumps(recent[-5:], indent=2)
        parts.append(f"Recent alerts (last 5):\n{recent_json}")

    return "\n".join(parts)


def _call_groq(user_message: str) -> str:
    """Call Groq and return the response text. Raises on failure."""
    completion = _groq_client.chat.completions.create(
        model=_model_name,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        max_tokens=800,
    )
    return completion.choices[0].message.content


def _quick_action_prompt(action_type: str, context: Dict) -> str:
    """Build a focused user prompt for a quick action type."""
    ctx = _build_context_text(context)
    last = context.get("last_alert", {})

    if action_type == "explain_last":
        return (
            f"Security Context:\n{ctx}\n\n"
            f"Task: Provide a detailed explanation of the latest security alert.\n"
            f"Alert: {last.get('title')} ({last.get('severity')} severity)\n"
            f"User: {last.get('user')}, Asset: {last.get('asset')}\n"
            f"Details: {last.get('description', '')}\n\n"
            f"Include: what happened, likely attacker intent, and 3 specific recommended actions."
        )
    elif action_type == "threat_summary":
        return (
            f"Security Context:\n{ctx}\n\n"
            "Task: Summarise the current threat landscape across all active alerts. "
            "Include trending threats, most targeted users/assets, and overall risk posture."
        )
    elif action_type == "recommend_actions":
        return (
            f"Security Context:\n{ctx}\n\n"
            "Task: Provide a prioritised list of recommended security actions the team "
            "should take right now. Organise by: immediate containment, investigation steps, "
            "and proactive hardening."
        )
    elif action_type == "system_status":
        return (
            f"Security Context:\n{ctx}\n\n"
            "Task: Provide a brief security posture assessment. Include overall risk level, "
            "key active threats, and whether immediate action is required."
        )
    else:
        return (
            f"Security Context:\n{ctx}\n\n"
            f"Task: Answer this security question concisely: {action_type}"
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Template Fallback (no API key needed)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_smart_response(prompt_type: str, context: Dict) -> str:
    """Template-based responses using real alert data."""
    if not context:
        return "I don't have any alert data to analyse at the moment. The system appears to be initialising."

    last_alert = context.get("last_alert", {})
    recent_alerts = context.get("recent_alerts", [])
    stats = context.get("alert_stats", {})

    if prompt_type == "explain_last":
        if not last_alert:
            return "No recent alerts found in the system."

        title = last_alert.get("title", "Unknown Threat")
        severity = last_alert.get("severity", "UNKNOWN")
        user = last_alert.get("user", "unknown")
        asset = last_alert.get("asset", "unknown")
        desc = last_alert.get("description", "")

        response = "## Latest Alert Analysis\n\n"
        response += f"**Threat Type:** {title} ({severity} severity)\n\n"
        response += f"**Affected Systems:**\n- User: `{user}`\n- Asset: `{asset}`\n\n"

        if "INSIDER" in title.upper():
            response += "**Analysis:** Insider threat pattern detected. Behaviour deviates from normal baseline.\n\n"
            response += "**Recommended Actions:**\n1. Verify identity via out-of-band communication\n2. Review access logs\n3. Suspend account pending investigation\n"
        elif "BRUTE FORCE" in title.upper():
            response += "**Analysis:** Credential stuffing / brute force attack detected.\n\n"
            response += "**Recommended Actions:**\n1. Block source IP immediately\n2. Reset targeted user's password\n3. Enable MFA\n"
        elif "SUSPICIOUS LOGIN" in title.upper():
            response += "**Analysis:** Login from unusual location — possible account compromise.\n\n"
            response += "**Recommended Actions:**\n1. Contact user to verify login\n2. Review concurrent sessions\n3. Check for data exfiltration\n"
        else:
            response += f"**Analysis:** {desc[:300]}\n\n"
            response += "**Recommended Actions:**\n1. Investigate affected user and asset\n2. Review related logs\n3. Isolate asset if threat confirmed\n"

        return response

    elif prompt_type == "threat_summary":
        total = stats.get("total", 0)
        critical = stats.get("critical", 0)
        high = stats.get("high", 0)

        response = "## Current Threat Landscape\n\n"
        response += f"**Alert Summary:**\n- Total: {total}\n- Critical: {critical}\n- High: {high}\n"
        response += f"- Medium: {stats.get('medium', 0)}\n- Low: {stats.get('low', 0)}\n\n"

        if critical > 0:
            response += f"**HIGH RISK:** {critical} critical alert(s) require immediate attention.\n\n"

        if recent_alerts:
            threat_types: Dict[str, int] = {}
            users: Dict[str, int] = {}
            for alert in recent_alerts:
                t = alert.get("title", "Unknown")
                u = alert.get("user", "unknown")
                threat_types[t] = threat_types.get(t, 0) + 1
                users[u] = users.get(u, 0) + 1
            most_common = max(threat_types.items(), key=lambda x: x[1])
            response += f"**Trending Threat:** {most_common[0]} ({most_common[1]} occurrences)\n\n"
            most_targeted = max(users.items(), key=lambda x: x[1])
            if most_targeted[1] > 1:
                response += f"**Most Affected User:** {most_targeted[0]} ({most_targeted[1]} alerts)\n\n"

        response += "**Status:** Active monitoring continues. Review high-priority alerts first."
        return response

    elif prompt_type == "recommend_actions":
        response = "## Recommended Priority Actions\n\n"
        critical = stats.get("critical", 0)
        high = stats.get("high", 0)

        if critical > 0:
            response += f"**1. Address Critical Alerts ({critical})**\n   - Triage all critical severity alerts\n   - Escalate to senior analyst if needed\n\n"
        if high > 0:
            response += f"**2. Review High Priority Alerts ({high})**\n   - Assess lateral movement risk\n   - Update detection rules if new patterns emerge\n\n"
        if recent_alerts and len(recent_alerts) > 5:
            response += f"**3. Pattern Analysis**\n   - {len(recent_alerts)} recent alerts — look for common indicators\n   - Consider automated response playbooks\n\n"
        response += "**4. Proactive Measures**\n   - Update security baselines\n   - Review user access privileges\n   - Schedule security awareness training"
        return response

    elif prompt_type == "system_status":
        total = stats.get("total", 0)
        critical = stats.get("critical", 0)

        if critical > 0:
            status_label = "**ELEVATED RISK**"
        elif total > 50:
            status_label = "**HIGH ACTIVITY**"
        else:
            status_label = "**NORMAL OPERATIONS**"

        response = f"## System Security Status\n\n{status_label}\n\n"
        response += f"**Current Metrics:**\n- Active Alerts: {total}\n- Critical Issues: {critical}\n"
        response += "- Detection Coverage: Active\n- Agent Processing: Operational\n\n"
        response += (
            f"**Action Required:** {critical} critical alert(s) need immediate investigation.\n"
            if critical > 0
            else "**Status:** All systems operating within normal parameters.\n"
        )
        return response

    return "I can help you with security analysis. Try asking about alerts, threats, or system status."


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Public Interface
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_ai_response(user_message: str, context: Dict = None) -> str:
    """
    Get AI response for a free-form user message.
    Tries Groq first; falls back to smart templates.
    """
    if GROQ_AVAILABLE and context:
        try:
            ctx = _build_context_text(context)
            prompt = (
                f"Security Context:\n{ctx}\n\n"
                f"Analyst question: {user_message}"
            )
            return _call_groq(prompt)
        except Exception as e:
            print(f"Groq error: {e} — using template fallback")

    if not context:
        return "I don't have enough context. Please ensure the system has alert data."

    message_lower = user_message.lower()
    if any(w in message_lower for w in ["last", "recent", "latest", "newest"]):
        return generate_smart_response("explain_last", context)
    elif any(w in message_lower for w in ["summary", "overview", "situation"]):
        return generate_smart_response("threat_summary", context)
    elif any(w in message_lower for w in ["do", "action", "recommend", "fix", "handle"]):
        return generate_smart_response("recommend_actions", context)
    elif any(w in message_lower for w in ["status", "health", "operational"]):
        return generate_smart_response("system_status", context)
    else:
        stats = context.get("alert_stats", {})
        last_alert = context.get("last_alert", {})
        response = f"Tracking {stats.get('total', 0)} alerts in your environment.\n\n"
        if last_alert:
            response += f"Latest: {last_alert.get('title', 'Unknown')} affecting {last_alert.get('user', 'unknown')}.\n\n"
        response += "Ask me about specific alerts, threat summaries, or recommended actions!"
        return response


def get_quick_action_response(action_type: str, context: Dict = None) -> str:
    """
    Handle predefined quick actions.
    Tries Groq with a focused prompt; falls back to templates.
    """
    if not context:
        return "No alert data available for analysis."

    if GROQ_AVAILABLE:
        try:
            prompt = _quick_action_prompt(action_type, context)
            return _call_groq(prompt)
        except Exception as e:
            print(f"Groq error for quick action '{action_type}': {e} — using fallback")

    return generate_smart_response(action_type, context)
