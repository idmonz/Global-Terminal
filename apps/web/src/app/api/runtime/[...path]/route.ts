import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export const ALLOWED_RUNTIME_PREFIXES = [
  "api/symbol-workstation/",
  "api/analyst-workspace/",
  "api/research-operations/jobs/",
  "api/runtime-health",
] as const;

function runtimeBaseUrl(): string {
  return (process.env.GLOBAL_TERMINAL_API_BASE_URL?.trim() || "http://127.0.0.1:8000")
    .replace(/\/+$/, "");
}

function allowedPath(parts: string[]): string | null {
  const joined = parts.map((part) => decodeURIComponent(part)).join("/");
  if (
    !joined
    || joined.length > 320
    || joined.includes("..")
    || joined.includes("\\")
    || !ALLOWED_RUNTIME_PREFIXES.some((prefix) => joined.startsWith(prefix))
  ) {
    return null;
  }
  return joined;
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const path = allowedPath((await context.params).path);
  if (!path) {
    return NextResponse.json(
      { error: "runtime-route-not-allowed" },
      { status: 404, headers: { "Cache-Control": "no-store" } },
    );
  }

  const upstream = new URL(`${runtimeBaseUrl()}/${path}`);
  request.nextUrl.searchParams.forEach((value, key) => {
    upstream.searchParams.append(key, value);
  });

  try {
    const response = await fetch(upstream, {
      cache: "no-store",
      headers: {
        Accept: "application/json",
        ...(request.headers.get("if-none-match")
          ? { "If-None-Match": request.headers.get("if-none-match") as string }
          : {}),
      },
      signal: AbortSignal.timeout(15_000),
    });
    const body = response.status === 304 ? null : await response.arrayBuffer();
    const headers = new Headers({
      "Cache-Control": response.headers.get("cache-control") || "private, max-age=30",
      "Content-Type": response.headers.get("content-type") || "application/json",
      "X-Global-Terminal-Runtime": "same-origin-proxy",
    });
    const etag = response.headers.get("etag");
    if (etag) headers.set("ETag", etag);
    return new NextResponse(body, { status: response.status, headers });
  } catch {
    return NextResponse.json(
      {
        error: "runtime-api-offline",
        source_status: "unavailable",
        data_gap: "The configured local runtime API did not respond.",
      },
      {
        status: 503,
        headers: {
          "Cache-Control": "no-store",
          "X-Global-Terminal-Runtime": "same-origin-proxy",
        },
      },
    );
  }
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const path = allowedPath((await context.params).path);
  if (
    !path
    || !/^api\/analyst-workspace\/[A-Z0-9=._-]{1,24}\/refresh$/.test(path)
  ) {
    return NextResponse.json(
      { error: "runtime-mutation-not-allowed" },
      { status: 404, headers: { "Cache-Control": "no-store" } },
    );
  }
  const rawBody = await request.text();
  if (rawBody.length > 16_384) {
    return NextResponse.json(
      { error: "runtime-request-too-large" },
      { status: 413, headers: { "Cache-Control": "no-store" } },
    );
  }
  try {
    const parsed = rawBody ? JSON.parse(rawBody) : {};
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("invalid-body");
    }
  } catch {
    return NextResponse.json(
      { error: "runtime-request-invalid" },
      { status: 422, headers: { "Cache-Control": "no-store" } },
    );
  }
  try {
    const response = await fetch(`${runtimeBaseUrl()}/${path}`, {
      method: "POST",
      cache: "no-store",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: rawBody || "{}",
      signal: AbortSignal.timeout(20_000),
    });
    return new NextResponse(await response.arrayBuffer(), {
      status: response.status,
      headers: {
        "Cache-Control": "no-store",
        "Content-Type": response.headers.get("content-type") || "application/json",
        "X-Global-Terminal-Runtime": "same-origin-proxy",
      },
    });
  } catch {
    return NextResponse.json(
      {
        error: "runtime-api-offline",
        source_status: "unavailable",
        data_gap: "The configured local runtime API did not respond.",
      },
      {
        status: 503,
        headers: {
          "Cache-Control": "no-store",
          "X-Global-Terminal-Runtime": "same-origin-proxy",
        },
      },
    );
  }
}
