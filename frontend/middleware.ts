/**
 * Route protection for Zentro Leads frontend
 * NOT middleware.ts — Next.js 16 convention used in ZIMS
 *
 * Protected routes: /dashboard/*
 * Auth routes: /login, /register
 */

import { NextRequest, NextResponse } from "next/server";

const PROTECTED = ["/dashboard"];
const AUTH_ROUTES = ["/login", "/register"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const session = request.cookies.get("zentro_session")?.value;

  const isProtected = PROTECTED.some((p) => pathname.startsWith(p));
  const isAuthRoute = AUTH_ROUTES.some((p) => pathname.startsWith(p));

  // Not logged in → trying to access protected route
  if (isProtected && !session) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Already logged in → trying to access auth routes
  if (isAuthRoute && session) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/login",
    "/register",
  ],
};
