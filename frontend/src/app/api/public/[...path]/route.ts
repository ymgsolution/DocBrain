import { type NextRequest, NextResponse } from "next/server";
import { API_BASE_URL } from "@/lib/constants";

// The public sibling of /api/bff — and the difference is the entire point:
// this route NEVER reads the session cookie and never sets an Authorization
// header. A share page must behave identically whether or not the person
// opening it happens to have a DocBrain session, so a logged-in user
// checking their own link sees exactly what their client sees.
//
// GET and POST only. POST is needed because two unauthenticated actions
// genuinely write: accepting an invitation (which creates the account) and
// completing a password reset. Both are guarded server-side by a
// single-use, expiring token — see the backend's /public routers.
async function proxyPublic(request: NextRequest, path: string[]): Promise<NextResponse> {
  const url = new URL(`${API_BASE_URL}/api/v1/public/${path.join("/")}`);
  url.search = request.nextUrl.search;

  const headers = new Headers();
  let body: BodyInit | undefined;
  if (request.method === "POST") {
    body = await request.text();
    const contentType = request.headers.get("content-type");
    if (contentType) headers.set("content-type", contentType);
  }

  const backendResponse = await fetch(url, { method: request.method, headers, body });
  const isNullBodyStatus = [204, 205, 304].includes(backendResponse.status);
  const responseBody = isNullBodyStatus ? null : await backendResponse.arrayBuffer();

  const responseHeaders = new Headers({
    "content-type": backendResponse.headers.get("content-type") ?? "application/json",
    // Belt and braces: the backend already sends these on shared content,
    // but a shared document must not be indexed or cached by anything in
    // between, so they're asserted here too.
    "x-robots-tag": "noindex, nofollow",
    "cache-control": "private, no-store",
  });
  const disposition = backendResponse.headers.get("content-disposition");
  if (disposition) responseHeaders.set("content-disposition", disposition);
  const nosniff = backendResponse.headers.get("x-content-type-options");
  if (nosniff) responseHeaders.set("x-content-type-options", nosniff);

  return new NextResponse(responseBody, {
    status: backendResponse.status,
    headers: responseHeaders,
  });
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, { params }: RouteContext) {
  return proxyPublic(request, (await params).path);
}

export async function POST(request: NextRequest, { params }: RouteContext) {
  return proxyPublic(request, (await params).path);
}
