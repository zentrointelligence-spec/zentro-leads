/**
 * Browser-safe JSON parsing from fetch Response (handles HTML/plain-text errors).
 */

export async function parseJsonResponse<T>(res: Response, fallback: T): Promise<T> {
  const text = await res.text();
  const trimmed = text.trim();
  if (!trimmed) return fallback;
  try {
    return JSON.parse(trimmed) as T;
  } catch {
    return fallback;
  }
}

/** FastAPI-style `{ "detail": string | object }` from a parsed JSON body. */
export function detailFromApiJson(body: unknown): string | null {
  if (body && typeof body === "object" && "detail" in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) {
      return d
        .map((item: unknown) =>
          typeof item === "object" && item && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : JSON.stringify(item)
        )
        .join(", ");
    }
    try {
      return JSON.stringify(d);
    } catch {
      return String(d);
    }
  }
  return null;
}

/**
 * One-shot auth form handler: read body once, show a clear toast on non-JSON / 500 HTML.
 */
export async function readAuthFetchResult(
  res: Response
): Promise<
  | { success: true; body: unknown }
  | { success: false; message: string }
> {
  const text = await res.text();
  const trimmed = text.trim();
  let body: unknown = null;
  if (trimmed) {
    try {
      body = JSON.parse(trimmed) as unknown;
    } catch {
      return {
        success: false,
        message:
          res.status >= 500
            ? `Server error (${res.status}). Ensure the API is running on port 8001, run Alembic migrations, and start Redis — or set DEBUG=true in the backend .env to use in-memory rate limiting without Redis.`
            : `Invalid response (${res.status}).`,
      };
    }
  }

  if (!res.ok) {
    return {
      success: false,
      message:
        detailFromApiJson(body) ??
        (res.status >= 500
          ? `Server error (${res.status}). Check API logs and configuration.`
          : `Request failed (${res.status}).`),
    };
  }

  return { success: true, body };
}
