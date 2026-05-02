"""
Company website scraper — Playwright + heuristics for people, emails, phones, social.
Never raises; returns empty structure on any failure.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import random
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from loguru import logger
from playwright.async_api import async_playwright

from app.config import settings


TITLE_KEYWORDS = [
    "CEO",
    "Chief Executive",
    "CFO",
    "COO",
    "CTO",
    "Director",
    "Manager",
    "Head of",
    "VP",
    "Vice President",
    "President",
    "Founder",
    "Co-Founder",
    "Partner",
    "Principal",
    "Officer",
    "General Manager",
    "MD",
    "Managing Director",
]

TEAM_PATHS = [
    "/about",
    "/team",
    "/people",
    "/about-us",
    "/our-team",
    "/who-we-are",
    "/leadership",
    "/management",
]

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_NAME_CONNECTORS = frozenset({
    "al", "ap", "bin", "binti", "da", "de", "del", "der", "di", "ibn",
    "la", "le", "md", "mohd", "van", "von",
})
_NAME_TOKEN_BLOCKLIST = frozenset({
    "about",
    "advisory",
    "advisor",
    "announcement",
    "announcements",
    "app",
    "article",
    "articles",
    "campaign",
    "campaigns",
    "care",
    "career",
    "careers",
    "charter",
    "claim",
    "claims",
    "component",
    "consent",
    "contact",
    "content",
    "cookie",
    "cookies",
    "customer",
    "doctor",
    "event",
    "events",
    "faq",
    "financial",
    "find",
    "football",
    "foreign",
    "form",
    "glossary",
    "guide",
    "help",
    "human",
    "important",
    "introducing",
    "investment",
    "key",
    "library",
    "locate",
    "menu",
    "news",
    "office",
    "overview",
    "page",
    "partnership",
    "partnerships",
    "payment",
    "personnel",
    "preference",
    "preferences",
    "premium",
    "privacy",
    "product",
    "products",
    "promotion",
    "promotions",
    "public",
    "read",
    "record",
    "recordkeeping",
    "registration",
    "renew",
    "resource",
    "resources",
    "running",
    "specialist",
    "success",
    "support",
    "technical",
    "terms",
    "wellness",
})

# Social / aggregator platforms that should never be scraped as company sites.
_SKIP_BASE_DOMAINS: frozenset[str] = frozenset({
    "facebook.com",
    "fb.com",
    "linkedin.com",
    "lnkd.in",
    "instagram.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "youtube.com",
    "pinterest.com",
    "wa.me",
    "whatsapp.com",
    "t.me",
    "telegram.me",
    "threads.net",
    "snapchat.com",
    "linktr.ee",
    "beacons.ai",
})
PHONE_MY = re.compile(r"\+60[\s\-]?\d{1,2}[\s\-]?\d{3,4}[\s\-]?\d{3,4}")
PHONE_UAE = re.compile(r"\+971[\s\-]?\d[\s\-]?\d{3}[\s\-]?\d{4}")
PHONE_GENERAL = re.compile(r"[\+]?[(]?\d{1,4}[)]?[-\s\.]?\d{6,12}")


_SKIP_DOMAINS = frozenset({
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "youtube.com", "tiktok.com", "wa.link",
    "bit.ly", "linktr.ee", "t.me",
})


def _normalize_url(url: str) -> str | None:
    """Return absolute http(s) URL or None. Skips social/redirect domains."""
    if not url or not isinstance(url, str):
        return None
    u = url.strip()
    if not u.startswith(("http://", "https://")):
        return None
    try:
        host = urlparse(u).netloc.lower().lstrip("www.")
        if any(host == d or host.endswith("." + d) for d in _SKIP_DOMAINS):
            return None
    except Exception:
        pass
    return u


def _same_domain(base: str, target: str) -> bool:
    """Return True if target host is same as base or subdomain."""
    try:
        b = urlparse(base).netloc.lower().lstrip("www.")
        t = urlparse(target).netloc.lower().lstrip("www.")
        return t == b or t.endswith("." + b)
    except Exception:
        return False


def _filter_email(email: str) -> bool:
    """Return False if email should be discarded."""
    e = email.lower()
    if e.endswith("@example.com"):
        return False
    if e.endswith("@domain.com"):
        return False
    if e.startswith("noreply@") or e.startswith("no-reply@"):
        return False
    if "sentry" in e and e.startswith("info@"):
        return False
    if e.startswith("info@sentry"):
        return False
    return True


def _extract_emails(text: str) -> list[str]:
    """Extract deduplicated emails from raw text."""
    found = EMAIL_RE.findall(text or "")
    out: list[str] = []
    for em in found:
        if _filter_email(em):
            if em not in out:
                out.append(em)
    return out


def _extract_phones(text: str) -> list[str]:
    """Extract phone-like strings from text."""
    phones: list[str] = []
    for pattern in (PHONE_MY, PHONE_UAE, PHONE_GENERAL):
        for m in pattern.findall(text or ""):
            if m not in phones:
                phones.append(m)
    return phones[:20]


def _extract_social(soup: BeautifulSoup) -> dict[str, str]:
    """Extract linkedin/facebook/instagram URLs from hrefs."""
    social: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if "linkedin.com" in href and "linkedin" not in social:
            social["linkedin"] = a["href"]
        elif "facebook.com" in href and "facebook" not in social:
            social["facebook"] = a["href"]
        elif "instagram.com" in href and "instagram" not in social:
            social["instagram"] = a["href"]
    return social


def _normalize_person_text(value: str) -> str:
    text = (value or "").replace("\u200b", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _looks_like_real_name(name: str) -> bool:
    cleaned = _normalize_person_text(name)
    if not cleaned or len(cleaned) > 60:
        return False
    if any(ch.isdigit() for ch in cleaned):
        return False
    if any(ch in cleaned for ch in "@/|\\"):
        return False
    words = cleaned.split()
    if len(words) < 2 or len(words) > 5:
        return False

    human_tokens = 0
    for raw_word in words:
        word = raw_word.strip(".,:;()[]{}\"'")
        lower = word.lower()
        if not word:
            return False
        if lower in _NAME_TOKEN_BLOCKLIST:
            return False
        if lower in _NAME_CONNECTORS:
            continue
        if not re.fullmatch(r"[A-Za-z][A-Za-z'\\-]{0,24}", word):
            return False
        if not word[0].isupper():
            return False
        human_tokens += 1

    return human_tokens >= 2


def _infer_seniority(title: str) -> str:
    """Map a title string to coarse seniority bucket."""
    t = (title or "").lower()
    if any(x in t for x in ("ceo", "cfo", "coo", "cto", "chief", "president", "founder")):
        return "c-level"
    if "director" in t or "vp" in t or "vice president" in t:
        return "director"
    if "manager" in t or "head of" in t:
        return "manager"
    return "individual"


def _extract_people_from_soup(soup: BeautifulSoup) -> list[dict[str, str]]:
    """
    Heuristic extraction of people (name + title) from page soup.
    Looks for title keywords then nearby text as name.
    """
    people: list[dict[str, str]] = []
    text_blocks = soup.find_all(["h1", "h2", "h3", "h4", "p", "span", "div", "li"])

    for el in text_blocks:
        raw = el.get_text(" ", strip=True)
        if not raw:
            continue
        for kw in TITLE_KEYWORDS:
            if kw.lower() in raw.lower():
                title = raw
                name = ""
                prev = el.find_previous(["h1", "h2", "h3", "h4", "p", "span"])
                if prev:
                    name = prev.get_text(" ", strip=True)
                if not name or len(name) > 80:
                    parts = raw.split("-", 1)
                    if len(parts) == 2:
                        name, title = parts[0].strip(), parts[1].strip()
                    else:
                        name = raw.split(",")[0].strip()
                if name and len(name) <= 80:
                    people.append({"name": name, "title": title})
                break

    seen: set[str] = set()
    uniq: list[dict[str, str]] = []
    for p in people:
        normalized_name = _normalize_person_text(p["name"])
        if not _looks_like_real_name(normalized_name):
            continue
        p["name"] = normalized_name
        key = normalized_name.lower()
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    return uniq[:20]


async def scrape_company_website(url: str) -> dict[str, Any]:
    """
    Visit company website and extract decision makers + contact info.

    Returns ``{"people": [], "emails": [], "phones": [], "social": {}}``.
    NEVER raises — returns empty dict on any failure.

    Runs the Playwright browser in a thread-pool executor so heavy I/O does
    not block the uvicorn event loop and starve other API requests.
    Silently skips social media / link-aggregator URLs.
    """
    base = _normalize_url(url)
    if not base:
        return {}

    # Guard: never scrape social media platforms masquerading as company websites.
    try:
        host = urlparse(base).netloc.lower().lstrip("www.")
        base_domain = ".".join(host.split(".")[-2:]) if "." in host else host
        if base_domain in _SKIP_BASE_DOMAINS:
            logger.debug(f"Skipping social/aggregator URL: {url}")
            return {}
    except Exception:
        pass

    try:
        ua_str = UserAgent().random
    except Exception:
        ua_str = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    people: list[dict[str, str]] = []
    emails: list[str] = []
    phones: list[str] = []
    social: dict[str, str] = {}
    raw_texts: list[str] = []

    try:
        # Run in a thread pool so Playwright doesn't block the uvicorn event loop.
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            result = await asyncio.wait_for(
                loop.run_in_executor(pool, _scrape_sync, base, ua_str),
                timeout=35.0,
            )
        return result
    except Exception as exc:
        logger.warning(f"Website scrape failed for {url}: {exc}")
        return {}


def _scrape_sync(base: str, ua_str: str) -> dict[str, Any]:
    """Synchronous Playwright scrape — called from a thread pool executor."""
    import asyncio as _asyncio
    return _asyncio.run(_scrape_async(base, ua_str))


async def _scrape_async(base: str, ua_str: str) -> dict[str, Any]:
    """Inner async Playwright logic running in its own event loop (thread)."""
    from app.config import settings as _settings

    people: list[dict[str, str]] = []
    emails: list[str] = []
    phones: list[str] = []
    social: dict[str, str] = {}
    raw_texts: list[str] = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context_kwargs: dict[str, Any] = {
                "user_agent": ua_str,
                "viewport": {"width": 1280, "height": 720},
            }
            if _settings.ROTATING_PROXY_URL:
                context_kwargs["proxy"] = {"server": _settings.ROTATING_PROXY_URL}
            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()

            async def visit(path: str) -> BeautifulSoup | None:
                full = urljoin(base, path)
                if not _same_domain(base, full):
                    return None
                await asyncio.sleep(random.uniform(2.0, 4.0))
                try:
                    resp = await page.goto(full, wait_until="domcontentloaded", timeout=8000)
                    if resp is None or resp.status >= 400:
                        return None
                    html = await page.content()
                    return BeautifulSoup(html, "lxml")
                except Exception as exc:
                    logger.warning(f"Website scrape path failed {full}: {exc}")
                    return None

            # Try team-like paths first
            for path in TEAM_PATHS:
                soup = await visit(path)
                if not soup:
                    continue
                found = _extract_people_from_soup(soup)
                txt = soup.get_text("\n", strip=True)
                raw_texts.append(txt)
                emails.extend(_extract_emails(txt))
                phones.extend(_extract_phones(txt))
                social.update(_extract_social(soup))
                if found:
                    people.extend(found)
                    break

            # Home page fallback
            if not people:
                soup = await visit("/")
                if soup:
                    people.extend(_extract_people_from_soup(soup))
                    txt = soup.get_text("\n", strip=True)
                    raw_texts.append(txt)
                    emails.extend(_extract_emails(txt))
                    phones.extend(_extract_phones(txt))
                    social.update(_extract_social(soup))

            # Contact pages for emails/phones
            for cpath in ("/contact", "/contact-us"):
                soup = await visit(cpath)
                if soup:
                    txt = soup.get_text("\n", strip=True)
                    raw_texts.append(txt)
                    emails.extend(_extract_emails(txt))
                    phones.extend(_extract_phones(txt))
                    social.update(_extract_social(soup))

            await context.close()
            await browser.close()

        # Dedupe emails/phones
        emails = list(dict.fromkeys(emails))[:50]
        phones = list(dict.fromkeys(phones))[:50]

        # Enrich seniority on people (not returned separately — caller uses title)
        for p in people:
            p.setdefault("title", "")
            _ = _infer_seniority(p.get("title", ""))

        full_raw = "\n".join(raw_texts)
        return {
            "people": people,
            "emails": emails,
            "phones": phones,
            "social": social,
            "raw_text": full_raw[:20000],  # Cap at 20K chars
        }
    except Exception as exc:
        logger.warning(f"Website scrape failed for {base}: {exc}")
        return {}
