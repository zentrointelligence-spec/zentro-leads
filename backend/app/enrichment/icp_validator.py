"""
ICP Validation Agent — uses Claude to evaluate each generated lead against
the user's Ideal Customer Profile. Returns match score, verdict, reason,
insurance needs, and recommended product.
"""

from __future__ import annotations

import json
from typing import Any

from anthropic import AsyncAnthropic
from loguru import logger

from app.config import settings


async def validate_lead_against_icp(
    company_name: str,
    company_industry: str | None,
    company_description: str | None,
    company_size: str | None,
    company_city: str | None,
    icp_description: str,
    icp_industries: list[str],
) -> dict[str, Any]:
    """
    Evaluate a single lead against the user's ICP using Claude.
    Returns structured validation data.
    """
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("No ANTHROPIC_API_KEY — skipping ICP validation")
        return _default_validation()

    industries_str = ", ".join(icp_industries) if icp_industries else "Not specified"

    prompt = f"""You are an expert ICP validation agent for a Malaysian insurance agency.

User's Ideal Customer Profile (ICP):
- Description: {icp_description or "SME businesses in Malaysia needing insurance"}
- Target industries: {industries_str}

Evaluate this lead:
- Company name: {company_name}
- Industry: {company_industry or "Unknown"}
- Description: {company_description or "N/A"}
- Size: {company_size or "Unknown"}
- Location: {company_city or "Malaysia"}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "match_score": 0-100,
  "verdict": "perfect_match" | "good_match" | "partial_match" | "poor_match",
  "reason": "One sentence explaining why this lead matches or doesn't match the ICP",
  "insurance_needs": ["auto", "fire", "cargo", "workmanship", "medical", "travel", "group_medical", "liability"],
  "recommended_product": "Most relevant single insurance product name"
}}

Rules:
- match_score: 90-100 = perfect (industry matches + size fits + clear need)
- match_score: 70-89 = good (industry matches or strong signal)
- match_score: 40-69 = partial (some overlap but not ideal)
- match_score: 0-39 = poor (unlikely to convert)
- Insurance needs: be specific based on industry (e.g., logistics = cargo + auto + liability)
- recommended_product: pick ONE most relevant product"""

    try:
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = await client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        # Strip markdown fences
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1].replace("json", "").strip() if len(parts) >= 2 else raw.strip()

        data = json.loads(raw)

        score = max(0, min(100, int(data.get("match_score", 0))))
        verdict = data.get("verdict", "poor_match")
        if verdict not in {"perfect_match", "good_match", "partial_match", "poor_match"}:
            verdict = "poor_match"

        return {
            "match_score": score,
            "verdict": verdict,
            "reason": str(data.get("reason", "")),
            "insurance_needs": [str(n) for n in (data.get("insurance_needs") or [])],
            "recommended_product": str(data.get("recommended_product", "")),
        }
    except Exception as exc:
        logger.warning(f"ICP validation failed for {company_name}: {exc}")
        return _default_validation()


def _default_validation() -> dict[str, Any]:
    return {
        "match_score": 50,
        "verdict": "partial_match",
        "reason": "ICP validation skipped — default score applied",
        "insurance_needs": [],
        "recommended_product": "",
    }
