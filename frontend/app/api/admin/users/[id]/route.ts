import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { readJsonBody } from "@/lib/read-json-response";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

async function getSession() {
  const cookieStore = await cookies();
  return cookieStore.get("zentro_session")?.value;
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const session = await getSession();
    const body = await req.text();

    const res = await fetch(`${BASE}/api/v1/admin/users/${id}`, {
      method: "PATCH",
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
        { detail: parsed.bodyPreview || "Invalid response from server" },
        { status: res.status || 502 }
      );
    }
    return NextResponse.json(parsed.data, { status: res.status });
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ detail: message }, { status: 502 });
  }
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const session = await getSession();

    const res = await fetch(`${BASE}/api/v1/admin/users/${id}`, {
      method: "DELETE",
      headers: session ? { Cookie: `zentro_session=${session}` } : {},
      cache: "no-store",
    });

    if (res.status === 204) {
      return new NextResponse(null, { status: 204 });
    }

    const parsed = await readJsonBody<unknown>(res);
    if (parsed.ok) {
      return NextResponse.json(parsed.data, { status: res.status });
    }
    return NextResponse.json({ detail: parsed.bodyPreview }, { status: res.status });
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ detail: message }, { status: 502 });
  }
}
