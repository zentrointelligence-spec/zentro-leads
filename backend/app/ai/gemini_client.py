"""
Gemini Flash-Lite bulk lead normalization client.

Uses gemini-1.5-flash-8b — the cheapest Gemini model (~$0.0375/1M input tokens).
Ideal for high-volume, low-stakes text normalization that would be wasteful
to run through Claude (ICP builder) or GPT-4o (outreach generation).

Four normalizers — all batch a full list into ONE API call each:
  normalize_industries_bulk   — raw scrape strings → 13 standard categories
  normalize_job_titles_bulk   — messy titles → {normalized, department, seniority, is_decision_maker}
  normalize_locations_bulk    — abbreviations/aliases → {city, state, country, market}
  classify_insurance_needs_bulk — company profile → insurance product type

Each function:
  - Returns a safe fallback dict on any API/parse error (never crashes the job).
  - Deduplicates inputs before calling the API to save tokens.
  - Parses the JSON fence-stripped response with two fallback strategies.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from loguru import logger

from app.config import settings

# ── Standard industry categories (never add more without updating prompts) ───
STANDARD_INDUSTRIES = [
    "Manufacturing",
    "Food & Beverage",
    "Technology",
    "Healthcare",
    "Retail",
    "Construction",
    "Logistics",
    "Finance",
    "Education",
    "Professional Services",
    "Hospitality",
    "Agriculture",
    "Other",
]

# ── Seniority levels ──────────────────────────────────────────────────────────
SENIORITY_LEVELS = ["c_suite", "director", "manager", "senior", "junior", "unknown"]

# ── Insurance product types ───────────────────────────────────────────────────
INSURANCE_TYPES = [
    "group_medical",  # 5+ employees — most common B2B opener
    "motor",          # delivery, logistics, company vehicles
    "fire",           # property owner / landlord
    "liability",      # contractor, professional services
    "life",           # SME owner — keyman life
    "home",           # B2C property buyer
    "pa",             # personal accident
    "other",
]


def _get_model():
    """
    Return a configured GenerativeModel instance.

    Returns None (silently) if GOOGLE_GEMINI_API_KEY is not set,
    causing all normalizers to return safe fallback values.
    """
    if not settings.GOOGLE_GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
        return genai.GenerativeModel(settings.GEMINI_MODEL)
    except Exception as exc:
        logger.warning(f"[gemini] Failed to initialize model: {exc}")
        return None


def _strip_json_fence(text: str) -> str:
    """Strip ```json ... ``` or ``` ... ``` fences from Gemini output."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_json_response(text: str) -> dict[str, Any] | None:
    """
    Parse JSON from Gemini response text with two fallback strategies.

    Strategy 1: direct JSON parse of the full stripped response.
    Strategy 2: extract the first {...} block via regex.
    Returns None if both fail.
    """
    stripped = _strip_json_fence(text)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # Try extracting the first JSON object from the text
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.warning(f"[gemini] Failed to parse JSON from response: {stripped[:200]}")
    return None


