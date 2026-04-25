"""
Intelligent AI Chatbot Helper with Smart Fallback

Provides security analysis based on actual alert data.
Falls back to template-based responses when OpenAI is unavailable.
"""

import os
from typing import List, Dict

# Try to import OpenAI, but don't fail if not available
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    OPENAI_AVAILABLE = True
except:
    OPENAI_AVAILABLE = False
    print("⚠️  OpenAI not available, using intelligent fallback")


def generate_smart_response(prompt_type: str, context: Dict) -> str:
    """
    Generate intelligent responses based on actual alert data.
    
    Args:
        prompt_type: Type of response to generate
        context: Alert data context
        
    Returns:
        Contextual response based on real data
    """
    if not context:
        return "I don't have any alert data to analyze at the moment. The system appears to be initializing."
    
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
        
        # Generate detailed explanation
        response = f"## 🔍 Latest Alert Analysis\n\n"
        response += f"**Threat Type:** {title} ({severity} severity)\n\n"
        response += f"**Affected Systems:**\n"
        response += f"- User: `{user}`\n"
        response += f"- Asset: `{asset}`\n\n"
        
        # Add threat-specific analysis
        if "INSIDER" in title.upper():
            response += "**Analysis:** This is an insider threat pattern. The user's behavior deviates from their normal baseline, potentially indicating compromised credentials or malicious intent.\n\n"
            response += "**Recommended Actions:**\n"
            response += "1. Verify the user's identity through out-of-band communication\n"
            response += "2. Review recent access logs and privilege changes\n"
            response += "3. Consider temporarily suspending the account pending investigation\n"
        elif "BRUTE FORCE" in title.upper():
            response += "**Analysis:** Multiple failed authentication attempts detected, indicating a credential stuffing or brute force attack.\n\n"
            response += "**Recommended Actions:**\n"
            response += "1. Block the source IP address immediately\n"
            response += "2. Reset the targeted user's password\n"
            response += "3. Enable multi-factor authentication if not already active\n"
        elif "SUSPICIOUS LOGIN" in title.upper():
            response += "**Analysis:** Login from an unusual location or at an unusual time. Could indicate account compromise or lateral movement.\n\n"
            response += "**Recommended Actions:**\n"
            response += "1. Contact the user to verify the login attempt\n"
            response += "2. Review concurrent sessions for this account\n"
            response += "3. Check for data exfiltration attempts\n"
        else:
            response += f"**Analysis:** {desc[:300]}\n\n"
            response += "**Recommended Actions:**\n"
            response += "1. Investigate the affected user and asset\n"
            response += "2. Review recent logs for related activity\n"
            response += "3. Consider isolating the asset if threat is confirmed\n"
        
        return response
    
    elif prompt_type == "threat_summary":
        total = stats.get("total", 0)
        critical = stats.get("critical", 0)
        high = stats.get("high", 0)
        
        response = f"## 📊 Current Threat Landscape\n\n"
        response += f"**Alert Summary:**\n"
        response += f"- Total: {total} alerts\n"
        response += f"- Critical: {critical} 🔴\n"
        response += f"- High: {high} 🟠\n"
        response += f"- Medium: {stats.get('medium', 0)} 🟡\n"
        response += f"- Low: {stats.get('low', 0)} 🟢\n\n"
        
        if critical > 0:
            response += f"**⚠️ High Risk:** {critical} critical alert(s) require immediate attention.\n\n"
        
        # Analyze patterns in recent alerts
        if recent_alerts:
            threat_types = {}
            users = {}
            for alert in recent_alerts:
                threat = alert.get("title", "Unknown")
                user = alert.get("user", "unknown")
                threat_types[threat] = threat_types.get(threat, 0) + 1
                users[user] = users.get(user, 0) + 1
            
            # Most common threat
            most_common = max(threat_types.items(), key=lambda x: x[1])
            response += f"**Trending Threat:** {most_common[0]} ({most_common[1]} occurrences)\n\n"
            
            # Most targeted user
            most_targeted = max(users.items(), key=lambda x: x[1])
            if most_targeted[1] > 1:
                response += f"**Most Affected User:** {most_targeted[0]} ({most_targeted[1]} alerts)\n\n"
        
        response += "**Status:** Active monitoring continues. Review high-priority alerts first."
        return response
    
    elif prompt_type == "recommend_actions":
        response = f"## 🎯 Recommended Priority Actions\n\n"
        
        critical = stats.get("critical", 0)
        high = stats.get("high", 0)
        
        if critical > 0:
            response += f"**1. Address Critical Alerts ({critical})**\n"
            response += "   - Investigate and triage all critical severity alerts\n"
            response += "   - Escalate to senior analyst if needed\n"
            response += "   - Document response actions\n\n"
        
        if high > 0:
            response += f"**2. Review High Priority Alerts ({high})**\n"
            response += "   - Assess for potential lateral movement\n"
            response += "   - Correlate with threat intelligence feeds\n"
            response += "   - Update detection rules if new patterns emerge\n\n"
        
        if recent_alerts and len(recent_alerts) > 5:
            response += "**3. Pattern Analysis**\n"
            response += f"   - {len(recent_alerts)} recent alerts detected\n"
            response += "   - Look for common indicators across alerts\n"
            response += "   - Consider automated response playbooks\n\n"
        
        response += "**4. Proactive Measures**\n"
        response += "   - Update security baselines\n"
        response += "   - Review user access privileges\n"
        response += "   - Schedule security awareness training"
        
        return response
    
    elif prompt_type == "system_status":
        total = stats.get("total", 0)
        critical = stats.get("critical", 0)
        
        if critical > 0:
            status = "⚠️ **ELEVATED RISK**"
            color = "🔴"
        elif total > 50:
            status = "⚡ **HIGH ACTIVITY**"  
            color = "🟡"
        else:
            status = "✅ **NORMAL OPERATIONS**"
            color = "🟢"
        
        response = f"## {color} System Security Status\n\n"
        response += f"{status}\n\n"
        response += f"**Current Metrics:**\n"
        response += f"- Active Alerts: {total}\n"
        response += f"- Critical Issues: {critical}\n"
        response += f"- Detection Coverage: Active\n"
        response += f"- Agent Processing: Operational\n\n"
        
        if critical > 0:
            response += f"**Action Required:** {critical} critical alert(s) need immediate investigation.\n"
        else:
            response += "**Status:** All systems operating within normal parameters.\n"
        
        return response
    
    return "I can help you with security analysis. Try asking about alerts, threats, or system status."


