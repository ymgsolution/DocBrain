import { cookies } from "next/headers";
import { type NextRequest, NextResponse } from "next/server";
import { API_BASE_URL, TOKEN_COOKIE } from "@/lib/constants";

// The one and only place that turns the browser's httpOnly session cookie
// into the Authorization header FastAPI expects — the browser itself never
// sees the JWT (§10.2 of the architecture doc).
async function proxyToBackend(request: NextRequest, path: string[]): Promise<NextResponse> {
  const cookieStore = await cookies();
  const token = cookieStore.get(TOKEN_COOKIE)?.value;

  const url = new URL(`${API_BASE_URL}/api/v1/${path.join("/")}`);
  url.search = request.nextUrl.search;

  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let body: BodyInit | undefined;
  if (request.method !== "GET" && request.method !== "HEAD") {
    const contentType = request.headers.get("content-type");
    if (contentType?.includes("multipart/form-data")) {
      body = await request.formData();
    } else {
      body = await request.text();
      if (contentType) headers.set("content-type", contentType);
    }
  }

  const backendResponse = await fetch(url, { method: request.method, headers, body });
  const responseBody = await backendResponse.arrayBuffer();

  return new NextResponse(responseBody, {
    status: backendResponse.status,
    headers: {
      "content-type": backendResponse.headers.get("content-type") ?? "application/json",
    },
  });
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, { params }: RouteContext) {
  return proxyToBackend(request, (await params).path);
}

export async function POST(request: NextRequest, { params }: RouteContext) {
  return proxyToBackend(request, (await params).path);
}

export async function PATCH(request: NextRequest, { params }: RouteContext) {
  return proxyToBackend(request, (await params).path);
}

export async function DELETE(request: NextRequest, { params }: RouteContext) {
  return proxyToBackend(request, (await params).path);
}
