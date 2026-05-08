import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { readJsonBody } from "@/lib/read-json-response";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export async function GET() {
  try {
    const cookieStore = await cookies();
    const session = cookieStore.get("zentro_session")?.value;

    const res = await fetch(`${BASE}/api/v1/admin/activity`, {
      headers: session ? { Cookie: `zentro_session=${session}` } : {},
      cache: "no-store",
    });

    const parsed = await readJsonBody<unknown>(res);

    if (!res.ok) {
      return NextResponse.json([], { status: 200 });
    }

    if (!parsed.ok || !Array.isArray(parsed.data)) {
      return NextResponse.json([], { status: 200 });
    }

    return NextResponse.json(parsed.data);
  } catch {
    return NextResponse.json([], { status: 200 });
  }
}
