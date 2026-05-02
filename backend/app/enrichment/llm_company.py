"""
LLM-powered company enrichment — extracts structured B2B data from website text.
Uses Claude (Anthropic) to analyze scraped website content and estimate:
  - employee count range
  - industry / sub-industry
  - business model
  - intent signals (hiring, expanding, new products, etc.)
  - key products / services

Zero external APIs. Runs entirely on scraped website text + Claude.
"""

from __future__ import annotations

import json
from typing import Any

from anthropic import AsyncAnthropic
from loguru import logger

from app.config import settings


# Standard employee ranges used by the scoring engine
SIZE_ORDER = ["1-10", "10-50", "50-200", "200-500", "500+"]

# Truncate website text to keep API costs reasonable (~4k tokens ≈ 12k chars)
_MAX_TEXT_CHARS = 12000

# Malaysian industry mappings — Claude sometimes returns variations; normalize them
_INDUSTRY_SYNONYMS: dict[str, str] = {
    "accounting": "Accounting & Finance",
    "accountancy": "Accounting & Finance",
    "audit": "Accounting & Finance",
    "tax": "Accounting & Finance",
    "bookkeeping": "Accounting & Finance",
    "logistics": "Logistics & Transportation",
    "freight": "Logistics & Transportation",
    "cargo": "Logistics & Transportation",
    "transport": "Logistics & Transportation",
    "shipping": "Logistics & Transportation",
    "warehouse": "Logistics & Transportation",
    "3pl": "Logistics & Transportation",
    "restaurant": "Food & Beverage",
    "cafe": "Food & Beverage",
    "catering": "Food & Beverage",
    "f&b": "Food & Beverage",
    "insurance": "Insurance",
    "takaful": "Insurance",
    "construction": "Construction",
    "contractor": "Construction",
    "renovation": "Construction",
    "retail": "Retail",
    "e-commerce": "Retail",
    "online store": "Retail",
    "manufacturing": "Manufacturing",
    "technology": "Technology",
    "information technology": "Technology",
    "it services": "Technology",
    "software": "Software",
    "saas": "Software",
    "systems integrator": "Technology",
    "systems integration": "Technology",
    "factory": "Manufacturing",
    "software": "Technology",
    "it services": "Technology",
    "digital": "Technology",
    "web design": "Technology",
    "healthcare": "Healthcare",
    "clinic": "Healthcare",
    "medical": "Healthcare",
    "pharmacy": "Healthcare",
    "law firm": "Professional Services",
    "legal": "Professional Services",
    "consulting": "Professional Services",
    "agency": "Professional Services",
    "marketing": "Professional Services",
    "real estate": "Real Estate",
    "property": "Real Estate",
    "education": "Education",
    "training": "Education",
}


def _truncate_text(text: str, max_chars: int = _MAX_TEXT_CHARS) -> str:
    """Truncate from the start; keep the beginning (home page) + end (contact/about)."""
    if len(text) <= max_chars:
        return text
    # Keep first 60% + last 40% to capture both homepage and contact/about content
    head_len = int(max_chars * 0.6)
    tail_len = max_chars - head_len
    return text[:head_len] + "\n...[truncated]...\n" + text[-tail_len:]


def _map_employee_count(estimate: str | None) -> str | None:
    """Map free-text employee estimate to standard range."""
    if not estimate:
        return None
    e = estimate.lower().strip()
    # Direct match
    if e in SIZE_ORDER:
        return e
    # Numeric extraction
    import re as _re
    nums = _re.findall(r"\d+", e)
    if not nums:
        return None
    n = int(nums[0])
    if n < 10:
        return "1-10"
    if n < 50:
        return "10-50"
    if n < 200:
        return "50-200"
    if n < 500:
        return "200-500"
    return "500+"


def _normalize_industry(industry: str | None) -> str | None:
    """Normalize industry text to standard categories."""
    if not industry:
        return None
    ind = industry.lower().strip()
    # Direct synonym lookup
    for key, value in _INDUSTRY_SYNONYMS.items():
        if key in ind:
            return value
    # Return original if no match, capitalized
    return industry.strip().title()


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


