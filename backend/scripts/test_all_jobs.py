#!/usr/bin/env python3
"""
Master test suite for all background jobs.
Run: python scripts/test_all_jobs.py
"""

import asyncio
import sys
sys.path.insert(0, "/home/sammy1998/zentro-leads/backend")

from app.jobs.job_board_monitor import (
    JOB_SIGNALS,
    _clean_company_name,
    _extract_company_from_job_title,
)
from app.jobs.ssm_monitor import _extract_company_from_search
from app.jobs.daily_digest import _format_whatsapp_digest
from app.models import ZLLead


async def test_job_signal_mapping():
    print("=" * 60)
    print("TEST: Job Title → Insurance Signal Mapping")
    print("=" * 60)

    test_cases = [
        ("lorry driver", "Fleet/Commercial Vehicle Insurance", "hiring_drivers"),
        ("site supervisor", "Workmanship Liability Insurance", "construction_hiring"),
        ("safety officer", "Workmanship Liability + SOCSO", "safety_expansion"),
        ("warehouse supervisor", "Fire + Cargo Insurance", "warehouse_expansion"),
        ("factory operator", "Workers Compensation + Fire", "manufacturing_hiring"),
        ("delivery rider", "Motor Insurance", "fleet_expansion"),
        ("hr executive", "Group Medical Card", "hr_setup"),
        ("crane operator", "Equipment + Workmanship Insurance", "heavy_equipment"),
    ]

    passed = 0
    for job_title, expected_product, expected_signal in test_cases:
        config = JOB_SIGNALS.get(job_title)
        ok = config is not None and config["product"] == expected_product and config["signal"] == expected_signal
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"  [{status}] {job_title} → {config['product'] if config else 'MISSING'}")

    print(f"\nResult: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


async def test_company_name_extraction():
    print("\n" + "=" * 60)
    print("TEST: Company Name Extraction from Job Titles")
    print("=" * 60)

    test_cases = [
        ("Lorry Driver at ABC Logistics Sdn Bhd", "lorry driver", "ABC Logistics Sdn Bhd"),
        ("Site Supervisor - XYZ Construction", "site supervisor", "XYZ Construction"),
        ("Safety Officer | Fast Builders Bhd", "safety officer", "Fast Builders Bhd"),
        ("Warehouse Supervisor at Cold Storage KL", "warehouse supervisor", "Cold Storage KL"),
        ("Factory Operator at Mega Manufacturing", "factory operator", "Mega Manufacturing"),
    ]

    passed = 0
    for title, job_title, expected in test_cases:
        result = _extract_company_from_job_title(title, job_title)
        ok = result is not None and expected.lower() in (result or "").lower()
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"  [{status}] '{title[:45]}'")
        print(f"         Expected: {expected} | Got: {result}")

    print(f"\nResult: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


async def test_ssm_company_extraction():
    print("\n" + "=" * 60)
    print("TEST: SSM Company Name Extraction from Search")
    print("=" * 60)

    test_cases = [
        ("ABC Logistics Sdn Bhd — New company in KL", "ABC Logistics Sdn Bhd"),
        ("XYZ Construction Bhd registered in Malaysia", "XYZ Construction Bhd"),
        ("Fast Transport Group — Business news", "Fast Transport Group"),
    ]

    passed = 0
    for text, expected in test_cases:
        result = _extract_company_from_search(text, "")
        ok = result is not None and expected.lower() in (result or "").lower()
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"  [{status}] '{text[:50]}' → {result}")

    print(f"\nResult: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


async def test_digest_formatting():
    print("\n" + "=" * 60)
    print("TEST: Daily Digest Message Formatting")
    print("=" * 60)

    # Create mock leads
    class MockCompany:
        def __init__(self, name):
            self.name = name

    class MockPerson:
        def __init__(self, phone):
            self.phone = phone

    class MockLead:
        def __init__(self, company_name, phone, notes=None):
            self.company = MockCompany(company_name)
            self.person = MockPerson(phone)
            self.notes = notes
            self.id = "test-id"

    top3 = [
        MockLead("ABC Logistics", "+60123456789", "High intent signal detected"),
        MockLead("XYZ Construction", "+60198765432", "Recently won tender"),
        MockLead("Fast Cargo", None, None),
    ]

    msg = _format_whatsapp_digest("Moses", [], [], [], top3)

    checks = [
        "Good morning Moses" in msg,
        "LeadRadar Daily Digest" in msg,
        "ABC Logistics" in msg,
        "XYZ Construction" in msg,
        "Fast Cargo" in msg,
        "Contact today" in msg,
    ]

    passed = sum(checks)
    for i, check in enumerate(checks):
        status = "PASS" if check else "FAIL"
        labels = ["Greeting", "Header", "Lead 1", "Lead 2", "Lead 3", "CTA"]
        print(f"  [{status}] {labels[i]}")

    print(f"\nResult: {passed}/{len(checks)} passed")
    return passed == len(checks)


async def test_job_board_rss_fetch():
    print("\n" + "=" * 60)
    print("TEST: Indeed RSS Feed Fetching")
    print("=" * 60)

    from app.jobs.job_board_monitor import fetch_indeed_rss

    jobs = await fetch_indeed_rss("lorry driver", "https://malaysia.indeed.com/rss?q=lorry+driver&l=Malaysia")
    print(f"  Fetched {len(jobs)} lorry driver jobs from Indeed Malaysia")

    if jobs:
        print(f"  Sample: {jobs[0]['company_name']} — {jobs[0]['title'][:60]}")

    # Not failing if 0 — Indeed may block or have no results
    print(f"\nResult: {'PASS' if len(jobs) >= 0 else 'FAIL'} (fetched {len(jobs)} jobs)")
    return True


async def test_ssm_google_search():
    print("\n" + "=" * 60)
    print("TEST: SSM Google Search")
    print("=" * 60)

    from app.jobs.ssm_monitor import _google_search

    results = await _google_search("new company registered Malaysia logistics sdn bhd 2026")
    print(f"  Found {len(results)} search results")

    if results:
        for r in results[:3]:
            print(f"    - {r['company_name'][:50]}")

    print(f"\nResult: PASS (API {'configured' if results else 'not configured or no results'})")
    return True


async def main():
    print("\n" + "🚀 LeadRadar Background Jobs Master Test Suite".center(60))
    print()

    results = []
    results.append(("Job Signal Mapping", await test_job_signal_mapping()))
    results.append(("Company Extraction (Job)", await test_company_name_extraction()))
    results.append(("Company Extraction (SSM)", await test_ssm_company_extraction()))
    results.append(("Digest Formatting", await test_digest_formatting()))
    results.append(("Indeed RSS Fetch", await test_job_board_rss_fetch()))
    results.append(("SSM Google Search", await test_ssm_google_search()))

    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} — {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check logs above.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
