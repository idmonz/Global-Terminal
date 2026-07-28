import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const MAX_BODY_BYTES = 16_384;
const MAX_BACKUP_BODY_BYTES = 550_000;

function runtimeBaseUrl(): string {
  return (process.env.GLOBAL_TERMINAL_API_BASE_URL?.trim() || "http://127.0.0.1:8000")
    .replace(/\/+$/, "");
}

function allowedPath(parts: string[]): string | null {
  const joined = parts.map((part) => decodeURIComponent(part)).join("/");
  if (
    !joined ||
    joined.length > 180 ||
    joined.includes("..") ||
    joined.includes("\\")
  ) return null;
  if (["session", "hosted-session", "local-session", "signout", "export"].includes(joined)) {
    return joined;
  }
  if ([
    "continuity",
    "continuity/replay",
    "continuity/resolve",
    "continuity/export",
    "continuity/import",
  ].includes(joined)) {
    return joined;
  }
  if (/^preferences\/[a-z][a-z0-9-]{0,63}$/.test(joined)) return joined;
  if ([
    "research-desk",
    "research-desk/export",
    "research-desk/imports",
    "research-desk/imports/preview",
    "research-desk/sync",
    "research-desk/sync/preview",
    "research-desk/sync/queue",
    "research-desk/sync/replay",
  ].includes(joined)) {
    return joined;
  }
  if ([
    "attention-desk",
    "attention-desk/policy",
    "attention-desk/checkpoint",
    "attention-desk/audit",
    "observation-runs",
    "alert-manager",
    "alert-manager/audit",
    "alert-manager/evaluations",
    "alert-manager/export",
    "alert-manager/rules",
    "alert-manager/worker/run-once",
    "alert-manager/scheduler",
    "alert-manager/scheduler/audit",
    "alert-manager/scheduler/schedules",
  ].includes(joined)) {
    return joined;
  }
  if (/^attention-desk\/items\/[0-9a-f]{64}$/.test(joined)) return joined;
  if (/^observation-runs\/[a-z0-9_]{3,80}$/.test(joined)) return joined;
  if (/^observation-runs\/[a-z0-9_]{3,80}\/snapshots$/.test(joined)) return joined;
  if (/^observation-runs\/[a-z0-9_]{3,80}\/cancel$/.test(joined)) return joined;
  if (/^alert-manager\/rules\/[a-z0-9_]{3,80}$/.test(joined)) return joined;
  if (/^alert-manager\/triggers\/[a-z0-9_]{3,80}$/.test(joined)) return joined;
  if (/^alert-manager\/scheduler\/schedules\/[a-z0-9_]{3,80}$/.test(joined)) return joined;
  if (/^research-desk\/sync\/queue\/[a-z0-9_]{3,80}$/.test(joined)) return joined;
  if (/^research-desk\/watchlists\/[a-z0-9_]{3,64}(?:\/(?:rule|inbox))?$/.test(joined)) return joined;
  if (/^research-desk\/inbox\/[a-z0-9_]{3,64}$/.test(joined)) return joined;
  return null;
}

function sameOrigin(request: NextRequest): boolean {
  const origin = request.headers.get("origin");
  const forwardedHost = request.headers.get("x-forwarded-host")?.split(",", 1)[0]?.trim();
  const host = forwardedHost || request.headers.get("host")?.trim();
  const forwardedProtocol = request.headers.get("x-forwarded-proto")?.split(",", 1)[0]?.trim();
  const protocol = forwardedProtocol || request.nextUrl.protocol.replace(":", "");
  if (!origin || !host || !["http", "https"].includes(protocol)) return false;
  try {
    const candidate = new URL(origin);
    return (
      !candidate.username &&
      !candidate.password &&
      candidate.host.toLowerCase() === host.toLowerCase() &&
      candidate.protocol === `${protocol}:`
    );
  } catch {
    return false;
  }
}

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE",
) {
  const path = allowedPath((await context.params).path);
  if (!path) {
    return NextResponse.json(
      { error: "account-route-not-allowed" },
      { status: 404, headers: { "Cache-Control": "no-store" } },
    );
  }
  if (method !== "GET" && !sameOrigin(request)) {
    return NextResponse.json(
      { error: "account-same-origin-required" },
      { status: 403, headers: { "Cache-Control": "no-store" } },
    );
  }
  const rawBody = method === "GET" || method === "DELETE" ? "" : await request.text();
  const bodyLimit = path === "continuity/import" ? MAX_BACKUP_BODY_BYTES : MAX_BODY_BYTES;
  if (new TextEncoder().encode(rawBody).byteLength > bodyLimit) {
    return NextResponse.json(
      { error: "account-request-too-large" },
      { status: 413, headers: { "Cache-Control": "no-store" } },
    );
  }
  if (rawBody) {
    try {
      const parsed = JSON.parse(rawBody);
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error("invalid-body");
      }
    } catch {
      return NextResponse.json(
        { error: "account-request-invalid" },
        { status: 422, headers: { "Cache-Control": "no-store" } },
      );
    }
  }
  const base = runtimeBaseUrl();
  const upstream = new URL(`${base}/api/account/${path}`);
  request.nextUrl.searchParams.forEach((value, key) => upstream.searchParams.append(key, value));
  try {
    const response = await fetch(upstream, {
      method,
      cache: "no-store",
      headers: {
        Accept: "application/json",
        Origin: new URL(base).origin,
        ...(rawBody ? { "Content-Type": "application/json" } : {}),
        ...(request.headers.get("cookie") ? { Cookie: request.headers.get("cookie") as string } : {}),
        ...(request.headers.get("x-csrf-token")
          ? { "X-CSRF-Token": request.headers.get("x-csrf-token") as string }
          : {}),
      },
      body: rawBody || undefined,
      signal: AbortSignal.timeout(10_000),
    });
    const headers = new Headers({
      "Cache-Control": "no-store",
      "Content-Type": response.headers.get("content-type") || "application/json",
      "X-Global-Terminal-Account": "same-origin-proxy",
      "X-Content-Type-Options": "nosniff",
    });
    const responseHeaders = response.headers as Headers & { getSetCookie?: () => string[] };
    const cookies = responseHeaders.getSetCookie?.() || [];
    if (cookies.length) cookies.forEach((cookie) => headers.append("Set-Cookie", cookie));
    else if (response.headers.get("set-cookie")) {
      headers.append("Set-Cookie", response.headers.get("set-cookie") as string);
    }
    return new NextResponse(await response.arrayBuffer(), {
      status: response.status,
      headers,
    });
  } catch {
    return NextResponse.json(
      {
        error: "account-api-offline",
        source_status: "unavailable",
        data_gap: "Account runtime did not respond; local workspace remains available.",
      },
      {
        status: 503,
        headers: {
          "Cache-Control": "no-store",
          "X-Global-Terminal-Account": "same-origin-proxy",
        },
      },
    );
  }
}

export function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, context, "GET");
}

export function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, context, "POST");
}

export function PUT(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, context, "PUT");
}

export function PATCH(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, context, "PATCH");
}

export function DELETE(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, context, "DELETE");
}