async def analyze_company_website(
    raw_text: str,
    company_name: str,
    maps_category: str | None = None,
) -> dict[str, Any]:
    """
    Analyze a company's website text with Claude and extract structured B2B data.

    Returns:
        {
            "employee_range": "1-10" | "10-50" | ... | None,
            "industry": "string" | None,
            "sub_industry": "string" | None,
            "business_model": "string" | None,
            "signals_detected": ["hiring", "expanding", ...],
            "key_products": ["string", ...],
            "confidence": 0.0-1.0,
        }
    """
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set — skipping LLM company enrichment")
        return _empty_result()

    has_website_text = raw_text and len(raw_text.strip()) >= 200

    if has_website_text:
        truncated = _truncate_text(raw_text)
        prompt = f"""You are a B2B research analyst. Analyze the following website content for a Malaysian company and extract structured business intelligence.

Company Name: {company_name}
Google Maps Category: {maps_category or "Unknown"}

Website Content:
---
{truncated}
---

Extract the following fields. Return ONLY valid JSON (no markdown, no explanation):

{{
  "employee_range": "1-10" | "10-50" | "50-200" | "200-500" | "500+" | null,
  "industry": "Primary industry category (e.g., Logistics, Manufacturing, Insurance, Construction, Retail, Technology, Healthcare, Food & Beverage, Professional Services)",
  "sub_industry": "More specific sub-category (e.g., Freight Forwarding, General Insurance, Software Development)",
  "business_model": "Brief description of what they do and who they serve (1 sentence)",
  "signals_detected": ["hiring" | "expanding" | "new_product" | "new_location" | "funded" | "in_the_news" | "awards" | "partnership"],
  "key_products": ["List of main products or services they offer (max 5)"],
  "confidence": 0.0-1.0
}}

Rules:
- employee_range: infer from phrases like "team of 50", "200+ staff", "growing company". If no evidence, use null.
- industry: choose the SINGLE best match. Do not make up categories.
- signals_detected: only include signals with clear evidence in the text.
- confidence: how certain you are based on the amount and quality of information.
- Return null for any field where there is no evidence."""
    else:
        # Fallback: infer from company name + Google Maps category alone
        logger.debug(f"No website text for {company_name} — inferring from name + category")
        prompt = f"""You are a B2B research analyst. A Malaysian company's website could not be accessed, so infer its business profile from its name and Google Maps category.

Company Name: {company_name}
Google Maps Category: {maps_category or "Unknown"}

Based on the company name and category, make your BEST ESTIMATE for the following fields. Return ONLY valid JSON (no markdown, no explanation):

{{
  "employee_range": "1-10" | "10-50" | "50-200" | "200-500" | "500+" | null,
  "industry": "Primary industry category",
  "sub_industry": "More specific sub-category",
  "business_model": "Brief description of what they likely do (1 sentence)",
  "signals_detected": [],
  "key_products": ["List of likely products or services (max 3, be conservative)"],
  "confidence": 0.0-1.0
}}

CRITICAL RULES:
1. PRIORITIZE the COMPANY NAME over the Google Maps category. The category is often wrong.
   - "OR Technologies", "Info-Tech", "IT Solutions" = Technology/Software (ignore if category says Retail)
   - "Freight", "Logistics", "Shipping", "Cargo" = Logistics
   - "Manufacturing", "Factory", "Industrial" = Manufacturing
   - "Construction", "Builders", "Engineering" = Construction
2. Use naming conventions: "Sdn Bhd" = private limited company.
3. Category "Consultant" often means professional services. "Corporate office" usually means larger company.
4. If the name contains a location or is generic (e.g., "ABC Enterprise"), confidence should be lower (0.3-0.5).
5. If the name clearly describes the business (e.g., "Global Freight Solutions"), confidence can be higher (0.6-0.8).
6. employee_range: Malaysian SMEs are usually 10-200. Use "10-50" for typical Sdn Bhd, "50-200" if the name sounds like an established firm. "1-10" only for very small/home-based sounding names.
7. signals_detected: ALWAYS return empty array [] — no website means no signal evidence.
8. confidence: 0.3-0.5 for guesses, 0.6-0.8 for strongly indicative names. Never above 0.8 without website data."""

    try:
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = await client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        raw = _strip_json_fences(raw)
        parsed = json.loads(raw)

        # Normalize and validate
        result = {
            "employee_range": _map_employee_count(parsed.get("employee_range")),
            "industry": _normalize_industry(parsed.get("industry")),
            "sub_industry": parsed.get("sub_industry") if parsed.get("sub_industry") else None,
            "business_model": parsed.get("business_model") if parsed.get("business_model") else None,
            "signals_detected": _clean_signals(parsed.get("signals_detected", [])),
            "key_products": [str(p) for p in (parsed.get("key_products") or [])[:5]],
            "confidence": max(0.0, min(1.0, float(parsed.get("confidence", 0.0)))),
        }

        logger.info(
            f"LLM enrichment for {company_name}: "
            f"industry={result['industry']}, size={result['employee_range']}, "
            f"signals={result['signals_detected']}, confidence={result['confidence']:.2f}"
        )
        return result

    except json.JSONDecodeError as exc:
        logger.warning(f"LLM enrichment JSON parse failed for {company_name}: {exc}")
        return _empty_result()
    except Exception as exc:
        logger.warning(f"LLM enrichment failed for {company_name}: {exc}")
        return _empty_result()


def _empty_result() -> dict[str, Any]:
    return {
        "employee_range": None,
        "industry": None,
        "sub_industry": None,
        "business_model": None,
        "signals_detected": [],
        "key_products": [],
        "confidence": 0.0,
    }


def _clean_signals(signals: list[Any]) -> list[str]:
    """Validate and deduplicate signal names."""
    valid = {"hiring", "expanding", "new_product", "new_location", "funded", "in_the_news", "awards", "partnership"}
    cleaned: list[str] = []
    seen: set[str] = set()
    for s in signals:
        if s and str(s).lower() in valid:
            key = str(s).lower()
            if key not in seen:
                seen.add(key)
                cleaned.append(key)
    return cleaned
