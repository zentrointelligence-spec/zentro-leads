"""
Gemini normalizer tests.

ALL tests mock the Gemini model — the real API is never called.
We patch ``app.ai.gemini_client._get_model`` (the factory function)
and control the response via the model mock's ``generate_content`` return value.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.ai.gemini_client import (
    _parse_json_response,
    _strip_json_fence,
    normalize_industries_bulk,
    normalize_job_titles_bulk,
    normalize_locations_bulk,
    classify_insurance_needs_bulk,
)


def _make_model_mock(response_text: str) -> MagicMock:
    """Build a model mock whose generate_content returns response_text."""
    model = MagicMock()
    model.generate_content.return_value = SimpleNamespace(text=response_text)
    return model


# ── Internal helpers ───────────────────────────────────────────────────────────

async def test_strip_json_fence_with_json_prefix():
    raw = '```json\n{"a": "b"}\n```'
    assert _strip_json_fence(raw) == '{"a": "b"}'


async def test_strip_json_fence_without_prefix():
    raw = '```\n{"a": "b"}\n```'
    assert _strip_json_fence(raw) == '{"a": "b"}'


async def test_strip_json_fence_no_fences():
    raw = '{"a": "b"}'
    assert _strip_json_fence(raw) == '{"a": "b"}'


async def test_parse_json_response_direct_parse():
    result = _parse_json_response('{"key": "value"}')
    assert result == {"key": "value"}


async def test_parse_json_response_with_fence():
    result = _parse_json_response('```json\n{"key": "value"}\n```')
    assert result == {"key": "value"}


async def test_parse_json_response_embedded_json():
    """Regex fallback extracts JSON embedded in prose."""
    result = _parse_json_response('here is the answer: {"key": "value"} that is all')
    assert result == {"key": "value"}


async def test_parse_json_response_unparseable_returns_none():
    result = _parse_json_response("this is not json at all")
    assert result is None


# ── Industry Normalizer ────────────────────────────────────────────────────────

async def test_normalize_industries_standard_input():
    model = _make_model_mock('{"Manufacturing": "Manufacturing", "F&B": "Food & Beverage"}')
    with patch("app.ai.gemini_client._get_model", return_value=model):
        result = await normalize_industries_bulk(["Manufacturing", "F&B"])
    assert result["Manufacturing"] == "Manufacturing"
    assert result["F&B"] == "Food & Beverage"


async def test_normalize_industries_with_json_fence():
    """The normalizer must handle markdown-fenced JSON from Gemini."""
    model = _make_model_mock('```json\n{"mfg": "Manufacturing"}\n```')
    with patch("app.ai.gemini_client._get_model", return_value=model):
        result = await normalize_industries_bulk(["mfg"])
    assert result["mfg"] == "Manufacturing"


async def test_normalize_industries_malformed_json():
    """Malformed response returns a safe fallback — no crash."""
    model = _make_model_mock("here are the results: mfg → Manufacturing (probably)")
    with patch("app.ai.gemini_client._get_model", return_value=model):
        result = await normalize_industries_bulk(["mfg"])
    # Fallback must be a dict with the input key mapped to "Other"
    assert "mfg" in result
    assert result["mfg"] == "Other"


async def test_normalize_industries_empty_list():
    """Empty input returns empty dict without calling Gemini."""
    model = _make_model_mock("{}")
    with patch("app.ai.gemini_client._get_model", return_value=model) as mock_get:
        result = await normalize_industries_bulk([])
    assert result == {}
    # _get_model should NOT be called when there is nothing to normalise
    mock_get.assert_not_called()


async def test_normalize_industries_gemini_unavailable():
    """When _get_model returns None, all inputs get 'Other' — no exception raised."""
    with patch("app.ai.gemini_client._get_model", return_value=None):
        result = await normalize_industries_bulk(["SomeIndustry"])
    assert result["SomeIndustry"] == "Other"


async def test_normalize_industries_deduplication():
    """
    Duplicate inputs are deduplicated before the API call.
    Gemini should receive only UNIQUE values, saving tokens.
    """
    model = _make_model_mock('{"Manufacturing": "Manufacturing", "mfg": "Manufacturing"}')
    generate_calls: list = []

    def fake_generate(prompt):
        generate_calls.append(prompt)
        return SimpleNamespace(text='{"Manufacturing": "Manufacturing", "mfg": "Manufacturing"}')

    model.generate_content.side_effect = fake_generate

    with patch("app.ai.gemini_client._get_model", return_value=model):
        result = await normalize_industries_bulk(
            ["Manufacturing", "Manufacturing", "mfg"]
        )

    # Only one generate_content call should have been made
    assert model.generate_content.call_count == 1

    # The prompt's Input JSON array must contain only 2 unique values
    prompt_sent = generate_calls[0]
    # Extract the JSON array that was sent as input (after "Input: ")
    import re as _re
    input_match = _re.search(r'Input:\s*(\[.*?\])', prompt_sent)
    assert input_match, "Prompt must contain an 'Input: [...]' JSON array"
    import json as _json
    sent_inputs = _json.loads(input_match.group(1))
    assert len(sent_inputs) == 2  # 3 inputs, deduplicated to 2 unique values
    assert "Manufacturing" in sent_inputs
    assert "mfg" in sent_inputs

    # Both original inputs appear in the result
    assert "Manufacturing" in result
    assert "mfg" in result


# ── Job Title Normalizer ───────────────────────────────────────────────────────

async def test_normalize_job_titles_decision_maker_detection():
    """CEO is a decision maker; Office Boy is not."""
    model = _make_model_mock(
        '{"CEO": {"normalized": "CEO", "department": "Executive", "seniority": "c_suite", "is_decision_maker": true},'
        ' "Office Boy": {"normalized": "Office Assistant", "department": "Admin", "seniority": "junior", "is_decision_maker": false}}'
    )
    with patch("app.ai.gemini_client._get_model", return_value=model):
        result = await normalize_job_titles_bulk(["CEO", "Office Boy"])
    assert result["CEO"]["is_decision_maker"] is True
    assert result["Office Boy"]["is_decision_maker"] is False


async def test_normalize_job_titles_adversarial_input():
    """Null-like, empty, and special-char inputs must not raise."""
    model = _make_model_mock("{}")
    with patch("app.ai.gemini_client._get_model", return_value=model):
        # These should all return safe fallback values
        result = await normalize_job_titles_bulk(["", "12345", "!@#$%"])
    for k in ["", "12345", "!@#$%"]:
        if k in result:
            assert isinstance(result[k], dict)
            assert "seniority" in result[k]


async def test_normalize_job_titles_empty_list():
    """Empty input list returns empty dict without calling Gemini."""
    with patch("app.ai.gemini_client._get_model") as mock_get:
        result = await normalize_job_titles_bulk([])
    assert result == {}
    mock_get.assert_not_called()


# ── Location Normalizer ────────────────────────────────────────────────────────

async def test_normalize_locations_malaysia():
    """KL, Kuala Lumpur, Shah Alam all normalise to market='malaysia'."""
    mock_resp = (
        '{"KL": {"city": "Kuala Lumpur", "state": "Kuala Lumpur", "country": "Malaysia", "market": "malaysia"},'
        ' "Kuala Lumpur": {"city": "Kuala Lumpur", "state": "Kuala Lumpur", "country": "Malaysia", "market": "malaysia"},'
        ' "Shah Alam": {"city": "Shah Alam", "state": "Selangor", "country": "Malaysia", "market": "malaysia"}}'
    )
    model = _make_model_mock(mock_resp)
    with patch("app.ai.gemini_client._get_model", return_value=model):
        result = await normalize_locations_bulk(["KL", "Kuala Lumpur", "Shah Alam"])
    assert result["KL"]["market"] == "malaysia"
    assert result["Kuala Lumpur"]["market"] == "malaysia"
    assert result["Shah Alam"]["market"] == "malaysia"


async def test_normalize_locations_india():
    """Mumbai, Bombay, Bengaluru all map to market='india'."""
    mock_resp = (
        '{"Mumbai": {"city": "Mumbai", "state": "Maharashtra", "country": "India", "market": "india"},'
        ' "Bombay": {"city": "Mumbai", "state": "Maharashtra", "country": "India", "market": "india"},'
        ' "Bengaluru": {"city": "Bengaluru", "state": "Karnataka", "country": "India", "market": "india"}}'
    )
    model = _make_model_mock(mock_resp)
    with patch("app.ai.gemini_client._get_model", return_value=model):
        result = await normalize_locations_bulk(["Mumbai", "Bombay", "Bengaluru"])
    assert result["Mumbai"]["market"] == "india"
    assert result["Bombay"]["market"] == "india"
    assert result["Bengaluru"]["market"] == "india"


async def test_normalize_locations_ambiguous():
    """Unknown/ambiguous locations fall back gracefully — no crash."""
    model = _make_model_mock('{}')
    with patch("app.ai.gemini_client._get_model", return_value=model):
        result = await normalize_locations_bulk(["Springfield", "unknown city xyz"])
    # Must return something for each input without crashing
    for loc in ["Springfield", "unknown city xyz"]:
        assert loc in result
        assert "market" in result[loc]


async def test_normalize_locations_empty_list():
    """Empty input returns empty dict without calling Gemini."""
    with patch("app.ai.gemini_client._get_model") as mock_get:
        result = await normalize_locations_bulk([])
    assert result == {}
    mock_get.assert_not_called()


# ── Insurance Need Classifier ──────────────────────────────────────────────────

async def test_classify_insurance_needs_basic():
    """A logistics lead maps to 'motor'; a 5-person office maps to 'group_medical'."""
    mock_resp = '{"lead-1": "motor", "lead-2": "group_medical"}'
    model = _make_model_mock(mock_resp)
    leads = [
        {"id": "lead-1", "company_type": "Logistics", "size": 20, "signals": "delivery fleet"},
        {"id": "lead-2", "company_type": "Consultancy", "size": 8, "signals": "office"},
    ]
    with patch("app.ai.gemini_client._get_model", return_value=model):
        result = await classify_insurance_needs_bulk(leads)
    assert result["lead-1"] == "motor"
    assert result["lead-2"] == "group_medical"


async def test_classify_insurance_needs_unknown_type():
    """
    If Gemini returns an unrecognised insurance type, it falls back to 'other'
    rather than storing a raw string.
    """
    mock_resp = '{"lead-1": "umbrella_liability_xyz"}'  # not a valid type
    model = _make_model_mock(mock_resp)
    with patch("app.ai.gemini_client._get_model", return_value=model):
        result = await classify_insurance_needs_bulk([{"id": "lead-1"}])
    assert result["lead-1"] == "other"


async def test_classify_insurance_needs_empty_list():
    """Empty input returns empty dict without calling Gemini."""
    with patch("app.ai.gemini_client._get_model") as mock_get:
        result = await classify_insurance_needs_bulk([])
    assert result == {}
    mock_get.assert_not_called()
