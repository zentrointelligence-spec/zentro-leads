#!/usr/bin/env python3
"""
Recalculate lead scores for StratosNow ICP leads using updated scoring engine.
Standalone — no backend imports needed.
"""

import asyncio
import json

import asyncpg

POSTGRES_URL = "postgresql://zl_user:zl_pass@localhost:5433/zentro_leads"

SIZE_ORDER = ["1-10", "10-50", "50-200", "200-500", "500+"]


def _size_index(rng: str | None) -> int | None:
    if not rng:
        return None
    r = rng.strip()
    try:
        return SIZE_ORDER.index(r)
    except ValueError:
        return None


def _company_size_score(employee_range: str, icp_sizes: list[str]) -> int:
    if not icp_sizes:
        return 0
    idx = _size_index(employee_range)
    if idx is None:
        return 0
    icp_idxs = [_size_index(s) for s in icp_sizes]
    icp_idxs = [i for i in icp_idxs if i is not None]
    if not icp_idxs:
        return 0
    if idx in icp_idxs:
        return 30
    if any(abs(idx - j) == 1 for j in icp_idxs):
        return 15
    return 0


def _infer_seniority_from_title(title: str) -> str:
    t = (title or "").lower()
    if any(k in t for k in ("ceo", "cfo", "coo", "cto", "chief", "president", "founder")):
        return "c-level"
    if "director" in t or "vp" in t or "vice president" in t:
        return "director"
    if "manager" in t or "head of" in t:
        return "manager"
    return "individual"


def _role_score_fixed(job_title: str, icp_titles: list[str], icp_seniority: list[str]) -> int:
    jt = (job_title or "").lower().strip()
    titles = [t.lower() for t in (icp_titles or [])]
    if jt and any(t == jt for t in titles):
        return 25
    if jt and any(t and t in jt for t in titles):
        return 15
    senior = _infer_seniority_from_title(job_title)
    icp_sen = [s.lower() for s in (icp_seniority or [])]
    if senior.lower() in icp_sen:
        return 10
    return 0


def _industry_score(industry: str, icp_industries: list[str]) -> int:
    ind = (industry or "").lower().strip()
    if not ind:
        return 0
    inds = [i.lower().strip() for i in (icp_industries or []) if i]
    if not inds:
        return 0
    if any(i == ind for i in inds):
        return 20
    if any(i and (i in ind or ind in i) for i in inds):
        return 10
    return 0


def _signals_score(company: dict, person: dict, icp_signals: list[str], extra_signals: list[str] | None = None):
    signals_present: list[str] = []
    if company.get("is_hiring"):
        signals_present.append("hiring")
    if company.get("in_the_news"):
        signals_present.append("in_the_news")
    if person.get("job_changed_at"):
        signals_present.append("job_change")
    fs = company.get("funding_stage")
    if fs not in (None, "", []):
        signals_present.append("funded")
    for s in (extra_signals or []):
        if s and s not in signals_present:
            signals_present.append(s)
    icp_s = [str(s).lower() for s in (icp_signals or [])]
    matched = [s for s in signals_present if str(s).lower() in icp_s]
    score = min(len(matched) * 5, 15)
    return score, signals_present


def _email_score(person: dict) -> int:
    email = person.get("email") or ""
    confidence = float(person.get("email_confidence") or 0.0)
    if person.get("email_verified") and confidence >= 0.9:
        return 10
    if email and "@" in email:
        if confidence >= 0.7:
            return 10
        elif confidence > 0:
            return 5
    if email and confidence >= 0.5:
        return 5
    return 0


def calculate_lead_score(person: dict, company: dict, icp: dict, extra_signals: list[str] | None = None, icp_match_score: int | None = None):
    size_score = _company_size_score(company.get("employee_range"), icp.get("company_sizes") or [])
    role_score = _role_score_fixed(person.get("job_title") or "", icp.get("job_titles") or [], icp.get("seniority_levels") or [])
    industry_score = _industry_score(company.get("industry") or "", icp.get("industries") or [])
    signals_score, signals_present = _signals_score(company, person, icp.get("intent_signals") or [], extra_signals=extra_signals)
    email_sc = _email_score(person)

    total = size_score + role_score + industry_score + signals_score + email_sc

    icp_bonus = 0
    if icp_match_score is not None:
        if icp_match_score >= 90:
            icp_bonus = 25
        elif icp_match_score >= 75:
            icp_bonus = 15
        elif icp_match_score >= 60:
            icp_bonus = 10
    total += icp_bonus

    total = max(0, min(total, 100))

    if total >= 85:
        tier = "hot"
    elif total >= 60:
        tier = "warm"
    elif total >= 40:
        tier = "potential"
    else:
        tier = "cold"

    return {
        "score": total,
        "tier": tier,
        "breakdown": {
            "company_size": size_score,
            "role": role_score,
            "industry": industry_score,
            "signals": signals_score,
            "email": email_sc,
            "icp_match_bonus": icp_bonus,
            "signals_detected": signals_present,
        },
    }


