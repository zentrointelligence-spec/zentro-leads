"""
Lead scoring (100-point) and AI outreach generation.
Weights are fixed per product rules — do not change without explicit instruction.
"""

from __future__ import annotations

import json
from typing import Any

from anthropic import AsyncAnthropic
from loguru import logger

from app.config import settings

SIZE_ORDER = ["1-10", "10-50", "50-200", "200-500", "500+"]


def _size_index(rng: str | None) -> int | None:
    if not rng:
        return None
    r = rng.strip()
    try:
        return SIZE_ORDER.index(r)
    except ValueError:
        return None


def _company_size_score(employee_range: str, icp_sizes: list[str]) -> int:
    """Score company size match (max 30)."""
    if not icp_sizes:
        return 0
    idx = _size_index(employee_range)
    if idx is None:
        return 0
    icp_idxs = [_size_index(s) for s in icp_sizes]
    icp_idxs = [i for i in icp_idxs if i is not None]
    if not icp_idxs:
        return 0
    if idx in icp_idxs:
        return 30
    if any(abs(idx - j) == 1 for j in icp_idxs):
        return 15
    return 0


def _infer_seniority_from_title(title: str) -> str:
    t = (title or "").lower()
    if any(k in t for k in ("ceo", "cfo", "coo", "cto", "chief", "president", "founder")):
        return "c-level"
    if "director" in t or "vp" in t or "vice president" in t:
        return "director"
    if "manager" in t or "head of" in t:
        return "manager"
    return "individual"


def _role_score_fixed(job_title: str, icp_titles: list[str], icp_seniority: list[str]) -> int:
    """Score role match (max 25)."""
    jt = (job_title or "").lower().strip()
    titles = [t.lower() for t in (icp_titles or [])]

    if jt and any(t == jt for t in titles):
        return 25

    if jt and any(t and t in jt for t in titles):
        return 15

    senior = _infer_seniority_from_title(job_title)
    icp_sen = [s.lower() for s in (icp_seniority or [])]
    if senior.lower() in icp_sen:
        return 10
    return 0


def _industry_score(industry: str, icp_industries: list[str]) -> int:
    """Score industry match (max 20).

    Bidirectional substring so "Finance" (ICP) matches "Financial Services"
    (company) and "Financial Services" (ICP) matches "Finance" (company).
    """
    ind = (industry or "").lower().strip()
    if not ind:
        return 0
    inds = [i.lower().strip() for i in (icp_industries or []) if i]
    if not inds:
        return 0
    if any(i == ind for i in inds):
        return 20
    if any(i and (i in ind or ind in i) for i in inds):
        return 10
    return 0


def _signals_score(company: dict[str, Any], person: dict[str, Any], icp_signals: list[str]) -> tuple[int, list[str]]:
    """Intent signals score (max 15) and detected signal list."""
    signals_present: list[str] = []
    if company.get("is_hiring"):
        signals_present.append("hiring")
    if company.get("in_the_news"):
        signals_present.append("in_the_news")
    if person.get("job_changed_at"):
        signals_present.append("job_change")
    fs = company.get("funding_stage")
    if fs not in (None, "", []):
        signals_present.append("funded")

    icp_s = [str(s).lower() for s in (icp_signals or [])]
    matched = [s for s in signals_present if str(s).lower() in icp_s]
    score = min(len(matched) * 5, 15)
    return score, signals_present


def _email_score(person: dict[str, Any]) -> int:
    """Email verification score (max 10)."""
    if person.get("email_verified") and float(person.get("email_confidence") or 0.0) >= 0.9:
        return 10
    if person.get("email") and float(person.get("email_confidence") or 0.0) >= 0.5:
        return 5
    return 0


def calculate_lead_score(person: dict[str, Any], company: dict[str, Any], icp: dict[str, Any]) -> dict[str, Any]:
    """
    100-point scoring system. Returns ``{score, tier, breakdown}``.

    Weights (fixed):
    - company size: max 30
    - role: max 25
    - industry: max 20
    - intent signals: max 15
    - email: max 10
    """
    size_score = _company_size_score(company.get("employee_range"), icp.get("company_sizes") or [])
    role_score = _role_score_fixed(
        person.get("job_title") or "",
        icp.get("job_titles") or [],
        icp.get("seniority_levels") or [],
    )
    industry_score = _industry_score(company.get("industry") or "", icp.get("industries") or [])
    signals_score, signals_present = _signals_score(company, person, icp.get("intent_signals") or [])
    email_sc = _email_score(person)

    total = size_score + role_score + industry_score + signals_score + email_sc
    total = max(0, min(total, 100))

    if total >= 85:
        tier = "hot"
    elif total >= 60:
        tier = "warm"
    elif total >= 40:
        tier = "potential"
    else:
        tier = "cold"

    return {
        "score": total,
        "tier": tier,
        "breakdown": {
            "company_size": size_score,
            "role": role_score,
            "industry": industry_score,
            "signals": signals_score,
            "email": email_sc,
            "signals_detected": signals_present,
        },
    }


def _strip_json_fences(raw: str) -> str:
    """Remove markdown code fences if present."""
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            inner = parts[1]
            if inner.lower().startswith("json"):
                inner = inner[4:]
            return inner.strip()
    return text


async def generate_ai_outreach(
    person: dict[str, Any],
    company: dict[str, Any],
    icp_description: str,
    signals: list[str],
) -> dict[str, str]:
    """
    Generate personalised outreach using Claude.

    Falls back to deterministic templates when ANTHROPIC_API_KEY is missing.
    """
    if not settings.ANTHROPIC_API_KEY:
        first = person.get("first_name") or (person.get("full_name") or "there").split()[0]
        cname = company.get("name") or "your company"
        return {
            "whatsapp_message": f"Hi {first}, I help companies like {cname} with growth — quick question?",
            "email_subject": f"Quick question for {cname}",
            "email_body": (
                f"Hi {first},\n\nI noticed {cname} and wanted to reach out with something relevant.\n\n"
                "Would you be open to a short chat?"
            ),
            "linkedin_note": f"Hi {first}, would love to connect.",
        }

    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    prompt = f"""You are an expert sales copywriter for B2B outreach.

Seller context: {icp_description}

Lead details:
- Name: {person.get("full_name")}
- Title: {person.get("job_title")}
- Company: {company.get("name")}
- Industry: {company.get("industry")}
- Size: {company.get("employee_range")} employees
- Location: {company.get("city")}, {company.get("country")}
- Signals detected: {signals}

Write highly personalised outreach mentioning at least one specific signal.
Return ONLY valid JSON (no markdown, no explanation):
{{
  "whatsapp_message": "<max 200 chars, conversational, mention signal>",
  "email_subject": "<max 60 chars, specific not generic>",
  "email_body": "<max 300 chars, 2 paragraphs, personalised>",
  "linkedin_note": "<max 150 chars, connection request>"
}}"""

    message = await client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    raw = _strip_json_fences(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning(f"Failed to parse outreach JSON: {exc} raw={raw[:200]!r}")
        first = person.get("first_name") or "there"
        cname = company.get("name") or "your company"
        return {
            "whatsapp_message": f"Hi {first}, I help companies like {cname} — quick question?",
            "email_subject": f"Quick question for {cname}",
            "email_body": f"Hi {first},\n\nI noticed {cname} and wanted to reach out.",
            "linkedin_note": f"Hi {first}, would love to connect.",
        }
