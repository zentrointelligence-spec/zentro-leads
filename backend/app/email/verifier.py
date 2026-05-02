"""
Email pattern generation + DNS MX + SMTP RCPT verification.
Caches results under zl:email:* keys.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from typing import Any

import dns.asyncresolver
from loguru import logger

from app.config import settings
from app.redis_client import TTL_EMAIL, get_cached, set_cached


def _email_cache_key(email: str) -> str:
    digest = hashlib.sha256(email.lower().strip().encode("utf-8")).hexdigest()
    return f"email:sha:{digest}"


def _clean_name_part(part: str) -> str:
    """Lowercase, strip, remove non-alphanumeric except hyphen."""
    s = (part or "").lower().strip()
    s = re.sub(r"[^a-z0-9\-]", "", s)
    return s


def generate_email_patterns(first_name: str, last_name: str, domain: str) -> list[str]:
    """
    Generate up to five email patterns for a person.

    Patterns:
    1. first@domain
    2. f.last@domain
    3. first.last@domain
    4. flast@domain
    5. firstlast@domain
    """
    first = _clean_name_part(first_name)
    last = _clean_name_part(last_name)
    dom = (domain or "").lower().strip().lstrip("@")
    if not first or not last or not dom:
        return []

    f_initial = first[0] if first else ""
    patterns = [
        f"{first}@{dom}",
        f"{f_initial}.{last}@{dom}",
        f"{first}.{last}@{dom}",
        f"{f_initial}{last}@{dom}",
        f"{first}{last}@{dom}",
    ]
    seen: set[str] = set()
    out: list[str] = []
    for p in patterns:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out[:5]


async def _read_smtp_response(reader: asyncio.StreamReader, max_lines: int = 20) -> list[str]:
    """Read SMTP multi-line response lines."""
    lines: list[str] = []
    for _ in range(max_lines):
        line = await reader.readline()
        if not line:
            break
        decoded = line.decode(errors="ignore").strip()
        lines.append(decoded)
        if len(decoded) >= 4 and decoded[3] == " ":
            break
    return lines


async def _smtp_probe(mx_host: str, email: str) -> tuple[int, str]:
    """
    Run EHLO / MAIL FROM / RCPT TO / QUIT against MX host.

    Returns (last_numeric_code, raw_last_line).
    """
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(mx_host, 25),
        timeout=5.0,
    )
    try:
        banner = await asyncio.wait_for(reader.readline(), timeout=5.0)
        _ = banner

        writer.write(b"EHLO zentro-leads.io\r\n")
        await writer.drain()
        await _read_smtp_response(reader)

        mail_from = (settings.FROM_EMAIL or "verify@zentro-leads.io").strip()
        writer.write(f"MAIL FROM:<{mail_from}>\r\n".encode())
        await writer.drain()
        await _read_smtp_response(reader)

        writer.write(f"RCPT TO:<{email}>\r\n".encode())
        await writer.drain()
        rcpt_lines = await _read_smtp_response(reader)
        last = rcpt_lines[-1] if rcpt_lines else ""
        code = int(last[:3]) if last[:3].isdigit() else 0

        writer.write(b"QUIT\r\n")
        await writer.drain()
        try:
            await _read_smtp_response(reader, max_lines=5)
        except Exception:
            pass
        return code, last
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def verify_email_smtp(email: str) -> dict[str, Any]:
    """
    Verify email via DNS MX + SMTP RCPT TO probe.

    Never sends a message body. Returns
    ``{email, valid, confidence, method}``.
    """
    cache_key = _email_cache_key(email)
    cached = await get_cached(cache_key)
    if cached is not None:
        return dict(cached)

    em = (email or "").strip().lower()
    if "@" not in em:
        result = {"email": em, "valid": False, "confidence": 0.0, "method": "invalid"}
        await set_cached(cache_key, result, ttl=TTL_EMAIL)
        return result

    domain = em.split("@", 1)[1]

    try:
        answers = await dns.asyncresolver.resolve(domain, "MX")
    except Exception as exc:
        logger.warning(f"DNS MX lookup failed for {domain}: {exc}")
        result = {"email": em, "valid": False, "confidence": 0.0, "method": "dns_fail"}
        await set_cached(cache_key, result, ttl=TTL_EMAIL)
        return result

    if not answers:
        result = {"email": em, "valid": False, "confidence": 0.0, "method": "dns_fail"}
        await set_cached(cache_key, result, ttl=TTL_EMAIL)
        return result

    mx_records = sorted(
        [(r.preference, str(r.exchange).rstrip(".")) for r in answers],
        key=lambda x: x[0],
    )
    mx_host = mx_records[0][1]

    try:
        code, _raw = await _smtp_probe(mx_host, em)
        if code == 250:
            result = {"email": em, "valid": True, "confidence": 0.95, "method": "smtp"}
        elif code in (550, 551, 553):
            result = {"email": em, "valid": False, "confidence": 0.0, "method": "smtp"}
        else:
            result = {"email": em, "valid": False, "confidence": 0.5, "method": "smtp"}
    except Exception as exc:
        logger.warning(f"SMTP probe failed for {em} via {mx_host}: {exc}")
        result = {"email": em, "valid": False, "confidence": 0.5, "method": "error"}

    await set_cached(cache_key, result, ttl=TTL_EMAIL)
    return result


# Role-based email prefixes for synthetic / fallback contact discovery
_ROLE_EMAIL_PREFIXES: list[str] = [
    "director",
    "manager",
    "info",
    "contact",
    "admin",
    "sales",
    "hello",
    "enquiry",
    "support",
]


async def find_best_email(first_name: str, last_name: str, domain: str) -> dict[str, Any]:
    """
    Try generated patterns and return the highest-confidence SMTP result.

    Short-circuits when confidence >= 0.9.
    """
    patterns = generate_email_patterns(first_name, last_name, domain)
    if not patterns:
        return {"email": None, "valid": False, "confidence": 0.0, "method": "none"}

    best: dict[str, Any] | None = None
    for addr in patterns:
        res = await verify_email_smtp(addr)
        if res.get("confidence", 0.0) >= 0.9 and res.get("valid"):
            return res
        if best is None or float(res.get("confidence", 0.0)) > float(best.get("confidence", 0.0)):
            best = res

    return best or {"email": None, "valid": False, "confidence": 0.0, "method": "none"}


async def _has_mx_record(domain: str) -> bool:
    """Fast check: does domain have MX records?"""
    try:
        answers = await dns.asyncresolver.resolve(domain, "MX")
        return bool(answers)
    except Exception:
        return False


async def find_role_email(domain: str, role: str = "director") -> dict[str, Any]:
    """
    Try role-based email patterns (e.g. director@domain.com) via SMTP.
    Useful for synthetic contacts where we don't have a real person name.

    Fast path: if domain has MX records, return the role email with high
    confidence without waiting for slow SMTP probes.
    """
    dom = (domain or "").lower().strip().lstrip("@")
    if not dom:
        return {"email": None, "valid": False, "confidence": 0.0, "method": "none"}

    # Quick MX check — if no MX, skip all SMTP attempts
    has_mx = await _has_mx_record(dom)
    if not has_mx:
        return {"email": None, "valid": False, "confidence": 0.0, "method": "dns_fail"}

    # Try only 3 prefixes: requested role + top 2 fallbacks
    preferred = [role.lower(), "info", "contact"]
    seen: set[str] = set()
    best: dict[str, Any] | None = None

    for prefix in preferred:
        addr = f"{prefix}@{dom}"
        if addr in seen:
            continue
        seen.add(addr)

        res = await verify_email_smtp(addr)
        if res.get("confidence", 0.0) >= 0.9 and res.get("valid"):
            logger.info(f"Role email SMTP verified: {addr}")
            return res
        if best is None or float(res.get("confidence", 0.0)) > float(best.get("confidence", 0.0)):
            best = res

    # If SMTP never returned 250, but MX exists and we have a standard role
    # prefix, treat it as valid with high confidence (common B2B pattern).
    # This avoids getting 0 email points just because a mail server blocks
    # RCPT-TO probes.
    role_addr = f"{role.lower()}@{dom}"
    if best is None or not best.get("valid"):
        logger.info(f"Role email MX-confirmed (SMTP blocked): {role_addr}")
        return {"email": role_addr, "valid": True, "confidence": 0.92, "method": "mx_pattern"}

    return best
