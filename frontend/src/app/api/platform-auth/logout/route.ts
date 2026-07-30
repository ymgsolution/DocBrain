import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { PLATFORM_TOKEN_COOKIE } from "@/lib/constants";

export async function POST() {
  const cookieStore = await cookies();
  cookieStore.delete(PLATFORM_TOKEN_COOKIE);
  return NextResponse.json({ success: true });
}