async def recalculate():
    conn = await asyncpg.connect(POSTGRES_URL)

    icp_rows = await conn.fetch(
        "SELECT id FROM zl_icps WHERE name = 'StratosNow Insurance Malaysia'"
    )
    icp_ids = [str(r["id"]) for r in icp_rows]
    print(f"Found {len(icp_ids)} StratosNow ICPs: {icp_ids}")

    leads = await conn.fetch(
        """
        SELECT
            l.id,
            l.lead_score,
            l.lead_tier,
            l.icp_match_score,
            l.score_breakdown,
            l.intent_signals,
            p.full_name as person_name,
            p.job_title as person_job_title,
            p.email as person_email,
            p.email_verified as person_email_verified,
            p.email_confidence as person_email_confidence,
            p.phone as person_phone,
            c.name as company_name,
            c.industry as company_industry,
            c.employee_range as company_employee_range,
            c.is_hiring as company_is_hiring,
            c.in_the_news as company_in_the_news,
            c.funding_stage as company_funding_stage,
            i.industries as icp_industries,
            i.job_titles as icp_job_titles,
            i.seniority_levels as icp_seniority_levels,
            i.company_sizes as icp_company_sizes,
            i.intent_signals as icp_intent_signals
        FROM zl_leads l
        LEFT JOIN zl_people p ON l.person_id = p.id
        LEFT JOIN zl_companies c ON l.company_id = c.id
        LEFT JOIN zl_icps i ON l.icp_id = i.id
        WHERE l.icp_id = ANY($1)
        ORDER BY l.lead_score DESC
        """,
        icp_ids,
    )

    print(f"\nFound {len(leads)} leads to recalculate\n")

    updates = []
    for lead in leads:
        person = {
            "full_name": lead["person_name"] or "",
            "job_title": lead["person_job_title"] or "",
            "email": lead["person_email"] or "",
            "email_verified": lead["person_email_verified"] or False,
            "email_confidence": float(lead["person_email_confidence"] or 0),
            "phone": lead["person_phone"] or "",
        }
        company = {
            "name": lead["company_name"] or "",
            "industry": lead["company_industry"] or "",
            "employee_range": lead["company_employee_range"] or "",
            "is_hiring": lead["company_is_hiring"] or False,
            "in_the_news": lead["company_in_the_news"] or False,
            "funding_stage": lead["company_funding_stage"] or None,
        }
        icp = {
            "industries": json.loads(lead["icp_industries"]) if isinstance(lead["icp_industries"], str) else (lead["icp_industries"] or []),
            "job_titles": json.loads(lead["icp_job_titles"]) if isinstance(lead["icp_job_titles"], str) else (lead["icp_job_titles"] or []),
            "seniority_levels": json.loads(lead["icp_seniority_levels"]) if isinstance(lead["icp_seniority_levels"], str) else (lead["icp_seniority_levels"] or []),
            "company_sizes": json.loads(lead["icp_company_sizes"]) if isinstance(lead["icp_company_sizes"], str) else (lead["icp_company_sizes"] or []),
            "intent_signals": json.loads(lead["icp_intent_signals"]) if isinstance(lead["icp_intent_signals"], str) else (lead["icp_intent_signals"] or []),
        }
        extra_signals = json.loads(lead["intent_signals"]) if isinstance(lead["intent_signals"], str) else (lead["intent_signals"] or [])
        icp_match_score = lead["icp_match_score"]

        result = calculate_lead_score(
            person, company, icp,
            extra_signals=extra_signals,
            icp_match_score=icp_match_score,
        )

        old_score = lead["lead_score"]
        new_score = result["score"]
        new_tier = result["tier"]

        updates.append({
            "id": str(lead["id"]),
            "old_score": old_score,
            "new_score": new_score,
            "new_tier": new_tier,
            "company": lead["company_name"],
            "breakdown": result["breakdown"],
        })

        await conn.execute(
            """
            UPDATE zl_leads
            SET lead_score = $1,
                lead_tier = $2,
                score_breakdown = $3
            WHERE id = $4
            """,
            new_score,
            new_tier.upper(),
            json.dumps(result["breakdown"]),
            str(lead["id"]),
        )

    await conn.close()

    hot = [u for u in updates if u["new_score"] >= 85]
    warm = [u for u in updates if 75 <= u["new_score"] < 85]
    potential = [u for u in updates if 40 <= u["new_score"] < 75]
    cold = [u for u in updates if u["new_score"] < 40]

    print("=" * 70)
    print("📊 RECALCULATED SCORES — StratosNow Insurance Leads")
    print("=" * 70)
    print(f"\nHOT (≥85):     {len(hot)}")
    print(f"WARM (75-84):  {len(warm)}")
    print(f"POTENTIAL:     {len(potential)}")
    print(f"COLD:          {len(cold)}")
    print(f"TOTAL:         {len(updates)}")

    print("\n🏆 TOP 10 LEADS:")
    print("-" * 70)
    for u in sorted(updates, key=lambda x: x["new_score"], reverse=True)[:10]:
        delta = u["new_score"] - u["old_score"]
        print(f"  {u['company'][:45]:<45} | {u['old_score']:>3} → {u['new_score']:>3} (+{delta}) | {u['new_tier'].upper()}")

    print("\n📈 FULL BREAKDOWN:")
    print("-" * 70)
    for u in sorted(updates, key=lambda x: x["new_score"], reverse=True):
        delta = u["new_score"] - u["old_score"]
        bd = u["breakdown"]
        print(f"\n{u['company']}")
        print(f"  Old: {u['old_score']} → New: {u['new_score']} (+{delta}) | Tier: {u['new_tier'].upper()}")
        print(f"  Breakdown: size={bd['company_size']} role={bd['role']} industry={bd['industry']} signals={bd['signals']} email={bd['email']} icp_bonus={bd.get('icp_match_bonus', 0)}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(recalculate())
