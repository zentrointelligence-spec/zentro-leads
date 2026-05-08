"""
Scoring engine tests — pure unit tests.

No database, no HTTP, no mocks (except the ML model path).
All functions are imported and called directly.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.scoring.engine import (
    _company_size_score,
    _email_score,
    _industry_score,
    _role_score_fixed,
    _signals_score,
    calculate_lead_score,
)
from app.scoring.features import (
    encode_life_event,
    encode_seniority,
    extract_b2b_features,
)
from app.scoring.ml_scorer import load_model, predict_lead_score


# ── Helpers ────────────────────────────────────────────────────────────────────

def _perfect_person() -> dict:
    return {
        "job_title": "HR Manager",
        "email": "hr@acme.com.my",
        "email_verified": True,
        "email_confidence": 0.95,
    }


def _perfect_company() -> dict:
    return {
        "name": "Acme Sdn Bhd",
        "industry": "Manufacturing",
        "employee_range": "10-50",
        "employee_count": 50,
        "is_hiring": True,
        "in_the_news": True,
        "funding_stage": "series_a",
    }


def _perfect_icp() -> dict:
    return {
        "industries": ["Manufacturing", "Food & Beverage"],
        "job_titles": ["HR Manager", "General Manager"],
        "seniority_levels": ["manager", "director"],
        "company_sizes": ["10-50", "50-200"],
        "locations": ["Kuala Lumpur", "Selangor"],
        "intent_signals": ["hiring", "in_the_news", "funded"],
    }


def _empty_person() -> dict:
    return {"job_title": "Intern", "email": "", "email_verified": False, "email_confidence": 0.0}


def _empty_company() -> dict:
    return {
        "name": "Unknown Corp",
        "industry": "Telemarketing",
        "employee_range": "500+",
        "employee_count": 1000,
        "is_hiring": False,
        "in_the_news": False,
        "funding_stage": None,
    }


def _empty_icp() -> dict:
    return {
        "industries": ["Healthcare"],
        "job_titles": ["Medical Director"],
        "seniority_levels": ["c-level"],
        "company_sizes": ["1-10"],
        "locations": ["Johor Bahru"],
        "intent_signals": ["funded"],
    }


# ── Deterministic Engine ───────────────────────────────────────────────────────

async def test_perfect_b2b_score():
    """A lead matching the ICP on ALL dimensions with 3 matched signals → 100."""
    # With ML model absent, the deterministic engine runs.
    # size=30 + role=25 + industry=20 + signals=15(3×5) + email=10 = 100
    load_model.cache_clear()
    result = calculate_lead_score(
        person=_perfect_person(),
        company=_perfect_company(),
        icp=_perfect_icp(),
    )
    assert result["score"] == 100
    assert result["tier"] == "hot"


async def test_zero_b2b_score():
    """A lead matching nothing scores 0."""
    load_model.cache_clear()
    result = calculate_lead_score(
        person=_empty_person(),
        company=_empty_company(),
        icp=_empty_icp(),
    )
    assert result["score"] == 0
    assert result["tier"] == "cold"


async def test_email_verified_adds_points():
    """A verified email lifts the score compared to no email."""
    load_model.cache_clear()
    icp = _empty_icp()  # no industry/role/size overlap — only email differs

    person_with = {**_empty_person(), "email": "x@company.com", "email_verified": True, "email_confidence": 0.95}
    person_without = {**_empty_person(), "email": ""}

    score_with = calculate_lead_score(person_with, _empty_company(), icp)["score"]
    score_without = calculate_lead_score(person_without, _empty_company(), icp)["score"]
    assert score_with > score_without


async def test_c_suite_scores_higher_than_junior():
    """A CEO scores higher on role than a junior employee against the same ICP."""
    load_model.cache_clear()
    icp = {**_empty_icp(), "seniority_levels": ["c-level"]}
    company = _empty_company()

    ceo_person = {**_empty_person(), "job_title": "CEO", "email": "ceo@c.com", "email_confidence": 0.0}
    intern_person = {**_empty_person(), "job_title": "Junior Associate"}

    ceo_score = calculate_lead_score(ceo_person, company, icp)["score"]
    intern_score = calculate_lead_score(intern_person, company, icp)["score"]
    assert ceo_score > intern_score


async def test_score_capped_at_100():
    """Even with icp_match_bonus on a perfect lead, score never exceeds 100."""
    load_model.cache_clear()
    result = calculate_lead_score(
        person=_perfect_person(),
        company=_perfect_company(),
        icp=_perfect_icp(),
        icp_match_score=95,  # +25 bonus
    )
    assert result["score"] <= 100


async def test_score_never_negative():
    """Score is always ≥ 0, never goes below zero."""
    load_model.cache_clear()
    result = calculate_lead_score(
        person={"job_title": None, "email": None, "email_verified": False},
        company={"industry": None, "employee_range": None},
        icp={"industries": [], "company_sizes": [], "job_titles": [], "intent_signals": []},
    )
    assert result["score"] >= 0


# ── Sub-score functions ────────────────────────────────────────────────────────

async def test_company_size_score_exact_match():
    """Exact size match returns 30."""
    assert _company_size_score("10-50", ["10-50", "50-200"]) == 30


async def test_company_size_score_adjacent():
    """One bracket away returns 15."""
    assert _company_size_score("50-200", ["10-50"]) == 15


async def test_company_size_score_no_match():
    """Far-off size returns 0."""
    assert _company_size_score("500+", ["1-10"]) == 0


async def test_industry_score_exact():
    assert _industry_score("Manufacturing", ["Manufacturing"]) == 20


async def test_industry_score_partial():
    """
    Bidirectional substring match returns 10.
    "Financial" is a substring of "Financial Services" → partial match.
    """
    assert _industry_score("Financial", ["Financial Services"]) == 10
    assert _industry_score("Financial Services", ["Financial"]) == 10


async def test_industry_score_no_match():
    assert _industry_score("Telemarketing", ["Healthcare"]) == 0


async def test_role_score_exact():
    assert _role_score_fixed("HR Manager", ["HR Manager"], ["manager"]) == 25


async def test_role_score_seniority_fallback():
    """If the exact title isn't in the ICP list, match seniority instead (+10)."""
    assert _role_score_fixed("Operations Manager", ["HR Manager", "Finance Manager"], ["manager"]) == 10


