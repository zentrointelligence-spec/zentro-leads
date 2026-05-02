#!/usr/bin/env python3
"""
Create ICP for StratosNow Insurance and generate leads.
Run from backend directory with: .venv/bin/python scripts/create_icp_and_generate.py
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from time import sleep

sys.path.insert(0, "/home/sammy1998/zentro-leads/backend")

from jose import jwt
import httpx

# ── Config ─────────────────────────────────────────────
BASE_URL = "http://localhost:8001"
JWT_SECRET = "0c0ba7e263d172f2e78cf3d578fb135f800d8bc49e193be82cda3b57efbda0bd"
ALGORITHM = "HS256"

USER_ID = "6fbafc38-11db-45c1-8fb4-6b3c9c39284f"
USER_EMAIL = "test@zentro.io"

# ── Create JWT token ───────────────────────────────────
def create_token():
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    payload = {
        "sub": USER_ID,
        "email": USER_EMAIL,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)

TOKEN = create_token()
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}
COOKIES = {"zentro_session": TOKEN}

# ── ICP Payload ────────────────────────────────────────
ICP_PAYLOAD = {
    "name": "StratosNow Insurance Malaysia",
    "description": "I am StratosNow, a licensed general insurance agency in Malaysia. I sell auto insurance, fire insurance, goods in transit coverage, workmanship liability insurance, travel insurance and group medical cards to SME businesses, logistics companies, transportation fleets, manufacturing plants, construction contractors and any employer with 10 or more staff in Malaysia.",
    "industries": [
        "Logistics", "Transportation", "Manufacturing", "Construction",
        "Food & Beverage", "Retail & Trading", "Property & Real Estate",
        "Engineering", "Import & Export", "Wholesale & Distribution"
    ],
    "job_titles": [
        "Director", "Managing Director", "Owner", "Proprietor", "CEO",
        "Chief Executive Officer", "General Manager", "Operations Manager",
        "Fleet Manager", "Logistics Manager", "Factory Manager", "Site Manager",
        "Project Manager", "HR Manager", "Admin Manager"
    ],
    "seniority_levels": ["c_suite", "director", "manager"],
    "company_size_min": 10,
    "company_size_max": 500,
    "employee_ranges": ["10-50", "50-200", "200-500"],
    "locations": [
        "Kuala Lumpur", "Petaling Jaya", "Shah Alam", "Subang Jaya", "Klang",
        "Selangor", "Johor Bahru", "Johor", "Penang", "George Town", "Ipoh",
        "Perak", "Melaka", "Negeri Sembilan", "Pahang", "Kedah", "Sabah", "Sarawak"
    ],
    "keywords": [
        "fleet", "cargo", "lorry", "truck", "warehouse", "factory",
        "manufacturing", "construction", "contractor", "workers", "employees",
        "logistics", "transport", "delivery", "shipping", "import export",
        "machinery", "equipment", "building", "renovation", "food processing",
        "cold storage", "retail", "trading", "distribution", "supply chain"
    ],
    "intent_signals": [
        "expanding", "hiring", "new_contract", "new_office", "new_vehicle",
        "new_warehouse", "government_tender", "growing_headcount",
        "in_the_news", "funded"
    ],
    "excluded_industries": [
        "Insurance", "Banking", "Finance", "Technology", "IT Services",
        "Software", "Telecommunications", "Education", "Healthcare",
        "Government", "Non-profit"
    ],
    "excluded_keywords": [
        "insurance broker", "insurance agent", "insurance company", "bank",
        "fintech", "software company", "IT company", "school", "hospital",
        "clinic", "government"
    ],
}

SEARCH_QUERIES = [
    "logistics company Kuala Lumpur",
    "transportation company Selangor",
    "construction contractor Shah Alam",
    "manufacturing company Klang",
    "warehouse operator Johor Bahru",
]

# ── API Helpers ────────────────────────────────────────
async def create_icp(client: httpx.AsyncClient) -> str:
    print("📝 Creating ICP: StratosNow Insurance Malaysia...")
    resp = await client.post("/api/v1/icp/", json=ICP_PAYLOAD)
    print(f"   Status: {resp.status_code}")
    if resp.status_code >= 400:
        print(f"❌ ICP creation failed: {resp.status_code} {resp.text}")
        raise SystemExit(1)
    data = resp.json()
    icp_id = data["id"]
    print(f"✅ ICP created: {icp_id}")
    return icp_id

async def generate_leads(client: httpx.AsyncClient, icp_id: str, query: str) -> dict:
    print(f"\n🔍 Generating leads for: '{query}'...")
    resp = await client.post("/api/v1/leads/generate/", json={"icp_id": icp_id, "search_queries": [query]})
    print(f"   Status: {resp.status_code}")
    if resp.status_code >= 400:
        print(f"⚠️  Generation warning: {resp.status_code} {resp.text}")
        return {}
    data = resp.json()
    print(f"   → {data.get('message', 'Queued')}")
    print(f"   → Estimated: {data.get('estimated_seconds', '?')} seconds")
    return data

async def fetch_leads(client: httpx.AsyncClient) -> list:
    all_leads = []
    page = 1
    while True:
        resp = await client.get(f"/api/v1/leads/?page={page}&per_page=100")
        if resp.status_code >= 400:
            print(f"❌ Failed to fetch leads: {resp.status_code} {resp.text[:200]}")
            break
        data = resp.json()
        items = data.get("items", [])
        all_leads.extend(items)
        if len(items) < 100:
            break
        page += 1
    return all_leads

async def fetch_stats(client: httpx.AsyncClient) -> dict:
    resp = await client.get("/api/v1/leads/stats/")
    if resp.status_code >= 400:
        return {}
    return resp.json()

async def poll_for_leads(client: httpx.AsyncClient, expected_min: int = 1, max_wait: int = 120) -> list:
    print(f"\n⏳ Polling for leads (max {max_wait}s)...")
    for i in range(max_wait // 5):
        leads = await fetch_leads(client)
        if len(leads) >= expected_min:
            print(f"   ✓ Found {len(leads)} leads after {(i+1)*5}s")
            return leads
        print(f"   ... {len(leads)} leads so far, waiting 5s")
        sleep(5)
    return await fetch_leads(client)

# ── Main ───────────────────────────────────────────────
async def main():
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    timeout = httpx.Timeout(120.0, connect=10.0)

    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers=HEADERS,
        cookies=COOKIES,
        limits=limits,
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        # 1. Create ICP
        icp_id = await create_icp(client)

        # 2. Generate leads for each search query
        for query in SEARCH_QUERIES:
            await generate_leads(client, icp_id, query)
            sleep(3)  # brief pause between batches

        # 3. Poll for leads to appear
        print("\n" + "─" * 60)
        print("Waiting for background generation to complete...")
        print("─" * 60)
        leads = await poll_for_leads(client, expected_min=1, max_wait=180)

        # 4. Fetch stats
        stats = await fetch_stats(client)

        # 5. Filter out excluded industries/keywords
        excluded_industries = set([i.lower() for i in ICP_PAYLOAD["excluded_industries"]])
        excluded_keywords = set([k.lower() for k in ICP_PAYLOAD["excluded_keywords"]])

        def is_valid(lead: dict) -> bool:
            company = lead.get("company") or {}
            industry = (company.get("industry") or "").lower()
            name = (company.get("name") or "").lower()
            desc = (company.get("description") or "").lower()

            # Exclude by industry
            if industry in excluded_industries:
                return False

            # Exclude by keyword in name/description
            combined = f"{name} {desc}"
            for kw in excluded_keywords:
                if kw in combined:
                    return False

            return True

        valid_leads = [l for l in leads if is_valid(l)]

        # 6. Analyze
        hot = [l for l in valid_leads if (l.get("lead_score") or 0) >= 85]
        warm = [l for l in valid_leads if 75 <= (l.get("lead_score") or 0) < 85]

        # Sort by score desc
        top_leads = sorted(valid_leads, key=lambda x: x.get("lead_score") or 0, reverse=True)[:5]

        print("\n" + "=" * 60)
        print("📊 LEAD GENERATION RESULTS — StratosNow Insurance")
        print("=" * 60)
        print(f"\nTotal leads generated:    {len(leads)}")
        print(f"Valid prospects:          {len(valid_leads)}")
        print(f"HOT (score ≥ 85):         {len(hot)}")
        print(f"WARM (score 75-84):       {len(warm)}")
        print(f"API Stats:                {json.dumps(stats, indent=2)}")

        print("\n🏆 TOP 5 HIGHEST SCORING LEADS:")
        print("-" * 60)
        for i, lead in enumerate(top_leads, 1):
            company = lead.get("company") or {}
            person = lead.get("person") or {}
            score = lead.get("lead_score") or 0
            tier = lead.get("lead_tier") or "unknown"
            signals = lead.get("intent_signals") or []

            print(f"\n{i}. {company.get('name', 'N/A')}")
            print(f"   Industry:  {company.get('industry') or 'N/A'}")
            print(f"   Score:     {score} ({tier.upper()})")
            print(f"   Phone:     {person.get('phone') or company.get('phone') or 'N/A'}")
            print(f"   Email:     {person.get('email') or 'N/A'}")
            print(f"   Why Now:   {', '.join(signals) if signals else 'No signals'}")

        print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
