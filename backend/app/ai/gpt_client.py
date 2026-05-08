"""GPT-4o Mini client for outreach draft generation and score explanations.

Used for:
  - generate_outreach_draft()  → channel-specific, localised outreach copy
  - generate_score_explanation() → human-readable lead quality summary

Both functions fall back gracefully when OPENAI_API_KEY is not set.
"""

from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger

from app.config import settings

_OUTREACH_SYSTEM = """\
You are an expert insurance sales copywriter working in Malaysia and India.
Write outreach messages that feel personal, local, and non-pushy.
Match the language and cultural tone of the target market.
Reference the specific life event or buying signal that makes this lead 
relevant RIGHT NOW — never send a generic message.

Rules:
- WhatsApp: short, casual, max 200 chars, emoji optional, end with a soft CTA.
- Email: medium length, professional, 2–3 short paragraphs, strong subject line.
- SMS: very short, max 160 chars, no links in the body.
- Always address by first name.
- Return ONLY valid JSON, no markdown, no explanation."""

_SCORE_SYSTEM = """\
You are a lead quality analyst for an insurance lead generation platform
targeting SMEs and individuals in Malaysia and India.
Explain in 2–3 sentences why this lead scored the way it did.
Be specific about the signals — mention the actual numbers and contributing
factors. Write for an insurance agent: practical and actionable, not technical."""


def _strip_fences(text: str) -> str:
    """Strip markdown code fences from a JSON response."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


async def generate_outreach_draft(
    lead: dict[str, Any],
    channel: str,        # "whatsapp" | "email" | "sms"
    language: str,       # "en" | "ms" | "hi" | "ta"
    insurance_type: str,
) -> dict[str, Any]:
    """
    Generate a personalised outreach draft for a single lead via GPT-4o Mini.

    Args:
        lead:           Dict with company_name, person_name, location,
                        intent_signals, icp_reason, lead_score.
        channel:        Delivery channel — affects length and tone.
        language:       ISO language code — affects language and cultural tone.
        insurance_type: Product being offered (e.g. "motor fleet", "life").

    Returns:
        Dict with keys: subject (email only), body, follow_up, call_to_action.
        Falls back to a deterministic template when OpenAI is unavailable.
    """
    person_name = lead.get("person_name") or lead.get("name") or "there"
    first_name = person_name.split()[0] if person_name else "there"
    company    = lead.get("company_name") or "your company"
    location   = lead.get("location") or "your area"
    signals    = lead.get("intent_signals") or []
    signal_str = ", ".join(str(s) for s in signals) if signals else "general business need"
    why_now    = lead.get("icp_reason") or lead.get("why_now") or signal_str
    score      = lead.get("lead_score") or 0

    lang_label = {
        "en": "English",
        "ms": "Bahasa Malaysia",
        "hi": "Hindi",
        "ta": "Tamil",
    }.get(language, "English")

    channel_instruction = {
        "whatsapp": "Write a WhatsApp message (max 200 chars, casual, conversational).",
        "email":    "Write a sales email (professional, 2–3 short paragraphs).",
        "sms":      "Write an SMS (max 160 chars, no links, direct).",
    }.get(channel, "Write a WhatsApp message (max 200 chars).")

    user_prompt = f"""Lead details:
- Name: {first_name}
- Company: {company}
- Location: {location}
- Intent signals: {signal_str}
- Why now: {why_now}
- Insurance type offered: {insurance_type}
- Lead score: {score}/100

Channel: {channel_instruction}
Language: Write in {lang_label}.

