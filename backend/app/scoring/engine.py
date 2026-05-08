"""
Lead scoring (100-point) and AI outreach generation.
Weights are fixed per product rules — do not change without explicit instruction.

Scoring priority:
  1. XGBoost ML model (if trained and model file present)
  2. Deterministic 100-point engine (fallback, always available)
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from app.ai.gpt_client import generate_outreach_draft, generate_score_explanation
from app.config import settings
from app.scoring.features import extract_b2b_features
from app.scoring.ml_scorer import predict_lead_score

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


def _signals_score(
    company: dict[str, Any],
    person: dict[str, Any],
    icp_signals: list[str],
    extra_signals: list[str] | None = None,
) -> tuple[int, list[str]]:
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

    # Add extra signals (e.g. from company name keyword detection)
    for s in (extra_signals or []):
        if s and s not in signals_present:
            signals_present.append(s)

    icp_s = [str(s).lower() for s in (icp_signals or [])]
    matched = [s for s in signals_present if str(s).lower() in icp_s]
    score = min(len(matched) * 5, 15)
    return score, signals_present


def _email_score(person: dict[str, Any]) -> int:
    """Email verification score (max 10)."""
    email = person.get("email") or ""
    confidence = float(person.get("email_confidence") or 0.0)

    # Verified high-confidence email
    if person.get("email_verified") and confidence >= 0.9:
        return 10

    # Pattern email with good confidence
    if email and "@" in email:
        if confidence >= 0.7:
            return 10
        elif confidence > 0:
            return 5

    # Fallback for any email present
    if email and confidence >= 0.5:
        return 5
    return 0


def calculate_lead_score(
    person: dict[str, Any],
    company: dict[str, Any],
    icp: dict[str, Any],
    extra_signals: list[str] | None = None,
    icp_match_score: int | None = None,
) -> dict[str, Any]:
    """
    100-point scoring system. Returns ``{score, tier, breakdown}``.

    Priority:
      1. XGBoost ML model (uses extract_b2b_features; returns None if model absent)
      2. Deterministic weights (company_size:30, role:25, industry:20,
         signals:15, email:10, icp_bonus:up_to_25)
    """
    # ── ML inference (try first) ─────────────────────────────────────────────
    try:
        features  = extract_b2b_features(lead=person, company=company, icp=icp)
        ml_score  = predict_lead_score(features, model_type="b2b")
    except Exception as _exc:
        logger.debug(f"[engine] ML feature extraction skipped: {_exc}")
        ml_score = None

    if ml_score is not None:
        # Compute deterministic breakdown for transparency (the total is overridden)
        _size   = _company_size_score(company.get("employee_range"), icp.get("company_sizes") or [])
        _role   = _role_score_fixed(
            person.get("job_title") or "",
            icp.get("job_titles") or [],
            icp.get("seniority_levels") or [],
        )
        _ind    = _industry_score(company.get("industry") or "", icp.get("industries") or [])
        _sig, signals_present = _signals_score(
            company, person, icp.get("intent_signals") or [], extra_signals=extra_signals
        )
        _em     = _email_score(person)
        _icp_b  = (
            25 if (icp_match_score or 0) >= 90
            else 15 if (icp_match_score or 0) >= 75
            else 10 if (icp_match_score or 0) >= 60
            else 0
        )
        tier = (
            "hot"       if ml_score >= 85
            else "warm" if ml_score >= 60
            else "potential" if ml_score >= 40
            else "cold"
        )
        return {
            "score": ml_score,
            "tier":  tier,
            "breakdown": {
                "company_size":      _size,
                "role":              _role,
                "industry":          _ind,
                "signals":           _sig,
                "email":             _em,
                "icp_match_bonus":   _icp_b,
                "signals_detected":  signals_present,
                "ml_model":          True,
                "ml_score":          ml_score,
            },
        }

    # ── Deterministic fallback ───────────────────────────────────────────────
    size_score = _company_size_score(company.get("employee_range"), icp.get("company_sizes") or [])
    role_score = _role_score_fixed(
        person.get("job_title") or "",
        icp.get("job_titles") or [],
        icp.get("seniority_levels") or [],
    )
    industry_score = _industry_score(company.get("industry") or "", icp.get("industries") or [])
    signals_score, signals_present = _signals_score(
        company, person, icp.get("intent_signals") or [], extra_signals=extra_signals
    )
    email_sc = _email_score(person)

    total = size_score + role_score + industry_score + signals_score + email_sc

    # ICP match bonus
    icp_bonus = 0
    if icp_match_score is not None:
        if icp_match_score >= 90:
            icp_bonus = 25
        elif icp_match_score >= 75:
            icp_bonus = 15
        elif icp_match_score >= 60:
            icp_bonus = 10
    total += icp_bonus

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
            "icp_match_bonus": icp_bonus,
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
    why_now: str | None = None,
    competitor_tool: str | None = None,
) -> dict[str, str]:
    """
    Generate personalised multi-channel outreach using GPT-4o Mini.

    Wraps generate_outreach_draft() for all three channels (WhatsApp, email,
    SMS) and returns them in the legacy flat dict format expected by the lead
    generator so no other code needs to change.
    """
    first = person.get("first_name") or (person.get("full_name") or "there").split()[0]
    cname = company.get("name") or "your company"

    city = company.get("city") or ""
    country = company.get("country") or ""
    location = f"{city}, {country}".strip(", ") or "Malaysia"

    lead_dict: dict[str, Any] = {
        "person_name":    person.get("full_name") or first,
        "company_name":   cname,
        "location":       location,
        "intent_signals": signals,
        "icp_reason":     why_now or icp_description or "",
        "lead_score":     0,
    }
    if competitor_tool:
        lead_dict["icp_reason"] = (lead_dict["icp_reason"] + f" (currently using {competitor_tool})").strip()

    # Infer insurance type from ICP description or default
    insurance_type = icp_description.split(".")[0][:60] if icp_description else "insurance"

    # Generate WhatsApp + email drafts in parallel
    import asyncio as _asyncio

    wa_draft, em_draft = await _asyncio.gather(
        generate_outreach_draft(lead_dict, "whatsapp", "en", insurance_type),
        generate_outreach_draft(lead_dict, "email",    "en", insurance_type),
    )

    return {
        "whatsapp_message": wa_draft.get("body", f"Hi {first}, quick question about {cname}?"),
        "email_subject":    em_draft.get("subject", f"Quick question for {cname}"),
        "email_body":       em_draft.get("body", f"Hi {first},\n\nI noticed {cname} and wanted to reach out."),
        "linkedin_note":    f"Hi {first}, {wa_draft.get('call_to_action', 'would love to connect.')}",
    }


async def explain_lead_score(
    lead: dict[str, Any],
    score_breakdown: dict[str, Any],
) -> str:
    """
    Return a human-readable GPT-4o Mini explanation of the lead's score.

    This is a thin wrapper around gpt_client.generate_score_explanation()
    kept here so the scoring module remains the single import point for
    score-related functionality.
    """
    return await generate_score_explanation(lead, score_breakdown)
