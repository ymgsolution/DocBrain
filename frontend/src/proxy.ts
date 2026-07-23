import { type NextRequest, NextResponse } from "next/server";
import { TOKEN_COOKIE } from "@/lib/constants";

// Next.js 16 renamed `middleware.ts` -> `proxy.ts` (exported fn `proxy`, not
// `middleware`). This only checks token *presence*, not validity — the JWT
// itself is verified per-request by the backend; a 401 there is caught by
// the API client and redirects to /login as a second line of defense.
const PUBLIC_PATHS = ["/login"];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isPublicPath = PUBLIC_PATHS.some((path) => pathname.startsWith(path));
  const token = request.cookies.get(TOKEN_COOKIE)?.value;

  if (!token && !isPublicPath) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (token && isPublicPath) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api/).*)"],
};
