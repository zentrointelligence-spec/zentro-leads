"""
Competitor tool detection.
Scans company website text for mentions of known competitor tools.
"""

from __future__ import annotations

from typing import Any

# Map competitor name → canonical tool name
COMPETITOR_KEYWORDS: dict[str, str] = {
    # CRM / Sales
    "salesforce": "Salesforce",
    "hubspot": "HubSpot",
    "pipedrive": "Pipedrive",
    "zoho crm": "Zoho CRM",
    "freshsales": "Freshsales",

    # Lead gen / data
    "apollo": "Apollo",
    "apollo.io": "Apollo",
    "zoominfo": "ZoomInfo",
    "lusha": "Lusha",
    "cognism": "Cognism",
    "rocketreach": "RocketReach",
    "hunter.io": "Hunter",
    "hunter": "Hunter",
    "seamless.ai": "Seamless.AI",
    "seamlessai": "Seamless.AI",
    "clearbit": "Clearbit",
    "lead411": "Lead411",
    "uplead": "UpLead",

    # Outreach / engagement
    " outreach": "Outreach",
    "salesloft": "Salesloft",
    "reply.io": "Reply.io",
    "woodpecker": "Woodpecker",
    " Lemlist": "Lemlist",
    "lemlist": "Lemlist",
    "instantly": "Instantly",
    "smartlead": "Smartlead",
    "quickmail": "QuickMail",

    # Marketing automation
    "mailchimp": "Mailchimp",
    "activecampaign": "ActiveCampaign",
    "marketo": "Marketo",
    "pardot": "Pardot",
    "klaviyo": "Klaviyo",

    # Enrichment / intent
    "bombora": "Bombora",
    "6sense": "6sense",
    "demandbase": "Demandbase",
    "terminus": "Terminus",
    "madkudu": "MadKudu",
}


def detect_competitor_tools(website_text: str | None) -> list[dict[str, Any]]:
    """
    Scan website text for competitor tool mentions.
    Returns list of detected tools with confidence.
    """
    if not website_text:
        return []

    text_lower = website_text.lower()
    detected: list[dict[str, Any]] = []
    seen: set[str] = set()

    for keyword, canonical in COMPETITOR_KEYWORDS.items():
        if canonical in seen:
            continue
        if keyword.lower() in text_lower:
            seen.add(canonical)
            detected.append({
                "tool": canonical,
                "keyword_matched": keyword.strip(),
                "confidence": 0.85,
                "source": "website_text",
            })

    return detected


def get_competitor_signal(website_text: str | None) -> dict[str, Any]:
    """
    High-level helper: return competitor detection signal.
    """
    tools = detect_competitor_tools(website_text)
    if not tools:
        return {
            "competitor_detected": False,
            "tools": [],
            "primary_tool": None,
        }

    primary = tools[0]["tool"]
    return {
        "competitor_detected": True,
        "tools": [t["tool"] for t in tools],
        "primary_tool": primary,
        "source": "website_scan",
    }