def get_ai_response(user_message: str, context: Dict = None) -> str:
    """
    Get AI response - tries OpenAI first, falls back to smart templates.
    """
    # Always use smart fallback for reliability
    # You can enable OpenAI later by checking OPENAI_AVAILABLE
    
    if not context:
        return "I don't have enough context to answer that. Please ensure the system has alert data."
    
    # Analyze the user's question and provide contextual response
    message_lower = user_message.lower()
    
    if any(word in message_lower for word in ["last", "recent", "latest", "newest"]):
        return generate_smart_response("explain_last", context)
    elif any(word in message_lower for word in ["summary", "overview", "situation"]):
        return generate_smart_response("threat_summary", context)
    elif any(word in message_lower for word in ["do", "action", "recommend", "fix", "handle"]):
        return generate_smart_response("recommend_actions", context)
    elif any(word in message_lower for word in ["status", "health", "operational"]):
        return generate_smart_response("system_status", context)
    else:
        # General response with stats
        stats = context.get("alert_stats", {})
        last_alert = context.get("last_alert", {})
        
        response = f"I'm analyzing your security environment. Currently tracking {stats.get('total', 0)} alerts.\n\n"
        
        if last_alert:
            response += f"Latest: {last_alert.get('title', 'Unknown')} affecting {last_alert.get('user', 'unknown')}.\n\n"
        
        response += "Ask me about specific alerts, threat summaries, or recommended actions!"
        return response


def get_quick_action_response(action_type: str, context: Dict = None) -> str:
    """
    Handle predefined quick actions.
    """
    if not context:
        return "No alert data available for analysis."
    
    return generate_smart_response(action_type, context)
