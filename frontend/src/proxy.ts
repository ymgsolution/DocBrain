import { type NextRequest, NextResponse } from "next/server";
import { TOKEN_COOKIE } from "@/lib/constants";

// Next.js 16 renamed `middleware.ts` -> `proxy.ts` (exported fn `proxy`, not
// `middleware`). This only checks token *presence*, not validity — the JWT
// itself is verified per-request by the backend; a 401 there is caught by
// the API client and redirects to /login as a second line of defense.
const PUBLIC_PATHS = ["/login", "/forgot-password"];

// Reachable without a session, but — unlike /login — also reachable *with*
// one. A share link has to behave the same for everybody: an internal user
// checking the link they just sent must see the client's view, not get
// bounced to the dashboard. Matched as its own prefix rather than being
// added to PUBLIC_PATHS precisely so that difference is explicit.
const SHARED_PATHS = ["/share/", "/invite/", "/reset-password/"];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isPublicPath = PUBLIC_PATHS.some((path) => pathname.startsWith(path));
  // Note the trailing slash in SHARED_PATHS: "/share/<token>" opens, but a
  // bare "/share" (or anything like "/shared-secrets") does not, so this
  // can't accidentally widen into a hole.
  const isSharedPath = SHARED_PATHS.some((path) => pathname.startsWith(path));
  const token = request.cookies.get(TOKEN_COOKIE)?.value;

  if (isSharedPath) {
    return NextResponse.next();
  }

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
