"""Google Sheets export client for Zentro Leads.

Uses a GCP service account to create a new spreadsheet, write lead data,
format the header row, auto-resize columns, and share the sheet with the
requesting user.

Raises ValueError if GOOGLE_SERVICE_ACCOUNT_JSON is not configured so
callers can return a friendly 422 to the frontend.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from loguru import logger

from app.config import settings

# ── Column definition ─────────────────────────────────────────────────────────

HEADERS = [
    "Company",
    "Contact Name",
    "Role",
    "Email",
    "Phone",
    "Lead Score",
    "Tier",
    "ICP Match %",
    "Industry",
    "Location",
    "Intent Signals",
    "Recommended Product",
    "Status",
    "Website",
    "Created At",
]


def _lead_to_row(lead: dict[str, Any]) -> list[str | int | float]:
    """Convert a lead dict (from LeadResponse.model_dump()) to a sheet row."""
    person  = lead.get("person")  or {}
    company = lead.get("company") or {}

    city    = company.get("city")    or ""
    country = company.get("country") or ""
    location = f"{city}, {country}".strip(", ") or ""

    signals = lead.get("intent_signals") or []
    sig_str = ", ".join(str(s) for s in signals) if signals else ""

    created = lead.get("created_at") or ""
    if created and hasattr(created, "isoformat"):
        created = created.isoformat()
    elif created:
        created = str(created)[:19]  # trim microseconds

    return [
        company.get("name")              or "",
        person.get("full_name")          or "",
        person.get("job_title")          or "",
        person.get("email")              or "",
        person.get("phone")              or "",
        lead.get("lead_score")           or 0,
        (lead.get("lead_tier") or "").upper(),
        lead.get("icp_match_score")      or 0,
        company.get("industry")          or "",
        location,
        sig_str,
        lead.get("recommended_product")  or "",
        lead.get("status")               or "",
        company.get("website")           or "",
        created,
    ]


def _build_service():
    """
    Build an authenticated Google API resource (sync, called in thread).

    Returns a tuple (sheets_service, drive_service).
    Raises ValueError if credentials are not configured.
    """
    if not settings.GOOGLE_SERVICE_ACCOUNT_JSON:
        raise ValueError(
            "Google Sheets not configured — "
            "set GOOGLE_SERVICE_ACCOUNT_JSON in your environment."
        )

    # Import here so the module loads without google-api packages installed
    from google.oauth2 import service_account  # type: ignore[import]
    from googleapiclient.discovery import build  # type: ignore[import]

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    sa_info = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
    creds   = service_account.Credentials.from_service_account_info(
        sa_info, scopes=scopes
    )

    sheets = build("sheets", "v4",  credentials=creds, cache_discovery=False)
    drive  = build("drive",  "v3",  credentials=creds, cache_discovery=False)
    return sheets, drive


def _export_sync(
    leads: list[dict[str, Any]],
    sheet_title: str,
    user_email: str,
) -> str:
    """
    Synchronous core of the export — runs in a thread pool via asyncio.to_thread.

    Steps:
      1. Authenticate with service account
      2. Create spreadsheet
      3. Share with user_email (writer)
      4. Write header + data rows
      5. Bold + freeze header row
      6. Auto-resize all columns
      7. Return spreadsheet URL
    """
    sheets_svc, drive_svc = _build_service()

    # ── 1. Create spreadsheet ─────────────────────────────────────────────────
    spreadsheet = sheets_svc.spreadsheets().create(body={
        "properties": {"title": sheet_title},
        "sheets": [{
            "properties": {
                "title":     "Leads",
                "gridProperties": {"frozenRowCount": 1},
            }
        }],
    }).execute()

    spreadsheet_id  = spreadsheet["spreadsheetId"]
    sheet_id        = spreadsheet["sheets"][0]["properties"]["sheetId"]
    spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

    logger.debug(f"Sheets: created spreadsheet {spreadsheet_id}")

    # ── 2. Share with requesting user ─────────────────────────────────────────
    try:
        drive_svc.permissions().create(
            fileId=spreadsheet_id,
            body={"type": "user", "role": "writer", "emailAddress": user_email},
            sendNotificationEmail=False,
        ).execute()
        logger.debug(f"Sheets: shared {spreadsheet_id} with {user_email}")
    except Exception as exc:
        logger.warning(f"Sheets: could not share with {user_email}: {exc}")

    # ── 3. Write header + data rows ───────────────────────────────────────────
    rows: list[list[Any]] = [HEADERS] + [_lead_to_row(lead) for lead in leads]

    sheets_svc.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="Leads!A1",
        valueInputOption="RAW",
        body={"values": rows},
    ).execute()

    # ── 4. Format header row (bold, frozen, background colour) ────────────────
    requests: list[dict[str, Any]] = [
        # Bold header
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat":        {"bold": True},
                        "backgroundColor":   {"red": 0.2, "green": 0.6, "blue": 0.4},
                        "horizontalAlignment": "CENTER",
                    }
                },
                "fields": "userEnteredFormat(textFormat,backgroundColor,horizontalAlignment)",
            }
        },
        # Auto-resize all columns
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId":   sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex":   len(HEADERS),
                }
            }
        },
    ]

    sheets_svc.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()

    logger.info(f"Sheets: exported {len(leads)} leads → {spreadsheet_url}")
    return spreadsheet_url


async def export_leads_to_sheets(
    leads: list[dict[str, Any]],
    sheet_title: str,
    user_email: str,
) -> str:
    """
    Export a list of lead dicts to a new Google Sheet and return the URL.

    Runs the synchronous Google API calls in a thread pool so the FastAPI
    event loop is never blocked.

    Args:
        leads:       List of dicts from LeadResponse.model_dump().
        sheet_title: Title for the new spreadsheet.
        user_email:  Email of the user — the sheet will be shared with them.

    Returns:
        Full URL to the new Google Spreadsheet.

    Raises:
        ValueError: If GOOGLE_SERVICE_ACCOUNT_JSON is not configured.
        Exception:  Any Google API error is re-raised after logging.
    """
    if not leads:
        raise ValueError("No leads to export.")

    try:
        url = await asyncio.to_thread(_export_sync, leads, sheet_title, user_email)
        return url
    except ValueError:
        raise
    except Exception as exc:
        logger.error(f"Sheets: export failed: {exc}")
        raise
