"""
RSS funding news monitor.
Tracks funding announcements from SEA + Middle East tech media.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
from loguru import logger

# ── RSS Feed Sources ─────────────────────────────────────────
# NOTE: Only active/working feeds. Dead feeds commented out to reduce noise.
RSS_FEEDS = {
    # "techcrunch_asia": "https://techcrunch.com/category/asia/feed/",  # 404 dead
    # "vulcan_post": "https://vulcanpost.com/feed/",  # works but 0 funding articles
    "wamda": "https://www.wamda.com/feed",  # Middle East funding news (working)
    # "the_edge_malaysia": "https://theedgemalaysia.com/rss",  # 404 dead
}

# ── Keywords that indicate funding news ──────────────────────
FUNDING_KEYWORDS = {
    "funding",
    "raised",
    "seed",
    "series a",
    "series b",
    "series c",
    "venture capital",
    "vc",
    "investment",
    "invested",
    "million",
    "pre-seed",
    "angel",
    "private equity",
    "valuation",
    "unicorn",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml,application/xml,text/xml,*/*",
}


def _parse_rss_date(text: str | None) -> datetime | None:
    """Parse common RSS date formats."""
    if not text:
        return None
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _is_funding_article(title: str | None, description: str | None) -> bool:
    """Heuristic: does this article mention funding?"""
    text = f"{title or ''} {description or ''}".lower()
    return any(kw in text for kw in FUNDING_KEYWORDS)


def _extract_company_name(title: str | None, description: str | None) -> str | None:
    """
    Naive company name extraction from funding headlines.
    E.g. 'Singapore startup Grab raises $1B' → 'Grab'
    """
    text = title or ""
    text_lower = text.lower()

    # Simple patterns
    markers = [
        " raises ", " raised ", " secures ", " secured ",
        " gets ", " receives ", " closes ", " lands ",
        " announces ", " bags ",
    ]
    for marker in markers:
        if marker in text_lower:
            # Take words before the marker
            before = text_lower.split(marker)[0]
            # Remove common prefixes
            for prefix in [
                "singapore ", "malaysian ", "indonesian ", "thai ",
                "vietnamese ", "philippine ", "dubai ", "uae ",
                "startup ", "company ", "firm ", "platform ",
            ]:
                before = before.replace(prefix, "")
            # Return last 2-3 words as likely company name
            words = before.strip().split()
            if words:
                candidate = " ".join(words[-3:]).strip().title()
                if len(candidate) > 2:
                    return candidate
    return None


async def fetch_rss_feed(name: str, url: str) -> list[dict[str, Any]]:
    """Fetch and parse a single RSS feed."""
    articles: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=20.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            xml_text = resp.text
    except Exception as exc:
        logger.warning(f"RSS feed {name} failed: {exc}")
        return []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning(f"RSS feed {name} parse error: {exc}")
        return []

    # Handle both RSS 2.0 and Atom formats
    channel = root.find("channel")
    if channel is not None:
        items = channel.findall("item")
    else:
        # Atom
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall("atom:entry", ns)

    for item in items[:30]:  # Check last 30 articles
        if channel is not None:
            title_elem = item.find("title")
            desc_elem = item.find("description") or item.find("summary")
            link_elem = item.find("link")
            date_elem = item.find("pubDate") or item.find("published")
            title = title_elem.text if title_elem is not None else None
            description = desc_elem.text if desc_elem is not None else None
            link = link_elem.text if link_elem is not None else None
            pub_date = date_elem.text if date_elem is not None else None
        else:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            title_elem = item.find("atom:title", ns)
            desc_elem = item.find("atom:summary", ns) or item.find("atom:content", ns)
            link_elem = item.find("atom:link", ns)
            date_elem = item.find("atom:published", ns) or item.find("atom:updated", ns)
            title = title_elem.text if title_elem is not None else None
            description = desc_elem.text if desc_elem is not None else None
            link = link_elem.get("href") if link_elem is not None else None
            pub_date = date_elem.text if date_elem is not None else None

        if not _is_funding_article(title, description):
            continue

        company = _extract_company_name(title, description)
        parsed_date = _parse_rss_date(pub_date)

        articles.append({
            "source": name,
            "title": title,
            "description": description,
            "url": link,
            "published_at": parsed_date.isoformat() if parsed_date else None,
            "company_guess": company,
            "is_funding": True,
        })

    logger.info(f"RSS {name}: {len(articles)} funding articles found")
    return articles


async def scan_all_rss_feeds() -> list[dict[str, Any]]:
    """Fetch all configured RSS feeds and return funding articles."""
    all_articles: list[dict[str, Any]] = []
    for name, url in RSS_FEEDS.items():
        articles = await fetch_rss_feed(name, url)
        all_articles.extend(articles)
    return all_articles


def match_funding_to_company(
    company_name: str,
    articles: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Check if any funding article likely mentions the given company.
    Returns the best match or None.
    """
    cname_lower = company_name.lower()
    cname_words = set(cname_lower.split())

    best_match: dict[str, Any] | None = None
    best_score = 0

    for article in articles:
        guess = article.get("company_guess") or ""
        title = article.get("title") or ""
        text = f"{guess} {title}".lower()

        # Exact match
        if cname_lower in text:
            return article

        # Word overlap score
        text_words = set(text.split())
        overlap = len(cname_words & text_words)
        if overlap > best_score:
            best_score = overlap
            best_match = article

    # Only return if we have strong overlap (at least half the company name words)
    if best_score >= max(1, len(cname_words) // 2):
        return best_match

    return None
