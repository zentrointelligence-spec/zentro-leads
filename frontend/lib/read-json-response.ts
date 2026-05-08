/**
 * Safely parse a fetch Response body as JSON.
 * Backend and proxies sometimes return plain text ("Internal Server Error")
 * or HTML; Response.json() throws in those cases.
 */

export async function readJsonBody<T>(res: Response): Promise<{ ok: true; data: T } | { ok: false; bodyPreview: string }> {
  const text = await res.text();
  const trimmed = text.trim();
  if (!trimmed) {
    return { ok: false, bodyPreview: "(empty body)" };
  }
  try {
    return { ok: true, data: JSON.parse(trimmed) as T };
  } catch {
    return { ok: false, bodyPreview: trimmed.slice(0, 240) };
  }
}

export function detailFromUnknownJson(body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    try {
      return JSON.stringify(d);
    } catch {
      return String(d);
    }
  }
  return "";
}