async def _generate(model, prompt: str) -> str | None:
    """
    Run a Gemini generation call in a thread (SDK is sync).

    Returns the raw text or None on error.
    """
    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        return response.text
    except Exception as exc:
        logger.error(f"[gemini] Generation failed: {exc}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# NORMALIZER 1 — Industry
# ═══════════════════════════════════════════════════════════════════════════════

async def normalize_industries_bulk(
    raw_industries: list[str],
) -> dict[str, str]:
    """
    Normalize raw industry strings to standard Zentro Leads categories.

    Batches all inputs into a single Gemini API call.

    Args:
        raw_industries: List of messy strings, e.g. ["mfg", "F&B", "IT svc"].

    Returns:
        Dict mapping each input string to a standard category.
        Falls back to "Other" for any unmatched entry.
        Returns a full fallback dict (all → "Other") on API failure.

    Standard categories:
        Manufacturing, Food & Beverage, Technology, Healthcare, Retail,
        Construction, Logistics, Finance, Education, Professional Services,
        Hospitality, Agriculture, Other
    """
    if not raw_industries:
        return {}

    # Deduplicate while preserving order
    unique = list(dict.fromkeys(raw_industries))
    fallback = {r: "Other" for r in unique}

    model = _get_model()
    if model is None:
        logger.warning("[gemini] normalize_industries_bulk: no API key — returning fallback")
        return fallback

    categories_str = ", ".join(STANDARD_INDUSTRIES)
    inputs_json = json.dumps(unique, ensure_ascii=False)

    prompt = f"""Normalize these industry labels to standard categories.
Use ONLY these categories: {categories_str}
Match as closely as possible; use "Other" only if no category fits.
Input: {inputs_json}
Return ONLY a JSON object mapping each input exactly to one category.
No explanation, no markdown, no code fences.
Example: {{"mfg": "Manufacturing", "F&B": "Food & Beverage"}}"""

    logger.info(f"[gemini] Normalizing {len(unique)} industries in one call")
    raw_response = await _generate(model, prompt)

    if not raw_response:
        return fallback

    parsed = _parse_json_response(raw_response)
    if not parsed:
        return fallback

    # Validate: ensure every output is a known category
    result: dict[str, str] = {}
    for raw, normalized in parsed.items():
        if normalized in STANDARD_INDUSTRIES:
            result[raw] = normalized
        else:
            # Try case-insensitive match
            match = next(
                (s for s in STANDARD_INDUSTRIES if s.lower() == str(normalized).lower()),
                "Other",
            )
            result[raw] = match

    # Fill any inputs that Gemini skipped
    for r in unique:
        if r not in result:
            result[r] = "Other"

    logger.info(f"[gemini] Industry normalization complete: {len(result)} mapped")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# NORMALIZER 2 — Job Title
# ═══════════════════════════════════════════════════════════════════════════════

async def normalize_job_titles_bulk(
    raw_titles: list[str],
) -> dict[str, dict[str, Any]]:
    """
    Normalize raw job title strings into structured metadata.

    Batches all inputs into a single Gemini API call.

    Args:
        raw_titles: List of messy titles, e.g. ["HR mgr", "GM", "boss"].

    Returns:
        Dict mapping each input to:
            {
                "normalized":       str   — clean, standard title,
                "department":       str   — e.g. "HR", "Finance", "Sales",
                "seniority":        str   — one of SENIORITY_LEVELS,
                "is_decision_maker": bool — True if they can approve insurance purchase
            }
        Falls back to a conservative default dict on API failure.
    """
    if not raw_titles:
        return {}

    unique = list(dict.fromkeys(raw_titles))
    fallback = {
        t: {
            "normalized":        t,
            "department":        "Unknown",
            "seniority":         "unknown",
            "is_decision_maker": False,
        }
        for t in unique
    }

    model = _get_model()
    if model is None:
        logger.warning("[gemini] normalize_job_titles_bulk: no API key — returning fallback")
        return fallback

    seniority_str = ", ".join(SENIORITY_LEVELS)
    inputs_json = json.dumps(unique, ensure_ascii=False)

    prompt = f"""Normalize these job titles and return structured metadata.

Seniority levels (use exactly): {seniority_str}
is_decision_maker = true if this person can approve an insurance purchase for their company.

Input titles: {inputs_json}

Return ONLY a JSON object. Keys are the exact input strings. Values are objects:
{{
  "normalized": "clean standard title",
  "department": "department name",
  "seniority": "one of the seniority levels",
  "is_decision_maker": true or false
}}

No explanation, no markdown, no code fences.
Example: {{"HR mgr": {{"normalized": "HR Manager", "department": "HR", "seniority": "manager", "is_decision_maker": false}}}}"""

    logger.info(f"[gemini] Normalizing {len(unique)} job titles in one call")
    raw_response = await _generate(model, prompt)

    if not raw_response:
        return fallback

    parsed = _parse_json_response(raw_response)
    if not parsed:
        return fallback

    result: dict[str, dict[str, Any]] = {}
    for raw, meta in parsed.items():
        if not isinstance(meta, dict):
            result[raw] = fallback.get(raw, fallback[unique[0]])
            continue
        seniority = str(meta.get("seniority", "unknown")).lower()
        if seniority not in SENIORITY_LEVELS:
            seniority = "unknown"
        result[raw] = {
            "normalized":        str(meta.get("normalized", raw)),
            "department":        str(meta.get("department", "Unknown")),
            "seniority":         seniority,
            "is_decision_maker": bool(meta.get("is_decision_maker", False)),
        }

    for t in unique:
        if t not in result:
            result[t] = fallback[t]

    logger.info(f"[gemini] Job title normalization complete: {len(result)} mapped")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# NORMALIZER 3 — Location
# ═══════════════════════════════════════════════════════════════════════════════

async def normalize_locations_bulk(
    raw_locations: list[str],
) -> dict[str, dict[str, str]]:
    """
    Normalize raw location strings into structured city/state/country/market data.

    Batches all inputs into a single Gemini API call.

    Args:
        raw_locations: List of messy locations, e.g. ["KL", "Bombay", "Shah Alam"].

    Returns:
        Dict mapping each input to:
            {
                "city":    str — canonical city name,
                "state":   str — state/province,
                "country": str — full country name,
                "market":  str — "malaysia" | "india" | "other"
            }
        Falls back to {"city": raw, "state": "", "country": "", "market": "other"} on failure.
    """
    if not raw_locations:
        return {}

    unique = list(dict.fromkeys(raw_locations))
    fallback = {
        loc: {"city": loc, "state": "", "country": "", "market": "other"}
        for loc in unique
    }

    model = _get_model()
    if model is None:
        logger.warning("[gemini] normalize_locations_bulk: no API key — returning fallback")
        return fallback

    inputs_json = json.dumps(unique, ensure_ascii=False)

    prompt = f"""Normalize these location strings. All are from Malaysia or India.

Input locations: {inputs_json}

Return ONLY a JSON object. Keys are the exact input strings. Values are objects:
{{
  "city": "canonical city name",
  "state": "state or province",
  "country": "full country name e.g. Malaysia or India",
  "market": "malaysia" or "india" or "other"
}}

Rules:
- "KL" and "Kuala Lumpur" → city: "Kuala Lumpur", state: "Kuala Lumpur", country: "Malaysia", market: "malaysia"
- "Bombay" → city: "Mumbai", state: "Maharashtra", country: "India", market: "india"
- "Bengaluru" and "Bangalore" → city: "Bengaluru", state: "Karnataka", country: "India", market: "india"
- market is always lowercase: "malaysia", "india", or "other"
No explanation, no markdown, no code fences."""

    logger.info(f"[gemini] Normalizing {len(unique)} locations in one call")
    raw_response = await _generate(model, prompt)

    if not raw_response:
        return fallback

    parsed = _parse_json_response(raw_response)
    if not parsed:
        return fallback

    result: dict[str, dict[str, str]] = {}
    for raw, loc in parsed.items():
        if not isinstance(loc, dict):
            result[raw] = fallback.get(raw, fallback[unique[0]])
            continue
        market = str(loc.get("market", "other")).lower()
        if market not in ("malaysia", "india", "other"):
            market = "other"
        result[raw] = {
            "city":    str(loc.get("city", raw)),
            "state":   str(loc.get("state", "")),
            "country": str(loc.get("country", "")),
            "market":  market,
        }

    for loc in unique:
        if loc not in result:
            result[loc] = fallback[loc]

    logger.info(f"[gemini] Location normalization complete: {len(result)} mapped")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# NORMALIZER 4 — Insurance Need Classifier
# ═══════════════════════════════════════════════════════════════════════════════

async def classify_insurance_needs_bulk(
    lead_descriptions: list[dict[str, Any]],
) -> dict[str, str]:
    """
    Classify the most likely insurance need for a list of B2B leads.

    Each item in lead_descriptions must have at least an "id" key.

    Args:
        lead_descriptions: List of dicts with keys: id, company_type, size, signals.

    Returns:
        Dict mapping lead ID → insurance type string.
        Falls back to "other" for any unclassified lead or on API failure.

    Insurance types:
        group_medical — 5+ employees, any industry
        motor         — delivery, logistics, fleet, transport
        fire          — property owner, factory, warehouse
        liability     — contractor, professional services, consultant
        life          — SME owner keyman
        home          — B2C property buyer
        pa            — personal accident
        other         — catch-all
    """
    if not lead_descriptions:
        return {}

    fallback = {item["id"]: "other" for item in lead_descriptions if "id" in item}

    model = _get_model()
    if model is None:
        logger.warning("[gemini] classify_insurance_needs_bulk: no API key — returning fallback")
        return fallback

    insurance_str = ", ".join(INSURANCE_TYPES)
    inputs_json = json.dumps(lead_descriptions, ensure_ascii=False)

    prompt = f"""For each business description, classify the most likely insurance need.

Insurance types (use exactly): {insurance_str}

Rules:
- group_medical: 5+ employees, any industry (highest probability upsell)
- motor: delivery, logistics, company vehicles, fleet, transport
- fire: factory, warehouse, shophouse, property owner
- liability: contractor, consultant, IT firm, professional services
- life: SME owner — keyman / business continuity insurance
- home: B2C only — individual who just bought property
- pa: personal accident — manufacturing, construction, individual workers
- other: when genuinely unclear

Input: {inputs_json}

Return ONLY a JSON object mapping each "id" to one insurance type string.
No explanation, no markdown, no code fences.
Example: {{"lead-123": "group_medical", "lead-456": "motor"}}"""

    logger.info(f"[gemini] Classifying insurance needs for {len(lead_descriptions)} leads")
    raw_response = await _generate(model, prompt)

    if not raw_response:
        return fallback

    parsed = _parse_json_response(raw_response)
    if not parsed:
        return fallback

    result: dict[str, str] = {}
    for lead_id, insurance in parsed.items():
        ins = str(insurance).lower().strip()
        result[lead_id] = ins if ins in INSURANCE_TYPES else "other"

    # Fill any leads Gemini skipped
    for item in lead_descriptions:
        lead_id = item.get("id", "")
        if lead_id and lead_id not in result:
            result[lead_id] = "other"

    logger.info(f"[gemini] Insurance classification complete: {len(result)} leads")
    return result
