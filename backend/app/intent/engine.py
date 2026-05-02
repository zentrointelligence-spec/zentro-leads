"""
Intent signal orchestrator.
Combines hiring, funding, competitor detection into actionable signals + WHY NOW urgency.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from loguru import logger

from app.intent.competitor_detector import get_competitor_signal
from app.intent.rss_monitor import match_funding_to_company, scan_all_rss_feeds
# Wellfound scraper disabled — returns 403 Forbidden
# from app.intent.wellfound_scraper import get_hiring_signal


def detect_expanding_signal(
    is_hiring: bool,
    funding_detected: bool,
    job_count: int = 0,
) -> dict[str, Any]:
    """
    Expanding signal = hiring + (funding OR 5+ open roles).
    Returns signal dict with reasoning.
    """
    expanding = False
    reasons: list[str] = []

    if is_hiring:
        reasons.append(f"Hiring for {job_count} open roles")
    if funding_detected:
        reasons.append("Recent funding received")

    if is_hiring and funding_detected:
        expanding = True
    elif is_hiring and job_count >= 5:
        expanding = True
        reasons.append("Aggressive hiring indicates expansion")

    return {
        "signal": "expanding",
        "detected": expanding,
        "reasons": reasons,
        "components": {
            "hiring": is_hiring,
            "funding": funding_detected,
            "job_count": job_count,
        },
    }


def build_why_now_message(
    signals: list[str],
    signal_details: dict[str, Any],
    company_name: str | None = None,
) -> str:
    """
    Build a one-sentence WHY NOW urgency message for outreach.
    Example: "Funded 12 days ago — contact before they hire a competitor"
    """
    cname = company_name or "This company"
    now = datetime.now(timezone.utc)

    # Priority order: funding > expanding > hiring > competitor > news
    funding_detail = signal_details.get("funding")
    if funding_detail and "published_at" in funding_detail:
        pub_str = funding_detail["published_at"]
        try:
            pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            days_ago = (now - pub_dt).days
            if days_ago <= 30:
                if days_ago <= 7:
                    return f"{cname} raised funding just {days_ago} days ago — they have budget NOW."
                return f"{cname} raised funding {days_ago} days ago — contact before they commit budget elsewhere."
        except Exception:
            pass
        return f"{cname} recently raised funding — they have fresh budget to spend."

    expanding_detail = signal_details.get("expanding")
    if expanding_detail and expanding_detail.get("detected"):
        reasons = expanding_detail.get("reasons", [])
        reason = reasons[0] if reasons else "actively expanding"
        return f"{cname} is {reason.lower()} — strike while they're growing."

    if "hiring" in signals:
        return f"{cname} is hiring right now — they need solutions to support growth."

    competitor_detail = signal_details.get("competitor")
    if competitor_detail and competitor_detail.get("competitor_detected"):
        tool = competitor_detail.get("primary_tool", "a competitor")
        return f"{cname} uses {tool} — show them why LeadRadar is the smarter choice."

    if "in_the_news" in signals:
        return f"{cname} is in the news — timing is perfect to reach out."

    return f"{cname} matches your ICP perfectly — ideal time to connect."


async def enrich_company_intent(
    company_name: str,
    website_text: str | None,
    existing_signals: list[str],
    rss_articles: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Full intent enrichment pipeline for a single company.
    Runs Wellfound, RSS funding check, and competitor detection in parallel.
    Pass rss_articles to avoid re-fetching feeds for every company.
    """
    logger.info(f"Enriching intent for {company_name}")

    # Run checks concurrently
    # hiring_task = get_hiring_signal(company_name)  # Wellfound disabled (403)
    if rss_articles is None:
        rss_articles = await scan_all_rss_feeds()
    funding_match = match_funding_to_company(company_name, rss_articles)
    competitor = get_competitor_signal(website_text)

    # hiring = await hiring_task
    hiring = {"is_hiring": False, "job_count": 0, "jobs": [], "source": "disabled"}

    # Build signal details
    signal_details: dict[str, Any] = {
        "hiring": hiring,
        "funding": funding_match,
        "competitor": competitor,
    }

    # Collect detected signals
    detected_signals = [s for s in existing_signals if s]
    if hiring.get("is_hiring"):
        detected_signals.append("hiring")
    if funding_match:
        detected_signals.append("funded")
    if competitor.get("competitor_detected"):
        detected_signals.append("competitor_tool_used")

    # Deduplicate while preserving order
    seen = set()
    unique_signals = []
    for s in detected_signals:
        if s not in seen:
            seen.add(s)
            unique_signals.append(s)
    detected_signals = unique_signals

    # Compute expanding signal
    expanding = detect_expanding_signal(
        is_hiring=hiring.get("is_hiring", False),
        funding_detected=funding_match is not None,
        job_count=hiring.get("job_count", 0),
    )
    signal_details["expanding"] = expanding
    if expanding["detected"]:
        detected_signals.append("expanding")

    # Build WHY NOW
    why_now = build_why_now_message(
        signals=detected_signals,
        signal_details=signal_details,
        company_name=company_name,
    )

    return {
        "signals": detected_signals,
        "signal_details": signal_details,
        "why_now": why_now,
        "competitor_tools": competitor.get("tools", []),
        "primary_competitor": competitor.get("primary_tool"),
        "open_roles": hiring.get("open_roles", []),
        "job_count": hiring.get("job_count", 0),
    }
