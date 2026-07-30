import { cookies } from "next/headers";
import { type NextRequest, NextResponse } from "next/server";
import { API_BASE_URL, PLATFORM_TOKEN_COOKIE } from "@/lib/constants";

// Mirrors api/bff/[...path]/route.ts exactly, except it reads the platform
// cookie and forwards to /api/v1/platform/* — a separate proxy, not a
// parameterized version of the same one, so the two token cookies can never
// be read from the wrong route by a future edit to either file.
async function proxyToBackend(request: NextRequest, path: string[]): Promise<NextResponse> {
  const cookieStore = await cookies();
  const token = cookieStore.get(PLATFORM_TOKEN_COOKIE)?.value;

  const url = new URL(`${API_BASE_URL}/api/v1/platform/${path.join("/")}`);
  url.search = request.nextUrl.search;

  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let body: BodyInit | undefined;
  if (request.method !== "GET" && request.method !== "HEAD") {
    const contentType = request.headers.get("content-type");
    body = await request.text();
    if (contentType) headers.set("content-type", contentType);
  }

  const backendResponse = await fetch(url, { method: request.method, headers, body });
  const isNullBodyStatus = [204, 205, 304].includes(backendResponse.status);
  const responseBody = isNullBodyStatus ? null : await backendResponse.arrayBuffer();

  const responseHeaders = new Headers({
    "content-type": backendResponse.headers.get("content-type") ?? "application/json",
  });

  return new NextResponse(responseBody, {
    status: backendResponse.status,
    headers: responseHeaders,
  });
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, { params }: RouteContext) {
  return proxyToBackend(request, (await params).path);
}

export async function POST(request: NextRequest, { params }: RouteContext) {
  return proxyToBackend(request, (await params).path);
}

// A route handler only accepts the methods it exports — anything else is a
// 405 from Next.js before proxyToBackend is ever reached. This one had only
// GET and POST because the platform area had no other verbs until
// PATCH /organizations/{id}/settings; the tenant-facing /api/bff proxy has
// exported PATCH and DELETE since it needed them.
export async function PATCH(request: NextRequest, { params }: RouteContext) {
  return proxyToBackend(request, (await params).path);
}
