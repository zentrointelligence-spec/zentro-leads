import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { readJsonBody } from "@/lib/read-json-response";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const cookieStore = await cookies();
    const session = cookieStore.get("zentro_session")?.value;
    const body = await req.text();

    const res = await fetch(`${BASE}/api/v1/admin/users/${id}/reset-password`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(session ? { Cookie: `zentro_session=${session}` } : {}),
      },
      body,
      cache: "no-store",
    });

    const parsed = await readJsonBody<unknown>(res);
    if (!parsed.ok) {
      return NextResponse.json(
        { detail: parsed.bodyPreview, success: false },
        { status: res.status || 502 }
      );
    }
    return NextResponse.json(parsed.data, { status: res.status });
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ detail: message, success: false }, { status: 502 });
  }
}
