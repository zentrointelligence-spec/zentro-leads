import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { readJsonBody } from "@/lib/read-json-response";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export async function GET() {
  try {
    const cookieStore = await cookies();
    const session = cookieStore.get("zentro_session")?.value;

    const res = await fetch(`${BASE}/api/v1/admin/system/health`, {
      headers: session ? { Cookie: `zentro_session=${session}` } : {},
      cache: "no-store",
    });

    const parsed = await readJsonBody<unknown>(res);

    if (!res.ok) {
      if (parsed.ok) {
        return NextResponse.json(parsed.data, { status: res.status });
      }
      return NextResponse.json(
        { error: "upstream_failed", message: parsed.bodyPreview },
        { status: res.status }
      );
    }

    if (!parsed.ok) {
      return NextResponse.json(
        { error: "invalid_json", message: parsed.bodyPreview },
        { status: 502 }
      );
    }

    return NextResponse.json(parsed.data);
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: "proxy_failed", message }, { status: 502 });
  }
}
