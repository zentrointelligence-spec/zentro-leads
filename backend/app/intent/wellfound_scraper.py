"""
Wellfound (formerly AngelList) job scraper.
Extracts open roles, posting dates, and job titles per company.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.config import settings

WELLFOUND_BASE = "https://wellfound.com"
SEARCH_URL = f"{{WELLFOUND_BASE}}/company/{{slug}}/jobs"

# Default headers to look like a real browser
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
}


def _company_slug(name: str) -> str:
    """Convert company name to Wellfound slug guess."""
    return (
        name.lower()
        .replace(" & ", "-and-")
        .replace("+", "plus")
        .replace(".", "")
        .replace(",", "")
        .replace("'", "")
        .replace("  ", " ")
        .strip()
        .replace(" ", "-")
    )


def _extract_jobs_from_html(html: str) -> list[dict[str, Any]]:
    """Parse Wellfound job listings from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[dict[str, Any]] = []

    # Wellfound job cards typically have data-test="job-listing" or similar
    # The structure changes, so we use multiple selectors
    selectors = [
        '[data-test="job-listing"]',
        '.job-listing',
        '.styles_jobListing__',
        '[class*="jobListing"]',
        '[class*="JobListing"]',
    ]

    cards = []
    for sel in selectors:
        cards = soup.select(sel)
        if cards:
            break

    # Fallback: look for links containing "/jobs/"
    if not cards:
        for link in soup.find_all("a", href=True):
            if "/jobs/" in link["href"]:
                cards.append(link.find_parent("div", class_=True) or link)

    for card in cards[:20]:  # Limit to first 20 jobs
        title_elem = (
            card.select_one('[data-test="job-title"]')
            or card.select_one("h3")
            or card.select_one("h2")
            or card.select_one("a")
        )
        title = title_elem.get_text(strip=True) if title_elem else None

        if not title or len(title) < 3:
            continue

        # Try to find location
        loc_elem = (
            card.select_one('[data-test="job-location"]')
            or card.select_one("[class*='location']")
        )
        location = loc_elem.get_text(strip=True) if loc_elem else None

        # Try to find posting date
        date_elem = card.select_one("time") or card.select_one("[datetime]")
        posted_at = date_elem.get("datetime") if date_elem else None

        jobs.append({
            "title": title,
            "location": location,
            "posted_at": posted_at,
            "source": "wellfound",
        })

    return jobs


async def scrape_wellfound_jobs(company_name: str) -> list[dict[str, Any]]:
    """
    Scrape Wellfound job listings for a company.
    Returns list of job dicts or empty list on any failure.
    """
    slug = _company_slug(company_name)
    url = f"{WELLFOUND_BASE}/company/{slug}/jobs"

    try:
        async with httpx.AsyncClient(
            headers=HEADERS,
            timeout=15.0,
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            if resp.status_code == 404:
                logger.debug(f"Wellfound page not found for {company_name} ({slug})")
                return []
            resp.raise_for_status()
            html = resp.text
    except Exception as exc:
        logger.warning(f"Wellfound scrape failed for {company_name}: {exc}")
        return []

    jobs = _extract_jobs_from_html(html)
    logger.info(f"Wellfound: found {len(jobs)} jobs for {company_name}")
    return jobs


async def get_hiring_signal(company_name: str) -> dict[str, Any]:
    """
    High-level helper: return a hiring signal dict for a company.
    """
    jobs = await scrape_wellfound_jobs(company_name)
    if not jobs:
        return {"is_hiring": False, "job_count": 0, "open_roles": []}

    return {
        "is_hiring": True,
        "job_count": len(jobs),
        "open_roles": [j["title"] for j in jobs[:10]],
        "source": "wellfound",
        "last_checked": "now",
    }