Return ONLY valid JSON:
{{
  "subject": "<email subject line — omit for non-email channels>",
  "body": "<main message body>",
  "follow_up": "<3-day follow-up variation — shorter>",
  "call_to_action": "<single clear CTA phrase>"
}}"""

    if not settings.OPENAI_API_KEY:
        logger.debug("GPT outreach: OPENAI_API_KEY not set — returning template")
        return _fallback_outreach(first_name, company, channel, insurance_type)

    try:
        from openai import AsyncOpenAI  # type: ignore[import]

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=500,
            temperature=0.7,
            messages=[
                {"role": "system", "content": _OUTREACH_SYSTEM},
                {"role": "user",   "content": user_prompt},
            ],
        )
        raw = _strip_fences(response.choices[0].message.content or "")
        draft: dict[str, Any] = json.loads(raw)

        # Guarantee required keys exist
        draft.setdefault("subject", "")
        draft.setdefault("body", "")
        draft.setdefault("follow_up", "")
        draft.setdefault("call_to_action", "")
        logger.debug(f"GPT outreach: generated {channel}/{language} draft for {company}")
        return draft

    except json.JSONDecodeError as exc:
        logger.warning(f"GPT outreach: JSON parse failed: {exc}")
        return _fallback_outreach(first_name, company, channel, insurance_type)
    except Exception as exc:
        logger.warning(f"GPT outreach: API call failed: {exc}")
        return _fallback_outreach(first_name, company, channel, insurance_type)


def _fallback_outreach(
    first_name: str,
    company: str,
    channel: str,
    insurance_type: str,
) -> dict[str, Any]:
    """Deterministic template used when OpenAI is unavailable."""
    body = (
        f"Hi {first_name}, I help companies like {company} with {insurance_type} coverage. "
        "Would you be open to a quick 5-minute call?"
    )
    return {
        "subject":        f"Insurance protection for {company}",
        "body":           body,
        "follow_up":      f"Hi {first_name}, just following up on my earlier message. Happy to chat at your convenience.",
        "call_to_action": "Reply YES for a free quote",
    }


async def generate_score_explanation(
    lead: dict[str, Any],
    score_breakdown: dict[str, Any],
) -> str:
    """
    Generate a 2–3 sentence plain-English explanation of why a lead scored
    the way it did, aimed at an insurance agent.

    Args:
        lead:            Dict with company_name, lead_score, lead_tier, industry,
                         location, and any relevant context fields.
        score_breakdown: The score_breakdown dict from calculate_lead_score(),
                         e.g. {company_size: 30, role: 25, industry: 20, ...}.

    Returns:
        Explanation string. Returns a deterministic fallback on any error.
    """
    if not settings.OPENAI_API_KEY:
        return _fallback_explanation(lead, score_breakdown)

    company  = lead.get("company_name") or "this company"
    score    = lead.get("lead_score") or 0
    tier     = (lead.get("lead_tier") or "potential").upper()
    industry = lead.get("industry") or "unknown industry"

    user_prompt = f"""Lead: {company} ({industry})
Score: {score}/100  Tier: {tier}

Score breakdown:
{json.dumps(score_breakdown, indent=2)}

Write a 2–3 sentence explanation for an insurance agent. Be specific about
what drove the score up or down."""

    try:
        from openai import AsyncOpenAI  # type: ignore[import]

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=150,
            temperature=0.3,
            messages=[
                {"role": "system", "content": _SCORE_SYSTEM},
                {"role": "user",   "content": user_prompt},
            ],
        )
        explanation = (response.choices[0].message.content or "").strip()
        logger.debug(f"GPT score explanation: generated for {company}")
        return explanation

    except Exception as exc:
        logger.warning(f"GPT score explanation failed: {exc}")
        return _fallback_explanation(lead, score_breakdown)


def _fallback_explanation(
    lead: dict[str, Any],
    score_breakdown: dict[str, Any],
) -> str:
    """Deterministic fallback explanation when OpenAI is unavailable."""
    score   = lead.get("lead_score") or 0
    tier    = (lead.get("lead_tier") or "potential").upper()
    company = lead.get("company_name") or "This lead"
    top_factors = sorted(
        ((k, v) for k, v in score_breakdown.items() if isinstance(v, (int, float)) and k != "signals_detected"),
        key=lambda x: x[1],
        reverse=True,
    )[:2]
    factors_str = " and ".join(f"{k.replace('_', ' ')} ({v} pts)" for k, v in top_factors)
    return (
        f"{company} scored {score}/100 ({tier} tier). "
        f"Top contributing factors: {factors_str}. "
        f"{'Strong candidate for outreach.' if score >= 60 else 'More nurturing needed before direct outreach.'}"
    )
