"""
Tender Monitor — Automatic lead detection from Malaysian business news RSS feeds.

Scrapes business news every 6 hours, detects tender wins and construction projects,
then upgrades existing leads to HOT or creates new leads with score=85.

Feeds monitored:
  - Bernama Business
  - The Edge Markets
  - The Star Business
  - Malay Mail Business
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger
from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import (
    LeadSource,
    LeadStatus,
    LeadTier,
    ZLCompany,
    ZLICP,
    ZLLead,
    ZLLeadHistory,
    ZLNotification,
    ZLPerson,
    ZLUser,
)

# ═══════════════════════════════════════════════════════════════
# RSS Sources
# ═══════════════════════════════════════════════════════════════

TENDER_RSS_FEEDS: dict[str, str] = {
    # Working Malaysian / SEA business news RSS feeds
    "fmt_business": "https://www.freemalaysiatoday.com/category/business/feed/",
    "businesstoday_my": "https://www.businesstoday.com.my/feed/",
    "malaysian_reserve": "https://themalaysianreserve.com/feed/",
    # NOTE: The following feeds are currently dead (404/empty/redirect):
    # "bernama_business": "https://www.bernama.com/en/rss/business",  # 404
    # "theedgemarkets": "https://theedgemarkets.com/rss",  # redirects to dead domain
    # "thestar_business": "https://thestar.com.my/rss/business",  # 404
    # "malaymail_business": "https://www.malaymail.com/rss/feed/business.xml",  # empty channel
}

# ═══════════════════════════════════════════════════════════════
# Detection Keywords
# ═══════════════════════════════════════════════════════════════

# ── Win verbs ── any of these + a project noun = tender win
WIN_VERBS: list[str] = [
    "wins", "awarded", "secures", "secured", "clinches", "clinched",
    "bags", "bagged", "receives", "received", "lands", "landed",
    "gets", "got", "menang", "dapat", "terima",
]

# ── Project nouns ──
PROJECT_NOUNS: list[str] = [
    "contract", "tender", "deal", "project", "kontrak", "projek",
]

# ── Industry keywords ── at least one must appear for the match
CONSTRUCTION_KEYWORDS: list[str] = [
    "construction",
    "logistics",
    "manufacturing",
    "transport",
    "highway",
    "building",
    "infrastructure",
    "warehouse",
    "cargo",
    "freight",
    "contractor",
    "pembinaan",
    "projek",
    "MRT",
    "LRT",
    "road",
    "bridge",
    "development",
    "developer",
    "property",
    "real estate",
    "earthworks",
    "civil engineering",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml,application/xml,text/xml,*/*",
}

# ═══════════════════════════════════════════════════════════════
# RSS Parsing
# ═══════════════════════════════════════════════════════════════


def _parse_rss_date(text: str | None) -> datetime | None:
    """Parse common RSS date formats."""
    if not text:
        return None
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%d %b %Y %H:%M:%S %z",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


async def fetch_rss_feed(name: str, url: str) -> list[dict[str, Any]]:
    """Fetch and parse a single RSS feed, returning raw items."""
    items: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            xml_text = resp.text
    except Exception as exc:
        logger.warning(f"Tender monitor RSS {name} fetch failed: {exc}")
        return []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning(f"Tender monitor RSS {name} parse error: {exc}")
        return []

    # RSS 2.0
    channel = root.find("channel")
    if channel is not None:
        entries = channel.findall("item")
    else:
        # Atom
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)

    for entry in entries[:40]:  # Check last 40 articles
        if channel is not None:
            title_elem = entry.find("title")
            desc_elem = entry.find("description") or entry.find("summary")
            link_elem = entry.find("link")
            date_elem = entry.find("pubDate") or entry.find("published")
            title = (title_elem.text or "").strip() if title_elem is not None else ""
            description = (desc_elem.text or "").strip() if desc_elem is not None else ""
            link = (link_elem.text or "").strip() if link_elem is not None else ""
            pub_date = (date_elem.text or "").strip() if date_elem is not None else ""
        else:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            title_elem = entry.find("atom:title", ns)
            desc_elem = entry.find("atom:summary", ns) or entry.find("atom:content", ns)
            link_elem = entry.find("atom:link", ns)
            date_elem = entry.find("atom:published", ns) or entry.find("atom:updated", ns)
            title = (title_elem.text or "").strip() if title_elem is not None else ""
            description = (desc_elem.text or "").strip() if desc_elem is not None else ""
            link = link_elem.get("href", "").strip() if link_elem is not None else ""
            pub_date = (date_elem.text or "").strip() if date_elem is not None else ""

        items.append({
            "source": name,
            "title": title,
            "description": description,
            "url": link,
            "published_at": _parse_rss_date(pub_date),
        })

    logger.info(f"Tender monitor RSS {name}: fetched {len(items)} items")
    return items


# ═══════════════════════════════════════════════════════════════
# Keyword Detection
# ═══════════════════════════════════════════════════════════════


def _is_tender_match(title: str, description: str) -> bool:
    """
    Return True if article matches ALL THREE:
      1. A win verb (e.g. 'wins', 'awarded', 'secures')
      2. A project noun (e.g. 'contract', 'tender', 'deal')
      3. A construction/logistics keyword (e.g. 'construction', 'logistics')
    """
    text = f"{title} {description}".lower()

    has_win_verb = any(v.lower() in text for v in WIN_VERBS)
    has_project_noun = any(n.lower() in text for n in PROJECT_NOUNS)
    has_construction = any(kw.lower() in text for kw in CONSTRUCTION_KEYWORDS)

    return has_win_verb and has_project_noun and has_construction


# ═══════════════════════════════════════════════════════════════
# Company Name Extraction
# ═══════════════════════════════════════════════════════════════


def _extract_company_name(title: str, description: str) -> str | None:
    """
    Extract the company name from a tender headline.
    Uses heuristics; optional Claude fallback if ANTHROPIC_API_KEY is set.

    Examples:
      "ABC Construction wins RM500m highway contract" → "ABC Construction"
      "XYZ Logistics awarded warehouse tender" → "XYZ Logistics"
    """
    text = title or ""
    text_lower = text.lower()

    # ── Heuristic patterns ─────────────────────────────────────
    # Pattern: "COMPANY wins/awarded/secures/bags ..."
    markers = [
        " wins ", " awarded ", " secures ", " secured ", " bags ",
        " clinches ", " receives ", " lands ", " gets ",
        " menang ", " dapat ",
    ]
    for marker in markers:
        if marker in text_lower:
            before = text.split(marker, 1)[0].strip()
            # Clean up leading noise
            before = re.sub(r"^(update|breaking|exclusive)\s*[:\-]\s*", "", before, flags=re.I)
            before = before.strip()
            if len(before) >= 3 and len(before) <= 120:
                return before

    # Pattern: "... contract to COMPANY" or "... awarded to COMPANY"
    to_markers = [" contract to ", " awarded to ", " tender to ", " deal to "]
    for marker in to_markers:
        if marker in text_lower:
            after = text.split(marker, 1)[1].strip()
            # Take first 2-5 words as company name
            words = after.split()
            candidate = " ".join(words[:5]).strip()
            candidate = re.sub(r"[,.;:!?].*$", "", candidate)
            if len(candidate) >= 3:
                return candidate

    # Pattern: "COMPANY Sdn Bhd wins..."
    sdn_match = re.search(r"^([^,]+?\s+(?:Sdn\s+Bhd|Bhd|Ltd|Inc|Group|Corp))", text, re.I)
    if sdn_match:
        return sdn_match.group(1).strip()

    # Fallback: first 3-5 words if the title looks like "COMPANY something something"
    words = text.split()
    if len(words) >= 3:
        candidate = " ".join(words[:4]).strip()
        candidate = re.sub(r"[,.;:!?].*$", "", candidate)
        if len(candidate) >= 3 and not candidate.lower().startswith(("the ", "a ", "an ", "update")):
            return candidate

    return None


async def _extract_company_name_with_claude(title: str, description: str) -> str | None:
    """Optional Claude-based extraction if API key is available."""
    if not settings.ANTHROPIC_API_KEY:
        return None

    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        prompt = (
            f"Extract ONLY the company name from this news headline. "
            f"Return just the company name, nothing else.\n\n"
            f"Headline: {title}\n"
            f"Description: {description[:200]}"
        )
        message = await client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=64,
            messages=[{"role": "user", "content": prompt}],
        )
        name = message.content[0].text.strip()
        name = re.sub(r"^(the company name is|company:)\s*", "", name, flags=re.I)
        return name if len(name) >= 3 else None
    except Exception as exc:
        logger.debug(f"Claude company extraction failed: {exc}")
        return None


async def extract_company_name(title: str, description: str) -> str | None:
    """Best-effort company extraction: heuristic first, Claude fallback."""
    heuristic = _extract_company_name(title, description)
    if heuristic:
        return heuristic
    return await _extract_company_name_with_claude(title, description)


# ═══════════════════════════════════════════════════════════════
# Database Operations
# ═══════════════════════════════════════════════════════════════


async def _find_company_by_name(db, name: str) -> ZLCompany | None:
    """Fuzzy match company by name."""
    if not name or len(name) < 3:
        return None

    # Exact match first
    result = await db.execute(
        select(ZLCompany).where(func.lower(ZLCompany.name) == name.lower())
    )
    company = result.scalar_one_or_none()
    if company:
        return company

    # Substring match
    like_pattern = f"%{name.lower()}%"
    result = await db.execute(
        select(ZLCompany).where(func.lower(ZLCompany.name).like(like_pattern)).limit(1)
    )
    company = result.scalar_one_or_none()
    if company:
        return company

    # Reverse: does the company name appear in the tender name?
    result = await db.execute(
        select(ZLCompany).where(
            func.lower(ZLCompany.name).like(f"%{name.lower().split()[0]}%")
        ).limit(5)
    )
    candidates = result.scalars().all()
    for c in candidates:
        c_words = set((c.name or "").lower().split())
        n_words = set(name.lower().split())
        overlap = len(c_words & n_words)
        if overlap >= max(1, min(len(c_words), len(n_words)) // 2):
            return c

    return None


async def _find_existing_lead(db, user_id: str, company_id: str) -> ZLLead | None:
    """Find an existing lead for this user + company."""
    result = await db.execute(
        select(ZLLead)
        .where(
            ZLLead.user_id == user_id,
            ZLLead.company_id == company_id,
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _create_synthetic_person(db, company_id: str, company_name: str) -> ZLPerson:
    """Create a placeholder decision-maker for a tender-detected company."""
    person = ZLPerson(
        company_id=company_id,
        full_name="Decision Maker",
        first_name="Decision",
        last_name="Maker",
        job_title="Director",
        seniority="director",
        data_source=LeadSource.NEWS,
    )
    db.add(person)
    await db.flush()
    return person


async def _create_tender_lead(
    db,
    user_id: str,
    icp_id: str | None,
    company_id: str,
    person_id: str,
    article: dict[str, Any],
) -> ZLLead:
    """Create a new HOT lead from a tender detection."""
    why_now = (
        f"Detected via Tender Monitor ({article['source']}): "
        f"{article['title'][:120]}. "
        f"Company won/awarded a contract — high insurance need signal."
    )

    lead = ZLLead(
        user_id=user_id,
        icp_id=icp_id,
        person_id=person_id,
        company_id=company_id,
        lead_score=85,
        lead_tier=LeadTier.HOT,
        score_breakdown={
            "company_size": 0,
            "role": 0,
            "industry": 0,
            "signals": 0,
            "email": 0,
            "icp_bonus": 0,
            "email_bonus": 0,
            "tender_boost": 85,
        },
        intent_signals=["tender_win", "in_the_news"],
        status=LeadStatus.NEW,
        source=LeadSource.NEWS,
        notes=why_now,
        icp_match_score=75,
        icp_verdict="Strong fit",
        icp_reason="Company recently won a tender — immediate insurance opportunity",
    )
    db.add(lead)
    await db.flush()

    # History entry
    hist = ZLLeadHistory(
        lead_id=lead.id,
        event_type="tender_detected",
        new_value="hot",
        note=why_now,
        created_by="system",
    )
    db.add(hist)
    await db.flush()

    return lead


async def _upgrade_lead_to_hot(db, lead: ZLLead, article: dict[str, Any]) -> None:
    """Upgrade an existing lead to HOT due to tender detection."""
    old_tier = lead.lead_tier.value if lead.lead_tier else "unknown"
    old_score = lead.lead_score or 0

    lead.lead_score = max(old_score, 85)
    lead.lead_tier = LeadTier.HOT

    signals = list(lead.intent_signals or [])
    if "tender_win" not in signals:
        signals.append("tender_win")
    if "in_the_news" not in signals:
        signals.append("in_the_news")
    lead.intent_signals = signals

    note_addition = (
        f"\n\n[Tender Monitor {datetime.now(timezone.utc).strftime('%Y-%m-%d')}] "
        f"Company won contract: {article['title'][:120]}"
    )
    lead.notes = (lead.notes or "") + note_addition

    await db.flush()

    hist = ZLLeadHistory(
        lead_id=lead.id,
        event_type="score_updated",
        old_value=str(old_score),
        new_value=str(lead.lead_score),
        note=f"Upgraded to HOT via Tender Monitor: {article['title'][:100]}",
        created_by="system",
    )
    db.add(hist)
    await db.flush()

    logger.info(
        f"Upgraded lead {lead.id} to HOT (score {old_score}→{lead.lead_score}) "
        f"via tender detection: {article['title'][:80]}"
    )


async def _get_active_users_with_icps(db) -> list[tuple[ZLUser, list[ZLICP]]]:
    """Return active users and their active ICPs."""
    result = await db.execute(
        select(ZLUser)
        .where(ZLUser.is_active == True)
        .options(selectinload(ZLUser.icps))
    )
    users = result.scalars().unique().all()
    out: list[tuple[ZLUser, list[ZLICP]]] = []
    for user in users:
        active_icps = [icp for icp in user.icps if icp.is_active]
        if active_icps:
            out.append((user, active_icps))
    return out


async def _get_admin_users(db) -> list[ZLUser]:
    """Return users who should receive admin alerts (all active for now)."""
    result = await db.execute(
        select(ZLUser).where(ZLUser.is_active == True)
    )
    return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════════
# WhatsApp Alert
# ═══════════════════════════════════════════════════════════════


async def send_whatsapp_alert(message: str, to_number: str | None = None) -> bool:
    """
    Send WhatsApp alert via Twilio.
    Falls back to logger if Twilio is not configured.
    """
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.info(f"[WhatsApp Alert - no Twilio config] {message}")
        return False

    from_number = settings.TWILIO_WHATSAPP_NUMBER or settings.TWILIO_PHONE_NUMBER
    if not from_number:
        logger.info(f"[WhatsApp Alert - no sender number] {message}")
        return False

    target = to_number
    if not target:
        logger.info(f"[WhatsApp Alert - no target number] {message}")
        return False

    # Ensure WhatsApp prefix
    if not target.startswith("whatsapp:"):
        target = f"whatsapp:{target}"
    if not from_number.startswith("whatsapp:"):
        from_number = f"whatsapp:{from_number}"

    try:
        import twilio.rest
        client = twilio.rest.Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            from_=from_number,
            to=target,
            body=message[:1600],  # Twilio limit safety
        )
        logger.info(f"WhatsApp alert sent to {target}")
        return True
    except Exception as exc:
        logger.warning(f"WhatsApp alert failed: {exc}")
        return False


async def create_in_app_notification(
    db, user_id: str, title: str, body: str, link: str = ""
) -> None:
    """Create an in-app notification for the user."""
    notif = ZLNotification(
        user_id=user_id,
        type="hot_lead_found",
        title=title,
        body=body,
        link=link or "/dashboard/leads",
    )
    db.add(notif)
    await db.flush()


# ═══════════════════════════════════════════════════════════════
# Main Job
# ═══════════════════════════════════════════════════════════════


async def run_tender_monitor() -> dict[str, Any]:
    """
    Main tender monitor job.

    1. Scrape all RSS feeds
    2. Detect tender win + construction keywords
    3. Extract company names
    4. Find/create companies in DB
    5. Upgrade existing leads or create new HOT leads
    6. Send WhatsApp alerts + in-app notifications

    Returns summary dict for logging.
    """
    logger.info("Tender Monitor: starting scan...")
    summary: dict[str, Any] = {
        "feeds_scanned": 0,
        "articles_checked": 0,
        "matches_found": 0,
        "companies_extracted": 0,
        "leads_upgraded": 0,
        "leads_created": 0,
        "notifications_sent": 0,
        "errors": 0,
    }

    # ── Fetch all feeds ──────────────────────────────────────────
    all_articles: list[dict[str, Any]] = []
    for name, url in TENDER_RSS_FEEDS.items():
        try:
            items = await fetch_rss_feed(name, url)
            summary["feeds_scanned"] += 1
            all_articles.extend(items)
        except Exception as exc:
            logger.warning(f"Tender monitor feed {name} error: {exc}")
            summary["errors"] += 1

    summary["articles_checked"] = len(all_articles)
    logger.info(f"Tender Monitor: checked {len(all_articles)} articles from {summary['feeds_scanned']} feeds")

    # ── Detect matches ───────────────────────────────────────────
    matches: list[dict[str, Any]] = []
    for article in all_articles:
        if _is_tender_match(article["title"], article["description"]):
            company_name = await extract_company_name(article["title"], article["description"])
            if company_name:
                article["company_name"] = company_name
                matches.append(article)
                logger.info(f"Tender match: '{company_name}' — {article['title'][:100]}")
            else:
                logger.debug(f"Tender match but no company extracted: {article['title'][:100]}")

    summary["matches_found"] = len(matches)
    summary["companies_extracted"] = len({m.get("company_name") for m in matches if m.get("company_name")})

    if not matches:
        logger.info("Tender Monitor: no matches found. Scan complete.")
        return summary

    # ── Database operations ──────────────────────────────────────
    async with AsyncSessionLocal() as db:
        try:
            users_with_icps = await _get_active_users_with_icps(db)
            admin_users = await _get_admin_users(db)

            # Track what we notify about
            alert_lines: list[str] = []

            for article in matches:
                company_name = article.get("company_name")
                if not company_name:
                    continue

                # Find or create company
                company = await _find_company_by_name(db, company_name)
                if company:
                    logger.info(f"Tender Monitor: existing company '{company.name}' matched for '{company_name}'")
                else:
                    company = ZLCompany(
                        name=company_name,
                        industry="Construction / Logistics",  # Best guess
                        country="Malaysia",
                        data_source=LeadSource.NEWS,
                        in_the_news=True,
                        news_summary=article["title"],
                    )
                    db.add(company)
                    await db.flush()
                    logger.info(f"Tender Monitor: created new company '{company_name}'")

                # Process for each active user
                for user, icps in users_with_icps:
                    try:
                        # Pick the first active ICP (or none if we just want a general lead)
                        primary_icp = icps[0] if icps else None

                        existing_lead = await _find_existing_lead(db, user.id, company.id)
                        if existing_lead:
                            # Upgrade to HOT
                            was_hot = existing_lead.lead_tier == LeadTier.HOT
                            await _upgrade_lead_to_hot(db, existing_lead, article)
                            if not was_hot:
                                summary["leads_upgraded"] += 1
                                alert_lines.append(
                                    f"🔥 UPGRADED: {company.name} → HOT for {user.full_name}"
                                )
                            await create_in_app_notification(
                                db,
                                user.id,
                                title=f"{company.name} upgraded to HOT",
                                body=f"Tender win detected: {article['title'][:100]}",
                                link=f"/dashboard/leads?id={existing_lead.id}",
                            )
                        else:
                            # Create new lead — but check user limits first
                            current_used = user.leads_used_this_month or 0
                            current_limit = user.leads_limit or 0
                            if current_limit > 0 and current_used >= current_limit:
                                logger.info(
                                    f"Skip tender lead for user {user.id}: limit reached "
                                    f"({current_used}/{current_limit})"
                                )
                                continue

                            person = await _create_synthetic_person(db, company.id, company.name)
                            lead = await _create_tender_lead(
                                db, user.id, primary_icp.id if primary_icp else None,
                                company.id, person.id, article
                            )
                            summary["leads_created"] += 1

                            # Increment user's lead count
                            await db.execute(
                                update(ZLUser)
                                .where(ZLUser.id == user.id)
                                .values(leads_used_this_month=func.coalesce(ZLUser.leads_used_this_month, 0) + 1)
                            )
                            await db.flush()

                            alert_lines.append(
                                f"🆕 NEW HOT: {company.name} (score 85) for {user.full_name}"
                            )
                            await create_in_app_notification(
                                db,
                                user.id,
                                title=f"New HOT lead: {company.name}",
                                body=f"Tender win detected: {article['title'][:100]}",
                                link=f"/dashboard/leads?id={lead.id}",
                            )

                    except Exception as exc:
                        logger.error(f"Tender monitor user {user.id} processing error: {exc}")
                        summary["errors"] += 1
                        continue

            # ── Commit all DB changes ──────────────────────────────
            await db.commit()

            # ── WhatsApp alerts ────────────────────────────────────
            if alert_lines:
                alert_msg = (
                    "🚨 *LeadRadar Tender Alert*\n\n"
                    + "\n".join(alert_lines[:10])  # Limit to 10 lines
                    + f"\n\nTotal changes: {summary['leads_upgraded']} upgraded, {summary['leads_created']} new"
                )
                for admin in admin_users:
                    if admin.phone:
                        sent = await send_whatsapp_alert(alert_msg, admin.phone)
                        if sent:
                            summary["notifications_sent"] += 1

        except Exception as exc:
            await db.rollback()
            logger.exception(f"Tender Monitor database error: {exc}")
            summary["errors"] += 1

    logger.info(
        f"Tender Monitor: scan complete. "
        f"matches={summary['matches_found']}, upgraded={summary['leads_upgraded']}, "
        f"created={summary['leads_created']}, errors={summary['errors']}"
    )
    return summary