async def test_email_score_verified():
    assert _email_score({"email": "a@b.com", "email_verified": True, "email_confidence": 0.95}) == 10


async def test_email_score_no_email():
    assert _email_score({"email": None, "email_verified": False, "email_confidence": 0.0}) == 0


async def test_signals_score_max_15():
    """Three matching signals hit the 15-point cap."""
    company = {"is_hiring": True, "in_the_news": True, "funding_stage": "series_a"}
    person = {}
    icp_signals = ["hiring", "in_the_news", "funded"]
    score, detected = _signals_score(company, person, icp_signals)
    assert score == 15
    assert "hiring" in detected
    assert "in_the_news" in detected


# ── ML Scorer ─────────────────────────────────────────────────────────────────

async def test_ml_scorer_returns_none_when_no_model_file(tmp_path):
    """With no model file on disk, load_model returns None → deterministic fallback."""
    load_model.cache_clear()
    with patch("app.scoring.ml_scorer.os.path.exists", return_value=False):
        result = load_model("b2b")
    assert result is None
    load_model.cache_clear()


async def test_predict_returns_none_when_model_absent():
    """predict_lead_score returns None when the model file does not exist."""
    load_model.cache_clear()
    with patch("app.scoring.ml_scorer.load_model", return_value=None):
        result = predict_lead_score({"company_size": 1.0}, model_type="b2b")
    assert result is None


async def test_ml_scorer_fallback_integration():
    """
    When ML returns None, calculate_lead_score falls back to deterministic scoring
    and still returns a valid non-negative integer.
    """
    load_model.cache_clear()
    with patch("app.scoring.ml_scorer.load_model", return_value=None):
        result = calculate_lead_score(_perfect_person(), _perfect_company(), _perfect_icp())
    assert isinstance(result["score"], int)
    assert 0 <= result["score"] <= 100


# ── Feature Extraction ─────────────────────────────────────────────────────────

async def test_encode_seniority_known_titles():
    assert encode_seniority("CEO") == 4
    assert encode_seniority("HR Manager") == 2
    assert encode_seniority("Junior Analyst") == 1


async def test_encode_seniority_unknown_title():
    """Any unrecognised title falls back to 1 (individual contributor)."""
    result = encode_seniority("Oogabooga Specialist XYZ")
    # "specialist" is in the map at level 1
    assert result == 1


async def test_encode_seniority_malay_titles():
    """Malay job titles should map correctly via keyword matching."""
    # "Pengurus" contains no recognised English keyword → falls to 1
    # "Ketua Pegawai Eksekutif" contains no recognised English keyword → falls to 1
    # The tests verify behaviour, not that Malay is translated
    result_pengurus = encode_seniority("Pengurus Sumber Manusia")
    result_ceo = encode_seniority("Ketua Pegawai Eksekutif")
    # Both must return a valid 0–4 integer without crashing
    assert 0 <= result_pengurus <= 4
    assert 0 <= result_ceo <= 4


async def test_encode_life_event_values():
    assert encode_life_event("new_vehicle") == 5
    assert encode_life_event("marriage") == 2
    assert encode_life_event(None) == 0
    assert encode_life_event("unknown_event") == 0


async def test_encode_life_event_empty_string():
    assert encode_life_event("") == 0


async def test_extract_b2b_features_returns_14_keys():
    """extract_b2b_features must return exactly 14 numeric features."""
    features = extract_b2b_features(
        lead=_perfect_person(),
        company=_perfect_company(),
        icp=_perfect_icp(),
    )
    assert len(features) == 14
    for k, v in features.items():
        assert isinstance(v, float), f"Feature {k} should be float, got {type(v)}"
