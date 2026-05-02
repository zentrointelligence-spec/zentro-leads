#!/usr/bin/env python3
"""
Test script for the Tender Monitor.
Run: python scripts/test_tender_monitor.py
"""

import asyncio
import sys
sys.path.insert(0, "/home/sammy1998/zentro-leads/backend")

from app.jobs.tender_monitor import (
    TENDER_RSS_FEEDS,
    WIN_VERBS,
    PROJECT_NOUNS,
    CONSTRUCTION_KEYWORDS,
    _is_tender_match,
    _extract_company_name,
    extract_company_name,
    fetch_rss_feed,
    run_tender_monitor,
)


async def test_keyword_detection():
    """Test the keyword matching logic."""
    print("=" * 60)
    print("TEST 1: Keyword Detection")
    print("=" * 60)
    print(f"Win verbs: {WIN_VERBS}")
    print(f"Project nouns: {PROJECT_NOUNS}")
    print(f"Construction keywords: {CONSTRUCTION_KEYWORDS[:5]}...")
    print()

    test_cases = [
        ("ABC Construction wins RM500m highway contract", True),
        ("XYZ Logistics awarded warehouse tender in KL", True),
        ("Tech startup raises $2M funding", False),
        ("Local firm menang tender pembinaan jambatan", True),
        ("Global Corp launches new product line", False),
        ("Fast Cargo dapat kontrak logistik besar", True),
        ("Bank announces quarterly earnings", False),
        ("Building contractor secures infrastructure deal", True),
        ("Restaurant opens new branch in PJ", False),
        ("Gamuda clinches MRT3 construction deal", True),
        ("WCT bags RM1.2bn highway project", True),
        ("Company awarded supply contract", False),  # no construction keyword
    ]

    passed = 0
    for title, expected in test_cases:
        result = _is_tender_match(title, "")
        status = "PASS" if result == expected else "FAIL"
        if result == expected:
            passed += 1
        print(f"  [{status}] '{title[:50]}...' → match={result} (expected={expected})")

    print(f"\nResult: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


async def test_company_extraction():
    """Test company name extraction from headlines."""
    print("\n" + "=" * 60)
    print("TEST 2: Company Name Extraction")
    print("=" * 60)

    test_cases = [
        ("ABC Construction wins RM500m highway contract", "ABC Construction"),
        ("XYZ Logistics awarded warehouse tender in KL", "XYZ Logistics"),
        ("WCT Engineering Bhd secures MRT contract", "WCT Engineering Bhd"),
        ("Fast Cargo Logistics bags freight contract", "Fast Cargo Logistics"),
        ("Gamuda Berhad clinches Penang infrastructure deal", "Gamuda Berhad"),
        ("Local firm menang tender pembinaan", "Local firm"),
        ("Mega Transport Sdn Bhd receives logistics contract", "Mega Transport Sdn Bhd"),
    ]

    passed = 0
    for title, expected in test_cases:
        result = _extract_company_name(title, "")
        # Fuzzy check: extracted name should contain expected or vice versa
        ok = False
        if result and expected:
            r_lower = result.lower()
            e_lower = expected.lower()
            ok = e_lower in r_lower or r_lower in e_lower
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"  [{status}] '{title[:55]}'")
        print(f"         Expected: {expected}")
        print(f"         Got:      {result}")

    print(f"\nResult: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


async def test_rss_fetch():
    """Test RSS feed fetching."""
    print("\n" + "=" * 60)
    print("TEST 3: RSS Feed Fetching")
    print("=" * 60)

    all_items = []
    for name, url in TENDER_RSS_FEEDS.items():
        try:
            items = await fetch_rss_feed(name, url)
            all_items.extend(items)
            print(f"  {name}: {len(items)} items fetched")
            if items:
                print(f"    Latest: {items[0]['title'][:70]}...")
        except Exception as exc:
            print(f"  {name}: ERROR - {exc}")

    print(f"\nTotal items fetched: {len(all_items)}")
    return len(all_items) > 0


async def test_full_pipeline():
    """Test the full tender monitor pipeline against real feeds."""
    print("\n" + "=" * 60)
    print("TEST 4: Full Pipeline (Live RSS Scan)")
    print("=" * 60)

    summary = await run_tender_monitor()
    print(f"\nSummary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    return summary["errors"] == 0


async def main():
    print("\n" + "🚀 LeadRadar Tender Monitor Test Suite".center(60))
    print()

    results = []
    results.append(("Keyword Detection", await test_keyword_detection()))
    results.append(("Company Extraction", await test_company_extraction()))
    results.append(("RSS Fetching", await test_rss_fetch()))
    results.append(("Full Pipeline", await test_full_pipeline()))

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
