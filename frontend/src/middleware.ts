import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

const ACCESS_COOKIE = process.env.AUTH_ACCESS_COOKIE_NAME ?? "clinic_access_token";
const PATIENT_PROTECTED = ["/dashboard", "/book", "/appointments"];
const STAFF_PROTECTED = ["/staff/appointments", "/staff/schedule", "/staff/audit"];

type JwtPayload = {
  exp?: number;
  role?: string;
};

function decodePayload(token: string): JwtPayload | null {
  const parts = token.split(".");
  if (parts.length < 2) {
    return null;
  }

  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
    const decoded = atob(padded);
    return JSON.parse(decoded) as JwtPayload;
  } catch {
    return null;
  }
}

function isProtectedPath(pathname: string, patterns: string[]) {
  return patterns.some((pattern) => pathname === pattern || pathname.startsWith(`${pattern}/`));
}

function isTokenUsable(token: string | undefined) {
  if (!token) {
    return false;
  }

  const payload = decodePayload(token);
  if (!payload) {
    return false;
  }

  if (typeof payload.exp === "number") {
    const now = Math.floor(Date.now() / 1000);
    if (payload.exp <= now) {
      return false;
    }
  }

  return true;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const host = request.headers.get("host") ?? "";

  if (process.env.NODE_ENV !== "production" && host.startsWith("127.0.0.1:3000")) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.hostname = "localhost";
    return NextResponse.redirect(redirectUrl);
  }

  const accessToken = request.cookies.get(ACCESS_COOKIE)?.value;
  const tokenIsUsable = isTokenUsable(accessToken);
  const payload = tokenIsUsable && accessToken ? decodePayload(accessToken) : null;
  const role = payload?.role;

  if (isProtectedPath(pathname, PATIENT_PROTECTED) && !tokenIsUsable) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (isProtectedPath(pathname, STAFF_PROTECTED)) {
    if (!tokenIsUsable) {
      return NextResponse.redirect(new URL("/staff/login", request.url));
    }

    if (!role || role === "patient") {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
  }

  if (pathname === "/login" && tokenIsUsable && role === "patient") {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  if (pathname === "/staff/login" && tokenIsUsable && role && role !== "patient") {
    return NextResponse.redirect(new URL("/staff/appointments", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
