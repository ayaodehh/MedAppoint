import type { NextRequest } from "next/server";

const API_PROXY_TARGET = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";
const ACCESS_COOKIE = process.env.AUTH_ACCESS_COOKIE_NAME ?? "clinic_access_token";
const REFRESH_COOKIE = process.env.AUTH_REFRESH_COOKIE_NAME ?? "clinic_refresh_token";
const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "content-length",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

function buildUpstreamUrl(path: string[], request: NextRequest) {
  const upstreamUrl = new URL(`/api/${path.join("/")}`, API_PROXY_TARGET);
  request.nextUrl.searchParams.forEach((value, key) => {
    upstreamUrl.searchParams.append(key, value);
  });
  return upstreamUrl;
}

function copyResponseHeaders(source: Headers) {
  const headers = new Headers();
  source.forEach((value, key) => {
    if (key.toLowerCase() === "set-cookie") {
      return;
    }
    if (HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
      return;
    }
    headers.append(key, value);
  });

  const getSetCookie = (source as Headers & { getSetCookie?: () => string[] }).getSetCookie;
  if (typeof getSetCookie === "function") {
    for (const cookie of getSetCookie.call(source)) {
      headers.append("set-cookie", cookie);
    }
  } else {
    const cookie = source.get("set-cookie");
    if (cookie) {
      headers.append("set-cookie", cookie);
    }
  }

  return headers;
}

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const upstreamUrl = buildUpstreamUrl(path, request);
  const requestHeaders = new Headers(request.headers);
  const cookieHeader = request.headers.get("cookie") ?? "";

  requestHeaders.set("x-forwarded-host", request.headers.get("host") ?? "");
  requestHeaders.set("x-forwarded-proto", request.nextUrl.protocol.replace(":", ""));
  requestHeaders.delete("host");
  if (cookieHeader) {
    requestHeaders.set("cookie", cookieHeader);
  }

  const upstreamResponse = await fetch(upstreamUrl, {
    method: request.method,
    headers: requestHeaders,
    body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer(),
    redirect: "manual",
    cache: "no-store",
  });

  const responseHeaders = copyResponseHeaders(upstreamResponse.headers);
  if (upstreamResponse.status === 401) {
    responseHeaders.append("set-cookie", `${ACCESS_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax`);
    responseHeaders.append("set-cookie", `${REFRESH_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax`);
  }

  return new Response(upstreamResponse.body, {
    status: upstreamResponse.status,
    statusText: upstreamResponse.statusText,
    headers: responseHeaders,
  });
}

export const runtime = "nodejs";

export { proxy as DELETE, proxy as GET, proxy as HEAD, proxy as OPTIONS, proxy as PATCH, proxy as POST, proxy as PUT };
