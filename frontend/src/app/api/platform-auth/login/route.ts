import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { API_BASE_URL, PLATFORM_TOKEN_COOKIE } from "@/lib/constants";

export async function POST(request: Request) {
  const body = await request.text();

  const backendResponse = await fetch(`${API_BASE_URL}/api/v1/platform/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body,
  });

  const data = await backendResponse.json();

  if (!backendResponse.ok) {
    return NextResponse.json(data, { status: backendResponse.status });
  }

  const cookieStore = await cookies();
  cookieStore.set(PLATFORM_TOKEN_COOKIE, data.token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    expires: new Date(data.expiresAt),
  });

  return NextResponse.json({ admin: data.admin });
}
