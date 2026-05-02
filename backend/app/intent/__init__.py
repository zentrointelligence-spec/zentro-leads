"""
Intent signal detection layer for LeadRadar.
Wellfound scraper, RSS funding monitor, competitor detection.
"""

from app.intent.engine import (
    detect_expanding_signal,
    build_why_now_message,
    enrich_company_intent,
)

__all__ = [
    "detect_expanding_signal",
    "build_why_now_message",
    "enrich_company_intent",
]
