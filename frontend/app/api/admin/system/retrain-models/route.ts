import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { readJsonBody } from "@/lib/read-json-response";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export async function POST() {
  try {
    const cookieStore = await cookies();
    const session = cookieStore.get("zentro_session")?.value;

    const res = await fetch(`${BASE}/api/v1/admin/system/retrain-models`, {
      method: "POST",
      headers: session ? { Cookie: `zentro_session=${session}` } : {},
      cache: "no-store",
    });

    const parsed = await readJsonBody<unknown>(res);
    if (!parsed.ok) {
      return NextResponse.json(
        { status: "error", message: parsed.bodyPreview },
        { status: res.status || 502 }
      );
    }
    return NextResponse.json(parsed.data, { status: res.status });
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ status: "error", message }, { status: 502 });
  }
}
