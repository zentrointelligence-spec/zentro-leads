"""
Feature engineering for the XGBoost lead scoring models.

Two feature sets:
  extract_b2b_features(lead, company, icp)  → 14 numeric features
  extract_b2c_features(person, icp)          → 10 numeric features

All encoder/matcher helpers are pure functions — no I/O, no async.
Feature vectors are dicts so column names are preserved for XGBoost
``feature_names_in_`` tracking.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# ── Size / seniority tables ────────────────────────────────────────────────────

_SIZE_ORDER = ["1-10", "10-50", "50-200", "200-500", "500+"]

_SENIORITY_MAP = {
    # C-suite keywords
    "ceo": 4, "cfo": 4, "coo": 4, "cto": 4, "ciso": 4,
    "chief": 4, "president": 4, "founder": 4, "co-founder": 4,
    # Director
    "director": 3, "vp": 3, "vice president": 3, "partner": 3,
    "principal": 3, "head of": 3,
    # Manager
    "manager": 2, "supervisor": 2, "lead": 2, "senior": 2,
    "sr.": 2, "team lead": 2,
    # Junior / individual contributor
    "analyst": 1, "associate": 1, "coordinator": 1,
    "specialist": 1, "executive": 1, "officer": 1,
}

_LIFE_EVENT_ORDER = {
    None:           0,
    "":             0,
    "job_change":   1,
    "marriage":     2,
    "new_baby":     3,
    "new_property": 4,
    "new_vehicle":  5,
    "policy_lapse": 6,
}

_INCOME_MAP = {
    # Malaysia (RM)
    "3k-6k": 1, "6k-10k": 2, "10k-20k": 3, "20k+": 4,
    # India (INR/month)
    "25k-50k": 1, "50k-100k": 2, "100k-200k": 3, "200k+": 4,
}

_REVENUE_MAP = {
    "<1m": 1, "1-10m": 2, "1m-10m": 2, "10-50m": 3, "10m-50m": 3,
    "50m+": 4, ">50m": 4,
}

_FUNDING_STAGES = {
    None: 0, "": 0,
    "pre-seed": 1, "seed": 2, "series_a": 3, "series a": 3,
    "series_b": 4, "series b": 4, "series_c": 5, "series c": 5,
    "growth": 5, "late-stage": 6, "ipo": 7, "public": 7,
}


# ── Private helpers ────────────────────────────────────────────────────────────

def encode_seniority(job_title: str) -> int:
    """
    Map a job title string to a seniority integer.

    Returns:
        0 = unknown, 1 = junior/individual, 2 = manager,
        3 = director/VP, 4 = C-suite/founder
    """
    if not job_title:
        return 0
    t = job_title.lower()
    for keyword, level in sorted(_SENIORITY_MAP.items(), key=lambda x: -x[1]):
        if keyword in t:
            return level
    return 1  # default: individual contributor


def encode_life_event(life_event: str | None) -> int:
    """
    Map a life_event string to an ordinal integer.

    Higher = stronger insurance purchase signal.
    Returns 0 for unknown/null.
    """
    return _LIFE_EVENT_ORDER.get(life_event or "", 0)


def encode_income(income_bracket: str | None) -> int:
    """Map income bracket string → 0–4. 0 = unknown."""
    if not income_bracket:
        return 0
    return _INCOME_MAP.get(income_bracket.lower().replace(" ", ""), 0)


def encode_revenue(revenue: str | None) -> int:
    """Map revenue string → 0–4. 0 = unknown."""
    if not revenue:
        return 0
    r = revenue.lower().replace(",", "").replace("$", "").replace("rm", "").strip()
    for k, v in _REVENUE_MAP.items():
        if k in r:
            return v
    return 0


def encode_vehicle_type(person: dict[str, Any]) -> int:
    """Encode vehicle type: 0=none, 1=commercial, 2=motorcycle, 3=car."""
    vt = (person.get("vehicle_type") or "").lower()
    return {"car": 3, "motorcycle": 2, "commercial": 1}.get(vt, 0)


def encode_property_type(person: dict[str, Any]) -> int:
    """Encode property type: 0=none, 1=commercial, 2=apartment, 3=landed."""
    pt = (person.get("property_type") or "").lower()
    return {"landed": 3, "apartment": 2, "commercial": 1}.get(pt, 0)


def icp_size_match(company: dict[str, Any], icp: dict[str, Any]) -> bool:
    """Return True if company employee_range is in ICP target sizes."""
    emp_range = company.get("employee_range") or ""
    icp_sizes = [str(s) for s in (icp.get("company_sizes") or [])]
    if not icp_sizes:
        return True
    return emp_range in icp_sizes


def icp_industry_match(company: dict[str, Any], icp: dict[str, Any]) -> bool:
    """Return True if company industry overlaps with ICP target industries."""
    ind = (company.get("industry") or "").lower().strip()
    if not ind:
        return False
    icp_inds = [str(i).lower().strip() for i in (icp.get("industries") or [])]
    if not icp_inds:
        return True
    return any(i and (i == ind or i in ind or ind in i) for i in icp_inds)


def icp_location_match(target: dict[str, Any], icp: dict[str, Any]) -> bool:
    """
    Return True if target location (city or country) is in ICP locations.
    Works for both company dict (city/country keys) and person dict (location key).
    """
    icp_locs = [str(loc).lower().strip() for loc in (icp.get("locations") or [])]
    if not icp_locs:
        return True

    # Try person-style location field first
    person_loc = (target.get("location") or "").lower()
    if person_loc and any(loc in person_loc or person_loc in loc for loc in icp_locs):
        return True

    # Try company-style city/country fields
    city    = (target.get("city")    or "").lower()
    country = (target.get("country") or "").lower()
    for loc in icp_locs:
        if loc and (loc in city or loc in country or city in loc or country in loc):
            return True
    return False


def icp_age_match(person: dict[str, Any], icp: dict[str, Any]) -> bool:
    """Return True if person age falls in any ICP age range."""
    age = person.get("age")
    if age is None:
        return False
    icp_ranges = icp.get("age_ranges") or []
    for bracket in icp_ranges:
        parts = str(bracket).replace(" ", "").split("-")
        if len(parts) == 2:
            try:
                lo, hi = int(parts[0]), int(parts[1])
                if lo <= int(age) <= hi:
                    return True
            except (ValueError, TypeError):
                pass
    return False


def calculate_company_age(company: dict[str, Any]) -> int:
    """Return years in business from founded_year, or 0 if unknown."""
    founded = company.get("founded_year")
    if not founded:
        # Try years_in_business string (e.g. "5 years")
        yib = str(company.get("years_in_business") or "")
        for part in yib.split():
            try:
                return int(part)
            except ValueError:
                pass
        return 0
    try:
        return max(0, datetime.now(timezone.utc).year - int(founded))
    except (TypeError, ValueError):
        return 0


def calculate_signal_age(person: dict[str, Any]) -> int:
    """Return days since the life event signal was detected. 999 if unknown."""
    event_date = person.get("life_event_date")
    if not event_date:
        return 999
    if isinstance(event_date, str):
        try:
            event_date = datetime.fromisoformat(event_date)
        except ValueError:
            return 999
    if event_date.tzinfo is None:
        event_date = event_date.replace(tzinfo=timezone.utc)
    return max(0, (datetime.now(timezone.utc) - event_date).days)


# ── Public feature extractors ──────────────────────────────────────────────────

def extract_b2b_features(
    lead: dict[str, Any],
    company: dict[str, Any],
    icp: dict[str, Any],
) -> dict[str, float]:
    """
    Extract 14 numeric B2B features for XGBoost.

    Args:
        lead:    Person dict (ZLPerson fields serialised as dict).
        company: Company dict (ZLCompany fields serialised as dict).
        icp:     ICP dict (ZLICP fields serialised as dict).

    Returns:
        Dict of feature_name → float value.
    """
    size_idx = next(
        (i for i, s in enumerate(_SIZE_ORDER)
         if s == (company.get("employee_range") or "")),
        0,
    )
    funding_val = _FUNDING_STAGES.get(
        (company.get("funding_stage") or "").lower().replace("-", "_"), 0
    )

    return {
        "company_size":       float(company.get("employee_count") or size_idx * 25),
        "company_size_match": 1.0 if icp_size_match(company, icp) else 0.0,
        "role_seniority":     float(encode_seniority(lead.get("job_title") or "")),
        "industry_match":     1.0 if icp_industry_match(company, icp) else 0.0,
        "location_match":     1.0 if icp_location_match(company, icp) else 0.0,
        "email_verified":     1.0 if lead.get("email_verified") else 0.0,
        "email_confidence":   float(lead.get("email_confidence") or 0.0),
        "has_phone":          1.0 if lead.get("phone") else 0.0,
        "has_website":        1.0 if company.get("website") else 0.0,
        "has_linkedin":       1.0 if lead.get("linkedin_url") else 0.0,
        "hiring_signal":      1.0 if company.get("is_hiring") else 0.0,
        "funding_signal":     float(funding_val),
        "company_age_years":  float(calculate_company_age(company)),
        "revenue_bracket":    float(encode_revenue(company.get("revenue"))),
    }


def extract_b2c_features(
    person: dict[str, Any],
    icp: dict[str, Any],
) -> dict[str, float]:
    """
    Extract 10 numeric B2C features for XGBoost.

    Args:
        person: ZLPerson fields serialised as dict (B2C-specific fields required).
        icp:    B2C ICP dict.

    Returns:
        Dict of feature_name → float value.
    """
    return {
        "life_event_type":    float(encode_life_event(person.get("life_event"))),
        "signal_days_old":    float(min(calculate_signal_age(person), 90)),
        "age":                float(person.get("age") or 35),
        "age_match":          1.0 if icp_age_match(person, icp) else 0.0,
        "income_bracket":     float(encode_income(person.get("income_bracket"))),
        "location_match":     1.0 if icp_location_match(person, icp) else 0.0,
        "email_verified":     1.0 if person.get("email_verified") else 0.0,
        "has_phone":          1.0 if person.get("phone") else 0.0,
        "vehicle_type_match": float(encode_vehicle_type(person)),
        "property_type_match": float(encode_property_type(person)),
    }


# ── Feature extraction from stored breakdown dict ──────────────────────────────
#
# Used by the trainer when full person/company/ICP data is not loaded —
# reads pre-computed sub-scores from the score_breakdown JSON column.

def extract_features_from_breakdown(
    breakdown: dict[str, Any],
    lead_type: str = "b2b",
    original_score: int = 0,
) -> dict[str, float]:
    """
    Extract a flat feature vector from a stored score_breakdown dict.

    This is the fast path used during model training — avoids re-joining
    all related tables. The breakdown stores partial sub-scores which the
    model can use to learn optimal re-weighting.

    Args:
        breakdown:      ``ZLLead.score_breakdown`` dict.
        lead_type:      "b2b" or "b2c"
        original_score: ``ZLScoringFeedback.original_score``
    """
    bd = breakdown or {}
    if lead_type == "b2c":
        return {
            "life_event":      float(bd.get("life_event", 0)),
            "location_match":  float(bd.get("location_match", 0)),
            "contact_found":   float(bd.get("contact_found", 0)),
            "signal_recency":  float(max(0, bd.get("signal_recency", 0))),
            "property_bonus":  float(bd.get("property_bonus", 0)),
            "loan_bonus":      float(bd.get("loan_bonus", 0)),
            "metro_bonus":     float(bd.get("metro_bonus", 0)),
            "original_score":  float(original_score),
        }
    # B2B default
    return {
        "company_size":      float(bd.get("company_size", 0)),
        "role":              float(bd.get("role", 0)),
        "industry":          float(bd.get("industry", 0)),
        "signals":           float(bd.get("signals", 0)),
        "email":             float(bd.get("email", 0)),
        "icp_match_bonus":   float(bd.get("icp_match_bonus", 0)),
        "original_score":    float(original_score),
    }
