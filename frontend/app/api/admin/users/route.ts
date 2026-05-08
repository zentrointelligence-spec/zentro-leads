import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { readJsonBody } from "@/lib/read-json-response";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export async function GET(req: NextRequest) {
  try {
    const cookieStore = await cookies();
    const session = cookieStore.get("zentro_session")?.value;
    const qs = req.nextUrl.searchParams.toString();

    const res = await fetch(`${BASE}/api/v1/admin/users${qs ? `?${qs}` : ""}`, {
      headers: session ? { Cookie: `zentro_session=${session}` } : {},
      cache: "no-store",
    });

    const parsed = await readJsonBody<unknown>(res);

    if (!res.ok) {
      if (parsed.ok) {
        return NextResponse.json(parsed.data, { status: res.status });
      }
      return NextResponse.json({ items: [], total: 0 }, { status: 200 });
    }

    if (!parsed.ok) {
      return NextResponse.json({ items: [], total: 0 }, { status: 200 });
    }

    return NextResponse.json(parsed.data);
  } catch {
    return NextResponse.json({ items: [], total: 0 }, { status: 200 });
  }
}
