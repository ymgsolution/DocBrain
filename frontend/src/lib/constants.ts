export const TOKEN_COOKIE = "docbrain_token";
// Separate cookie, never the same one as TOKEN_COOKIE — a platform admin
// token and a regular user token must never be readable from the same
// storage slot, or a bug in one login flow could silently authenticate the
// other. See app/db/models/platform_admin.py (backend) for the full
// reasoning behind keeping the two systems apart.
export const PLATFORM_TOKEN_COOKIE = "docbrain_platform_token";
export const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";
