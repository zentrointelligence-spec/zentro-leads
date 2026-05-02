"""
Company detail enrichment — SSM, revenue, years, LinkedIn, decision maker name.
Zero external APIs. Uses scraped data + heuristics.
"""

from __future__ import annotations

import re
from typing import Any

from loguru import logger


# ── Revenue multipliers by industry (Malaysian RM, annual) ──────
# Based on typical SME revenue ranges in Malaysia
_INDUSTRY_REVENUE_MULTIPLIERS: dict[str, dict[str, str]] = {
    "logistics": {
        "1-10": "RM 500K - 2M",
        "10-50": "RM 1M - 5M",
        "50-200": "RM 5M - 20M",
        "200-500": "RM 20M - 50M",
        "500+": "RM 50M+",
    },
    "transportation": {
        "1-10": "RM 500K - 2M",
        "10-50": "RM 1M - 5M",
        "50-200": "RM 5M - 20M",
        "200-500": "RM 20M - 50M",
        "500+": "RM 50M+",
    },
    "manufacturing": {
        "1-10": "RM 1M - 3M",
        "10-50": "RM 3M - 10M",
        "50-200": "RM 10M - 50M",
        "200-500": "RM 50M - 100M",
        "500+": "RM 100M+",
    },
    "construction": {
        "1-10": "RM 1M - 5M",
        "10-50": "RM 5M - 20M",
        "50-200": "RM 20M - 80M",
        "200-500": "RM 80M - 200M",
        "500+": "RM 200M+",
    },
    "food & beverage": {
        "1-10": "RM 300K - 1M",
        "10-50": "RM 1M - 5M",
        "50-200": "RM 5M - 20M",
        "200-500": "RM 20M - 50M",
        "500+": "RM 50M+",
    },
    "retail": {
        "1-10": "RM 300K - 1M",
        "10-50": "RM 1M - 5M",
        "50-200": "RM 5M - 20M",
        "200-500": "RM 20M - 50M",
        "500+": "RM 50M+",
    },
    "technology": {
        "1-10": "RM 500K - 2M",
        "10-50": "RM 2M - 10M",
        "50-200": "RM 10M - 50M",
        "200-500": "RM 50M - 100M",
        "500+": "RM 100M+",
    },
    "software": {
        "1-10": "RM 500K - 2M",
        "10-50": "RM 2M - 10M",
        "50-200": "RM 10M - 50M",
        "200-500": "RM 50M - 100M",
        "500+": "RM 100M+",
    },
    "insurance": {
        "1-10": "RM 300K - 1M",
        "10-50": "RM 1M - 5M",
        "50-200": "RM 5M - 20M",
        "200-500": "RM 20M - 50M",
        "500+": "RM 50M+",
    },
    "professional services": {
        "1-10": "RM 500K - 2M",
        "10-50": "RM 2M - 10M",
        "50-200": "RM 10M - 40M",
        "200-500": "RM 40M - 100M",
        "500+": "RM 100M+",
    },
}

_DEFAULT_MULTIPLIER = {
    "1-10": "RM 300K - 1M",
    "10-50": "RM 1M - 5M",
    "50-200": "RM 5M - 20M",
    "200-500": "RM 20M - 50M",
    "500+": "RM 50M+",
}


# ── Decision maker title priority ───────────────────────────────
_DECISION_MAKER_PRIORITY = [
    "CEO", "Chief Executive", "Managing Director", "MD",
    "Director", "Founder", "Co-Founder", "Owner", "President",
    "General Manager", "Head of", "Manager",
]


def _ssm_verified(domain: str | None) -> bool:
    """Check if domain ends with .com.my or .my (Malaysian registered)."""
    if not domain:
        return False
    d = domain.lower().strip()
    return d.endswith(".com.my") or d.endswith(".my")


def _estimate_revenue(industry: str | None, employee_range: str | None) -> str | None:
    """Estimate revenue from industry + employee count."""
    if not employee_range:
        return None
    ind = (industry or "").lower().strip()
    # Find closest industry match
    for key, ranges in _INDUSTRY_REVENUE_MULTIPLIERS.items():
        if key in ind:
            return ranges.get(employee_range, _DEFAULT_MULTIPLIER.get(employee_range))
    return _DEFAULT_MULTIPLIER.get(employee_range)


def _years_in_business(founded_year: int | None, raw_text: str = "") -> str | None:
    """Extract years in business from founded_year or copyright footer."""
    if founded_year and founded_year > 1900:
        from datetime import datetime
        years = datetime.now().year - founded_year
        return f"Est. {founded_year} ({years} years)"

    # Try to extract from copyright footer
    if raw_text:
        # Patterns: © 2015, Copyright 2018, © 2010-2024
        m = re.search(r"(?:©|copyright)\s*(?:\d{4}\s*[-–]\s*)?(\d{4})", raw_text, re.I)
        if m:
            year = int(m.group(1))
            from datetime import datetime
            if 1980 <= year <= datetime.now().year:
                years = datetime.now().year - year
                return f"Est. {year} ({years} years)"

    return None


def _best_decision_maker(people: list[dict[str, str]], company_name: str = "") -> dict[str, str] | None:
    """Pick the best decision maker from scraped people list."""
    if not people:
        return None

    # Score each person by title priority
    def _score(p: dict[str, str]) -> int:
        title = (p.get("title") or "").lower()
        for i, kw in enumerate(_DECISION_MAKER_PRIORITY):
            if kw.lower() in title:
                return 100 - i
        return 0

    scored = sorted(people, key=_score, reverse=True)
    best = scored[0]
    if _score(best) > 0:
        return best
    return None


def _linkedin_guess(company_name: str) -> str | None:
    """Generate a likely LinkedIn company URL from name."""
    if not company_name:
        return None
    # Simple slugify
    slug = re.sub(r"[^a-z0-9\s]", "", company_name.lower())
    slug = re.sub(r"\s+", "-", slug).strip("-")
    # Remove common suffixes
    slug = re.sub(r"-(sdn|bhd|sdn-bhd|private|limited|ltd|inc|corp)$", "", slug).strip("-")
    if len(slug) < 2:
        return None
    return f"https://www.linkedin.com/company/{slug}"


def enrich_company_details(
    company_name: str,
    domain: str | None,
    industry: str | None,
    employee_range: str | None,
    founded_year: int | None,
    website_raw_text: str = "",
    people: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """
    Enrich company with SSM, revenue, years, LinkedIn, decision maker.
    Returns dict of fields to update.
    """
    result: dict[str, Any] = {}

    # SSM verification
    result["ssm_verified"] = _ssm_verified(domain)

    # Revenue estimate
    revenue = _estimate_revenue(industry, employee_range)
    if revenue:
        result["revenue"] = revenue

    # Years in business
    years = _years_in_business(founded_year, website_raw_text)
    if years:
        result["years_in_business"] = years

    # LinkedIn URL
    linkedin = _linkedin_guess(company_name)
    if linkedin:
        result["linkedin_url"] = linkedin

    # Best decision maker
    best = _best_decision_maker(people or [], company_name)
    if best:
        result["decision_maker_name"] = best.get("name")
        result["decision_maker_title"] = best.get("title")

    logger.info(
        f"Company details for {company_name}: "
        f"SSM={result.get('ssm_verified')}, revenue={revenue}, "
        f"years={years}, linkedin={linkedin is not None}, "
        f"dm={best.get('name') if best else None}"
    )

    return result
