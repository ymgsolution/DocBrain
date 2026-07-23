# DocBrain Project Status

> **This is the single source of truth for the project.** It must be updated whenever a feature is added, modified, refactored, removed, or completed. See [Important Rules](#important-rules) at the bottom.

**Last updated:** 2026-07-24 (AI feature track — text extraction wired live end-to-end: enqueue on upload/new-version/restore, worker processes automatically, hard-delete cleans up; pre-Gemini, still no user-facing surface)

---

## 1. Project Overview

| | |
|---|---|
| **Project Name** | DocBrain |
| **Purpose** | A focused document workspace that solves six specific pains: hard-to-find documents, no standard naming, unclear "latest version," no version tracking, no review reminders, no centralized dashboard. Phase 1 is deliberately scoped to *no AI features* — a clean, structured corpus is treated as the prerequisite/quality-gate for Phase 2 AI work, not a parallel effort. |
| **Hackathon** | Ahmedabad AI Hackathon #5 — "Smart Document Manager" problem statement |
| **Current Technology Stack** | Frontend: Next.js 16 (App Router, Turbopack) + TypeScript + Tailwind CSS v4 + shadcn/ui (Base UI primitives, not Radix) + TanStack Query + React Hook Form + Zod + next-themes + Lucide icons. Backend: Python 3.11+ / FastAPI, managed with `uv`. Database: Supabase Postgres (free tier), accessed directly via SQLAlchemy (not Supabase's client SDK/PostgREST). Storage: local filesystem (`backend/uploads/`), not Supabase Storage. Auth: mock identity (pick a seeded user, no password) with real signed JWTs, held in an httpOnly cookie set by a Next.js route handler. |
| **Current Architecture** | Backend: layered (router → service → repository), package-by-feature under `app/modules/`. Frontend: feature-first (`src/features/`) for business logic + a BFF proxy (`/api/bff/[...path]`) that turns the httpOnly session cookie into a `Bearer` header before forwarding to FastAPI — the browser never sees the JWT. |
| **Deployment Plan** | Frontend → Vercel; backend → local for the demo (or a small always-on host later — the API base URL is externalised config, so this is a one-line change whenever it happens, not a code change). Not yet deployed anywhere — currently local-only. |

Full architecture rationale lives in [docs/DOCBRAIN-ARCHITECTURE.md](docs/DOCBRAIN-ARCHITECTURE.md) (authoritative; supersedes `docs/PHASE-1-ARCHITECTURE.md`, which is kept only for its product-thinking sections).

---

## 2. Current Development Status

- ✅ Planning
- ✅ Architecture
- ✅ Database Design
- ✅ Backend Foundation
- ✅ Backend APIs (all modules from §9.1 of the architecture doc are built and manually verified)
- 🟨 Testing (extensive manual/curl verification done per-feature on the backend; browser-driven Playwright smoke test done for the shell; no automated `pytest`/component-test suite yet — that's Phase 6 in the roadmap)
- ✅ Frontend Phase 4 — **complete** (Phase 4.1 — Application Shell. 4.2 — Dashboard. 4.3 — Document Explorer. 4.4 — Upload Document. 4.5 — Document Details. 4.6 — Version History. 4.7 — Categories Admin. 4.8 — Tags Admin. 4.9 — Settings: profile (read-only), theme toggle, default page size — both preferences genuinely wired into the app, not just stored: theme persists across login and the Explorer's page size actually reads the saved value. Every screen from §6 (S1–S10) is now built and verified end-to-end in a real browser. Phase 5 (Integration hardening) and Phase 6 (Testing) are next per the roadmap — see §11)
- ✅ Pending Reviews UI + Trash UI (§6.7/§6.8) — the two remaining documented screens (S6, S8) that sat outside the strict 4.1–4.9 module order. `/reviews` (Reviewer/Admin queue, filters, mark-as-reviewed) and `/trash` (all users, owner-or-Admin scoped, restore + Admin-only type-to-confirm permanent delete). Found and fixed a backend gap along the way: there was no way to list trashed documents at all — added `GET /api/v1/documents/trash`.
- ✅ Phase 5 — Integration (§19.6) — an audit pass, not new construction: verified the canonical J2 flow (§4.3, Upload→Categorize→Search→View→Update Version→Dashboard Refresh) works end-to-end without touching a terminal, then systematically audited every screen's error handling against §16.5's HTTP-status contract via a dedicated research pass, closing the real gaps it found — see §3 and §9 for the full list (422/409 field-level errors now map onto the actual form field instead of a generic toast, the XHR upload path now redirects on 401 like every other request, a logic bug in Version History's conflict handling was fixed, and the app finally has styled `not-found.tsx`/`error.tsx` instead of falling through to Next's defaults).
- 🟨 **AI feature track (new, separate from the §19 hackathon roadmap)** — planned end-to-end (see the published "Smart Rename & Auto-Tag — Gemini Rollout Plan": phased rollout starting in shadow mode, `app/ai/` provider-abstraction architecture, Postgres-backed job queue, prompt/token strategy, UX). Text extraction (classic parsing, not an AI call) is now fully built, wired, and verified live end-to-end: every document upload/new-version/restore automatically queues an extraction job, a background worker processes it, and hard-delete cleans up after itself — all confirmed against the real running API, not just unit tests. No Gemini integration yet, no UI yet, nothing user-facing. Deliberate ordering: extraction has no external API dependency and no subjective quality gate, so it's the one piece of the AI pipeline safe to build for real before any Gemini work starts.
- ⬜ Deployment

---

## 3. Completed Features

### Project Setup

- **Monorepo scaffolding** — `backend/` (FastAPI + `uv`) and `frontend/` (Next.js) at repo root.
  - Completed: 2026-07-23
- **Backend skeleton** — `app/main.py` with `/api/v1/health`, `app/core/config.py` (pydantic-settings), folder structure matching the architecture doc's §9.1.
  - Completed: 2026-07-23
- **Frontend skeleton** — Next.js App Router, TypeScript, Tailwind, shadcn/ui initialized with a handful of primitives (button, card, input, dialog, avatar, badge, skeleton, sonner). Feature-first folders created but empty.
  - Completed: 2026-07-23
  - Notes: No real screens exist yet — this is scaffolding only.
- **Supabase connection** — pooled Postgres connection verified working (session pooler, port 5432, `+psycopg` driver).
  - Completed: 2026-07-23
  - Notes: Found and fixed two real issues along the way — a real DB password briefly landed in the committed `.env.example` template (moved to gitignored `.env`), and a copy-paste typo (`db@` merged into the pooler hostname) that broke DNS resolution.
- **Tooling** — `uv` for backend package management (chosen over plain `venv`/`pip` for speed). `.vscode/settings.json` pointing Pylance at `backend/.venv`.
  - Completed: 2026-07-23

### Database (Phase 2)

- **Schema** — 8 SQLAlchemy models (`User`, `Category`, `Document`, `DocumentVersion`, `Tag`, `DocumentTag`, `ActivityEvent`, `UserPreference`) matching architecture doc §7 exactly, including the `documents` ↔ `document_versions` circular FK (resolved via `use_alter` + a post-creation `ALTER TABLE`).
  - Completed: 2026-07-23
- **Migrations** — 2 Alembic migrations applied: initial schema (tables, indexes, triggers) and a bug-fix migration (see Known Issues → resolved).
  - Completed: 2026-07-23
- **Postgres-specific indexing** — GIN index on `documents.search_vector`, case-insensitive functional unique index on `categories.name` (`lower(name)`), partial index for the Explorer's default "active docs, newest first" query.
  - Completed: 2026-07-23
- **Triggers (system-owned denormalized state)** — 4 PL/pgSQL triggers: `search_vector` refresh (title/tags/description/category/current-filename, weighted A–D), tag-change → touch document, `document_versions` insert → bump `documents.version_count`, `document_tags` insert/delete → adjust `tags.usage_count`.
  - Completed: 2026-07-23
  - Notes: All 4 triggers verified with real insert/update/delete smoke tests, not just code review.
- **Seed script** (`backend/scripts/seed.py`) — idempotent (truncates + reseeds). Produces 5 users (all 3 roles), 12 categories, ~30 tags, ~52 documents with multi-version histories and a deliberate review-status mix (overdue/due-soon/fine/none).
  - Completed: 2026-07-23
  - Notes: Found and fixed a real bug where initial version-upload dates could land in the future relative to "today" — fixed and reverified zero future-dated rows.

### Authentication

- **Mock login + real JWT** — `POST /auth/login` (email only, must match a seeded user), `GET /auth/users` (persona picker), `GET /auth/me`, `POST /auth/logout`. Tokens are real signed JWTs (HS256, 24h expiry) despite the identity source being mocked.
  - Completed: 2026-07-23
- **Authorization plumbing** — `get_current_user` and `require_role(*roles)` FastAPI dependencies; used by every protected endpoint since.
  - Completed: 2026-07-23
- **Error handling foundation** — domain exception hierarchy (`NotFoundError`, `UnauthorizedError`, `PermissionDeniedError`, `ConflictError`, `ValidationError`, `PayloadTooLargeError`, `UnsupportedMediaTypeError`, `GoneError`) mapped to the exact `{error:{code,message,correlationId,fields?}}` envelope from architecture doc §16.6. Correlation-ID middleware on every request/response.
  - Completed: 2026-07-23
- **Swagger UI testability** — switched `get_current_user` from a plain `Header()` param to a proper `HTTPBearer` security scheme, so `/docs` shows one global "Authorize" button instead of requiring the token to be pasted per-endpoint.
  - Completed: 2026-07-23

### Documents

- **Storage layer** — `StoragePort` protocol + `LocalFileSystemStorage` adapter (temp-write → atomic move, path-traversal-safe reads, self-cleaning empty directories), streaming SHA-256 checksum.
  - Completed: 2026-07-23
- **File validation** — extension allowlist + magic-byte MIME sniffing via `python-magic`/`libmagic` (declared `Content-Type` is never trusted).
  - Completed: 2026-07-23
- **Create document (+ version 1)** — atomic per the architecture doc's §12.1 write protocol (DB commit happens before the physical file move, so a DB failure never leaves an orphan file). Auto-computes `review_due_date` from the category's default review period when not explicitly set.
  - Completed: 2026-07-23
- **List / filter / search / paginate** — full-text search via `tsvector` + `ts_rank_cd`, filters for category/tag(AND)/owner/review-status, standard pagination.
  - Completed: 2026-07-23
- **Get detail** — touches `last_accessed_at` on each view (powers the "recently accessed" dashboard widget).
  - Completed: 2026-07-23
- **Update metadata** — permission-checked (owner, or Reviewer/Admin; owner reassignment restricted to Reviewer/Admin).
  - Completed: 2026-07-23
- **Soft delete / restore (Trash)** and **hard delete** (Admin-only, Trash-only, purges files from disk).
  - Completed: 2026-07-23
  - Notes: Found and fixed a real bug here — hard-deleting a document with a *restored* version (`v3.restored_from_version_id → v1`) threw a 500, because that self-referential FK had no `ON DELETE` behavior. Fixed with `ON DELETE SET NULL` via a new migration, reverified the exact failing scenario end-to-end.
- **List Trash** (`GET /documents/trash`) — added 2026-07-23 when building the Trash frontend screen. Architectural gap: `GET /documents` hardcodes `status=ACTIVE` and the architecture doc's §8.3 never actually specified a way to list deleted documents at all, despite §6.8 documenting a full Trash screen. Scoped identically to soft-delete/restore (owner sees only their own trashed documents; Admin sees every trashed document org-wide) — same permission rule, no new authorization concept. Added a `Document.deleted_by_user` relationship (the `deleted_by` FK column already existed but had no relationship object) so the response can include who deleted it, not just when.
  - Completed: 2026-07-23

### Versions

- **List versions**, **upload new version** (row-locked parent-document fetch to prevent two concurrent uploads from allocating the same version number), **download** (inline for PDF/text/image, attachment otherwise, `X-Content-Type-Options: nosniff`), **restore version** (creates a new version with the old content — append-only history is never rewritten).
  - Completed: 2026-07-23
  - Notes: Verified byte-for-byte content integrity across create → v2 upload → restore-v1-as-v3, confirming v1's file is genuinely untouched by later uploads.

### Taxonomy (Categories & Tags)

- **Categories** — list (with live document counts), create, update/archive, delete (blocked while in use, case-insensitive name uniqueness, auto-deduped slugs).
  - Completed: 2026-07-23
- **Tags** — list/autocomplete, rename (conflict-checked), merge (target absorbs source; verified against a real overlap case — 4 documents already had both tags — with zero duplicate rows produced), delete (usage-guarded).
  - Completed: 2026-07-23
  - Notes: Admin-only for all mutations; reads open to any authenticated user (needed for the upload form's category picker / tag autocomplete).

### Reviews

- **Pending reviews queue** (`GET /reviews/pending`, Reviewer/Admin only, sorted by due date ascending, with computed `review_status`/`days_overdue`).
  - Completed: 2026-07-23
- **Mark as reviewed** (`POST /documents/{id}/reviews`) — resets `review_due_date` by the category's default review period, logs an activity event with the optional note folded in.
  - Completed: 2026-07-23

### Dashboard

- **Summary aggregate** (`GET /dashboard/summary`) — 4 KPIs, category distribution, recently-added, recently-accessed, expiring-soon, pending-reviews count, all in one call.
  - Completed: 2026-07-23
- **Activity feed** (`GET /dashboard/activity`) — paginated, newest first.
  - Completed: 2026-07-23
  - Notes: Cross-checked against the real seeded corpus — `expiring_soon` count and `pending_reviews_count` agree exactly (8 = 8).

### Frontend — Application Shell (Phase 4.1)

- **Design tokens** — from-scratch enterprise palette (navy/indigo primary, semantic success/warning/danger/info), light + dark mode, all as CSS custom properties in `globals.css`. Radius tightened to 8px for a less "consumer app" feel.
  - Completed: 2026-07-23
  - Notes: Found and fixed a real pre-existing bug while in there — `--font-sans` was circularly self-referencing instead of pointing at the loaded Geist font, so Geist Sans was silently never applying.
- **API layer foundation** — typed `fetch` wrapper (`apiClient`) with a matching `ApiError` class, TanStack Query provider, shared `PagedResponse<T>`/`ApiErrorBody` types. One API-layer file per backend module, built incrementally as each frontend phase needs it (only `authApi` exists so far).
  - Completed: 2026-07-23
- **BFF proxy** (`/api/bff/[...path]`) — reads the httpOnly session cookie server-side, forwards to FastAPI with a `Bearer` header; the browser never sees the JWT. Special-cased `/api/auth/login` (sets the cookie) and `/api/auth/logout` (clears it).
  - Completed: 2026-07-23
- **Auth guard** (`src/proxy.ts`) — Next.js 16 renamed `middleware.ts` → `proxy.ts`; redirects unauthenticated requests to `/login?next=...` and authenticated requests away from `/login`.
  - Completed: 2026-07-23
- **Login page** (S1) — persona-card picker (fetched live from `GET /auth/users`, not hardcoded) + email field, React Hook Form + Zod validation.
  - Completed: 2026-07-23
- **Reusable component library** — `PageHeader`, `AppBreadcrumb`, `EmptyState`, `ErrorState`, `ReviewStatusBadge`, `FileTypeIcon`, `UserAvatar`, `ConfirmDialog`, plus 15 shadcn primitives (dropdown-menu, sheet, tooltip, table, tabs, etc.).
  - Completed: 2026-07-23
- **Application shell** — data-driven sidebar (role-filtered nav items), topbar (search/upload placeholders, theme toggle, user menu), responsive collapse to an off-canvas `Sheet` drawer below `lg`, breadcrumb, dashboard placeholder page proving the whole stack works end to end.
  - Completed: 2026-07-23
  - Notes: Found and fixed a real bug via browser testing — the user menu crashed on open (`MenuGroupContext is missing`) because Base UI (shadcn's primitive library here, not Radix) requires `DropdownMenuLabel` to be wrapped in `DropdownMenuGroup`, unlike Radix where it worked standalone. Verified the full login → shell → dark mode → mobile → logout loop with a headless-Chromium Playwright script (screenshots + console-error check), not just code review.

### Frontend — Dashboard (Phase 4.2)

- **`dashboardApi` feature module** — `features/dashboard/{types,api,hooks}.ts`, consuming `GET /dashboard/summary` and `GET /dashboard/activity` through the shared `apiClient`. Shared `DocumentSummary`/`CategorySummary`/`TagSummary`/`VersionSummary`/`ReviewStatus` types moved to `src/types/document.ts` so the upcoming Explorer/Details phases reuse them instead of redefining them.
  - Completed: 2026-07-23
- **KPI section** — 4 KPI cards (Total Documents, Uploaded This Week, Versions Tracked, Categories In Use), 2-col on mobile → 4-col from `lg` up.
  - Completed: 2026-07-23
- **Pending Reviews banner** — role-gated (Reviewer/Admin only, via a `REVIEWER_ROLES` constant shared with the sidebar's nav-item gating so both surfaces can never drift apart), hidden entirely when the count is 0.
  - Completed: 2026-07-23
- **Documents by Category** — horizontal bar list (shadcn `Progress`), each row a link to `/documents?categoryId=…` (Explorer doesn't exist until Phase 4.3 — link is wired now, page lands once built, same forward-dependency pattern already used for the topbar's disabled Upload/Search buttons).
  - Completed: 2026-07-23
- **Recently Added / Recently Accessed / Expiring Soon** — one generic `DocumentListCard` (title/icon/list/empty-state/"View all" link) reused for all three via props, instead of three near-duplicate components. Expiring Soon shows a `ReviewStatusBadge` computed client-side by `getReviewStatus()`, which mirrors the backend's exact overdue/due-soon/ok thresholds (`documents/repository.py`) so a document is never badged differently than it would filter in the Explorer.
  - Completed: 2026-07-23
  - Notes: `DocumentSummary` (as returned by `/dashboard/summary`) has no `lastAccessedAt` field, only `updatedAt` — "Recently Accessed" currently displays `updatedAt` as its meta line for lack of a more precise timestamp from the backend. Not a frontend bug; flagged in Known Issues.
- **Activity feed** — reads `GET /dashboard/activity`, each row an `ActivityFeedItem` (avatar + summary + relative time via a new dependency-free `formatRelativeTime()` helper — no date library added, per the "no unnecessary dependencies" rule).
  - Completed: 2026-07-23
- **New shared components** — `KpiCard`, `DocumentListItem`, `ActivityFeedItem` (in `components/shared/`, reusable by future Explorer/Details phases, not dashboard-specific).
  - Completed: 2026-07-23
- **Loading/error states** — independent skeletons for the summary and activity queries (one slow endpoint doesn't block the other), `ErrorState` with retry for both, empty states for every list widget.
  - Completed: 2026-07-23
  - Notes: Found and fixed a real Base UI console warning via browser testing — `Button` rendered as a `Link` (`render={<Link .../>}`, used for "View all" / "Review now") needs `nativeButton={false}`, since Base UI's `Button` defaults to expecting a real `<button>` element. Verified zero console errors after the fix, across desktop/dark-mode/tablet/mobile, and across both an Admin persona (banner + all widgets visible) and an Employee persona (banner and Pending-Reviews nav item both correctly hidden).

### Frontend — Document Explorer (Phase 4.3)

- **`documentsApi` + `taxonomyApi` feature modules** — `features/documents/{types,api,hooks}.ts` (`GET /documents` with the full filter set) and `features/taxonomy/{types,api,hooks}.ts` (`GET /categories`, `GET /tags` — list-only for now; full CRUD lands with the admin screens in 4.7/4.8). `useDocuments()` uses TanStack Query's `placeholderData` to keep the previous page's rows on screen while a new page/filter loads, instead of flashing a skeleton on every pagination click.
  - Completed: 2026-07-23
- **URL-driven filter state** — every filter (`q`, `categoryId`, `tagId[]`, `reviewStatus`, `sort`, `page`) lives in the URL query string, not React state, parsed fresh from `useSearchParams()` on every render. This is why the Dashboard's `/documents?categoryId=…` and `/documents?reviewStatus=due_soon` links (built in Phase 4.2, dead until now) work correctly as entry points with no Explorer-side code aware of the Dashboard at all.
  - Completed: 2026-07-23
- **Filter bar** — debounced `SearchBox` (new shared component, 300ms, event-driven debounce via a ref'd timeout rather than an effect), Category select, Review Status select, `TagFilterCombobox` (Popover + Command, client-side filtered — the tag vocabulary is a few dozen entries, so one fetch-all beats a debounced per-keystroke server search), Sort select.
  - Completed: 2026-07-23
- **Results table** — desktop `DocumentsTable` (Title/Category/Owner/Version/Review/Updated columns, reusing `FileTypeIcon`/`UserAvatar`/`ReviewStatusBadge`), collapsing below `lg` to `DocumentsMobileList`, which reuses the `DocumentListItem` built for the Dashboard rather than a new mobile-specific row component.
  - Completed: 2026-07-23
- **`PaginationBar`** (new shared component) — Previous/Next + "Showing X–Y of Z", reusable by Trash/Pending Reviews/admin tables later.
  - Completed: 2026-07-23
- **Topbar search wired up** — previously a disabled placeholder ("Coming in the Explorer phase"); Enter now navigates to `/documents?q=…` from anywhere in the app. Deliberately submit-triggered, not debounce-live like the Explorer's own search box, since it's a cross-page entry point, not in-page filtering.
  - Completed: 2026-07-23
- **Loading/error/empty states** — row-skeleton list while loading, `ErrorState` with retry, and two distinct empty states ("no documents at all" vs. "no results for these filters," so a new empty account isn't told to "try adjusting your filters").
  - Completed: 2026-07-23
  - Notes: Found and fixed a real Base UI gotcha via browser testing — `Select.Value` does **not** auto-derive its displayed label from the matching `SelectItem`'s children (unlike Radix's `SelectValue`); it just renders the raw value string unless given a `children` render-function (`{(value) => label}`). All three Explorer selects were initially showing raw values (`"all"`, `"updated_at"`) instead of their labels — fixed by adding label-lookup render functions. Documented as a new Base UI-vs-Radix decision (§9) since it'll bite again the moment `Select` is reused elsewhere. Verified end-to-end with headless-Chromium Playwright: table renders, search/category/review-status/tag/sort filters all correctly update the URL and results, pagination, row-click navigation, empty state for a nonsense query, and mobile view swapping the table for a stacked list — zero console errors except the expected 404 from clicking into `/documents/{id}` (Phase 4.5).

### Frontend — Upload Document (Phase 4.4)

- **Architecture correction before implementing** — re-checked the architecture doc's §6.3 before writing code, per the standing "explain before implementing" rule. My own earlier `PROJECT_STATUS.md` phrasing had called this a "two-step stepper"; §6.3 actually specifies a single unified modal (dropzone + file card + metadata form together), not a wizard. Built to the doc, not my own paraphrase.
- **`UploadDropzone`** (new shared component) — drag-and-drop + click-to-browse, per the original design-system component list.
- **`TagInput`** (documents feature) — chip input with autocomplete against existing tags *and* free-text creation (the backend's `tags: list[str]` accepts names and creates new ones on the fly via `get_or_create_tags`). Deliberately separate from the Explorer's `TagFilterCombobox`, which only filters by existing tags — different semantics (names vs. IDs, creatable vs. filter-only), so not the same component. Implemented as a plain controlled dropdown rather than `Popover`/`Command`, since those toggle open on trigger click, which would have fought with keeping the list open while typing.
- **Upload dialog** (`UploadDocumentDialog`) — RHF + Zod for Title/Category/Description/Review-date, plus separately-managed `file` and `tags` state (not everything fits RHF's native-input model). Lazy-loaded via `next/dynamic({ ssr: false })` from the topbar's Upload button so the form/dropzone code isn't in every page's initial bundle. Submit button disabled until a file is selected and required fields are valid (§6.3's "disabled until valid").
  - Completed: 2026-07-23
- **Determinate upload progress** — `documentsApi.create()` uses `XMLHttpRequest` instead of `fetch`, specifically because `fetch` has no cross-browser way to observe upload progress; §6.3 requires a determinate progress bar with byte count. The BFF proxy needed no changes — it already forwards multipart bodies transparently.
  - Completed: 2026-07-23
- **Non-dismissible during upload** — the dialog's `onOpenChange` handler ignores every close attempt (Escape, outside click, close button, Cancel) while a mutation is pending; since Base UI funnels all of those through the same callback, one guard covers all of them without needing Radix-style `onInteractOutside`/`onEscapeKeyDown` props (which don't exist on Base UI's `Dialog.Popup`).
  - Completed: 2026-07-23
- **Client-side pre-validation** — extension allowlist and 25MB size limit mirrored from the backend's `core/config.py` defaults (`lib/upload-constants.ts`, documented decision, same pattern as `getReviewStatus()`) — instant "That file type isn't supported" / "File exceeds the size limit" feedback before a round trip; the backend remains the real authority.
  - Completed: 2026-07-23
- **Success/error feedback** — Sonner toast `"«Title» uploaded (v1)"` with a "View document" action (navigates to `/documents/{id}`), matching §6.3 exactly; error toasts map `ApiError` messages or fall back to "Upload failed — nothing was saved, retry?". On success, the documents-list and dashboard-summary query caches are invalidated so the Explorer/Dashboard reflect the new document without a manual refresh.
  - Completed: 2026-07-23
  - Notes: Verified end-to-end with headless-Chromium Playwright using a real uploaded file: empty-state submit-button-disabled check, file selection with auto-filled title, category select, tag creation (both an existing-tag suggestion and a brand-new tag), description, review date, progress bar, success toast, dialog auto-close, the new document appearing in both the Explorer and the Dashboard's Recent Activity feed immediately after (cache invalidation confirmed working, not just assumed), and a rejected `.exe` file correctly showing the unsupported-type error. Zero console errors. The test document and tag were deleted afterward via the API so the seed corpus stays at its documented baseline (53 documents). TypeScript, ESLint, and `next build` all clean.

### Frontend — Document Details (Phase 4.5)

- **Two architectural gaps found and fixed before implementing** — per the "explain before implementing" rule:
  1. **Corrected an earlier assumption about file downloads.** §10.2 (and this file's own earlier Known Issues entry) assumed downloads needed a signed/short-lived-token URL because a browser can't attach a Bearer header to a plain `<a href>`. That's true for a bare API call, but **not** for a same-origin request through the BFF — the browser sends the httpOnly session cookie automatically, and the BFF proxy already turns that into the Bearer header before calling FastAPI. So a plain `<a href="/api/bff/documents/{id}/versions/{n}/content">` just works, no signed URL needed. The actual bug was narrower: the generic BFF proxy (`route.ts`) only forwarded `content-type` from the backend response, silently dropping `Content-Disposition` (filename, inline-vs-attachment) and `X-Content-Type-Options`. Fixed by forwarding both headers through generically — safe for every route, since only file-content responses set them.
  2. **No way to fetch one document's activity.** `ActivityEvent.document_id` existed on the model with no query path exposed — `GET /dashboard/activity` had no `documentId` filter. Added an optional `documentId` query param to that existing endpoint (repository, service, router), reusing the same schema rather than adding a new endpoint.
  - Completed: 2026-07-23
- **Real bug found via browser testing: the BFF proxy crashed on any 204 No Content response.** The Fetch spec forbids passing a body (even an empty `ArrayBuffer`) to the `Response` constructor alongside a null-body status (204/205/304) — `DELETE /documents/{id}` was the *first* 204 response this proxy ever had to forward (every prior phase only used GET/POST/PATCH-with-body), so the bug was latent since Phase 4.1 and only surfaced now. Fixed by passing `null` as the body for 204/205/304 statuses. Found because Delete genuinely 500'd in the browser despite the backend correctly returning 204 — traced via the Next.js dev server's own error log, not just the browser console.
  - Completed: 2026-07-23
- **`/documents/[id]`** — header (title, file-type icon, version badge, `ReviewStatusBadge`), role-gated action bar (Download — owner/Reviewer/Admin via `_assert_can_edit`'s exact rule mirrored client-side; Mark as reviewed — Reviewer/Admin only; Edit — owner or Reviewer/Admin; Delete — owner or Admin only, *not* Reviewer, matching `_assert_can_delete` exactly), three tabs (Overview/Versions/Activity) per §6.5.
  - Completed: 2026-07-23
- **Overview tab** — `DocumentPreview` (PDF/text/image inline via `<iframe>`/`<img>` pointed at the BFF content URL with `disposition=inline`, mirroring the backend's own inline-eligibility rule so we never request inline for a type the server would force to `attachment`; anything else falls back to a file-type card + Download) and `MetadataPanel`, which becomes `EditMetadataForm` in place when editing — reuses `TagInput` from Upload rather than a new tag editor.
  - Completed: 2026-07-23
  - Notes: PDF preview couldn't be visually confirmed inside headless-Chromium screenshots — Playwright's bundled Chromium doesn't ship an active PDF-viewer plugin in headless mode, so the iframe renders blank there. Verified correctness a different way instead: fetched the exact inline URL directly and confirmed a valid 5-page PDF with `content-disposition: inline` and `content-type: application/pdf` — the real gap was environmental (headless testing), not the app. Renders normally in any real browser (Chrome, Edge, Firefox, Safari all have native PDF-in-iframe support).
- **Versions tab (read-only this phase)** — version table (number + Current badge, uploader, date, size, change note, Download). Restore-this-version and Upload-new-version are Phase 4.6's actions, per the module order — not built yet, intentionally.
  - Completed: 2026-07-23
- **Activity tab** — reuses the Dashboard's `ActivityFeedItem` against the newly-added `documentId`-filtered `GET /dashboard/activity`.
  - Completed: 2026-07-23
- **Mark as reviewed** — dialog with an optional note, `POST /documents/{id}/reviews`, success toast names the new due date per §6.7's exact copy.
  - Completed: 2026-07-23
- **Delete with Undo** — soft-delete via `ConfirmDialog` (reused from Phase 4.1, not rebuilt), success toast with an "Undo" action that calls `POST /documents/{id}/restore`, redirects to the Explorer.
  - Completed: 2026-07-23
- **404/error states** — `GET /documents/{id}` returning `NotFoundError` already carries the exact §6.5 copy ("This document doesn't exist or was deleted.") from the backend, so the page just displays `error.message` rather than hardcoding it a second time, plus a "Back to Documents" link.
  - Completed: 2026-07-23
  - Notes: Verified end-to-end with headless-Chromium Playwright: view → edit → save, mark-as-reviewed with note, Versions tab (Current badge, download), Activity tab (all real events including the test's own trash/restore cycles, proving the audit trail is genuine), 404 state for a bogus ID, soft-delete → redirect → toast → Undo → document accessible again, and an Employee persona correctly missing Mark-as-reviewed/Edit for a document they don't own. Zero console errors beyond expected 404s/401 from the deliberately-bogus-ID and post-logout test steps. Test-induced description clutter and Supabase network-latency-driven flakiness in early test runs were both diagnosed and aren't real bugs (see notes above and §10). TypeScript, ESLint, and `next build` all clean.

### Frontend — Version History (Phase 4.6)

- **`documentsApi.uploadVersion`/`restoreVersion`** — the two actions deliberately left out of the Versions tab in Phase 4.5. A shared `xhrUpload<T>()` helper was factored out of `documentsApi.create` (Phase 4.4) and `uploadVersion`, since both need the same XMLHttpRequest-for-progress mechanics — avoids the "duplicate logic" anti-pattern.
  - Completed: 2026-07-23
- **Upload new version** — added to the header's action bar (Download, **Upload new version**, Mark as reviewed, Edit, Delete), per §6.5 rather than buried in the Versions tab; gated on the same owner-or-Reviewer/Admin rule as Edit (matches the backend's `_assert_can_upload_version` exactly, which is identical to `_assert_can_edit`). `UploadVersionDialog` — dropzone (reused `UploadDropzone`) + required change note (mirrors the backend's 5-character minimum) + determinate progress bar — reuses the same XHR pattern from Upload, lazy-loaded via `next/dynamic` from the header.
  - Completed: 2026-07-23
- **Restore this version** — a Restore button on every non-current Versions-tab row (hidden on Current, per §6.6), reusing the existing `ConfirmDialog` from Phase 4.1 rather than a new component. The confirmation text names both version numbers explicitly, per §6.6's requirement ("Restore version 1? This creates a new version using version 1's content and replaces version 2 as current.").
  - Completed: 2026-07-23
  - Notes: Verified end-to-end with headless-Chromium Playwright against a throwaway test document (not the seed corpus — `DocumentVersion` rows are append-only with no delete endpoint, so testing against seed data would have permanently inflated its version count and the Dashboard's `versionsTracked` total): upload-new-version → v2 becomes current, restore v1 → v3 created and becomes current with `changeNote` "Restored from version 1", Current badge and Restore-button visibility both correct at every step, Activity tab shows both the `VERSION_UPLOADED` and `VERSION_RESTORED` events, and an Employee persona correctly sees neither action. One apparent bug (header still showing the pre-restore version badge in a screenshot) turned out to be the same Supabase network-latency timing already documented elsewhere, not a caching bug — confirmed by reloading fresh, which showed the correct version immediately. The throwaway document was hard-deleted afterward via the API; `totalDocuments`/`versionsTracked` confirmed back at the documented baseline (53 / 99). TypeScript, ESLint, and `next build` all clean.

### Frontend — Categories Admin (Phase 4.7)

- **`ForbiddenState`** (new shared component) — the app's first 403 UI, per §6.10's exact copy ("You don't have permission to view this — requires the {role} role."). `/admin/categories` is reachable directly by URL even though the sidebar already hides its nav link from non-Admins, so the page needed its own guard.
  - Completed: 2026-07-23
- **`categoriesApi` gains create/update/delete** (previously list-only, built in Phase 4.3 for the Explorer's filter dropdown). `useCategories()` gained an optional `includeArchived` param, defaulting to `false` so the Explorer's existing call site is unaffected — the admin page passes `true` to show everything.
  - Completed: 2026-07-23
- **`/admin/categories`** — table (name, description — hidden below `md`, usage count, status), New/Edit via a shared `CategoryFormDialog`, one-click Archive/Unarchive (a separate action from Edit, per §6.9's explicit button list — not folded into the edit form), and Delete disabled-with-tooltip while `documentCount > 0`, mirroring the backend's exact `ConflictError` condition so the button is disabled before a doomed round trip rather than after.
  - Completed: 2026-07-23
  - Notes: The disabled Delete button is wrapped in a `<span tabIndex={0}>` as the actual `TooltipTrigger`, not the button itself — disabled native elements don't reliably fire the hover events a tooltip needs. Verified end-to-end with headless-Chromium Playwright: create → edit → archive → unarchive → delete-blocked-with-tooltip on an in-use seed category (confirmed via the span-hover, not the inert button) → delete-allowed on a throwaway unused category → 403 for a non-Admin persona hitting the URL directly, with the sidebar correctly showing no Categories link for them at all. Category count confirmed back at the documented baseline (12) after cleanup. TypeScript, ESLint, and `next build` all clean.

### Frontend — Tags Admin (Phase 4.8)

- **`tagsApi` gains rename/merge/delete** (previously list-only). Mutations invalidate the same `taxonomyKeys.tags` cache key `TagInput` (Upload/Edit) and `TagFilterCombobox` (Explorer) already read — a rename or merge here is reflected in those pickers automatically, with zero extra invalidation code.
  - Completed: 2026-07-23
- **`/admin/tags`** — table sorted by usage (the backend already returns `usage_count desc, name asc`, matching §6.9's "sorted by usage" with no client-side sort needed), Rename via `RenameTagDialog`, Merge-into via `MergeTagDialog`, Delete disabled-with-tooltip while `usageCount > 0` — same precheck/tooltip pattern established in Categories (4.7), reused rather than re-derived. No "New tag" button — §6.9 only lists Rename/Merge/Delete for Tags (tags are created implicitly through `TagInput`, never directly here).
  - Completed: 2026-07-23
- **Merge confirmation states the affected document count** using the tag's already-known `usageCount` ("Used by N document(s) — they'll be re-tagged with the target tag instead"), satisfying §6.9's requirement without a new backend endpoint to preview the merge.
  - Completed: 2026-07-23
  - Notes: Verified end-to-end with headless-Chromium Playwright using two throwaway tags created via a throwaway document's `TagInput` (never the seed vocabulary): rename, merge into a second tag (toast correctly reported "1 document(s) updated," confirming the backend's already-tagged dedup logic works, not a naive double-insert), delete-blocked-with-tooltip while in use, removed the tag from the document to free it to usage=0, then delete-allowed succeeded, and 403 for a non-Admin persona. Tag count and seed document count both confirmed back at their documented baselines (30 tags, 53 documents) after cleanup. TypeScript, ESLint, and `next build` all clean.

### Frontend — Settings (Phase 4.9) — Phase 4 complete

- **Architectural gap found and fixed before implementing**: the `user_preferences` table (§7) exists and the seed script populates one row per user, and §2.11/§6.10 scope Settings to "toggle theme; set default page size" with **Dependencies: Auth** — but §8.2's documented Auth API surface never actually exposed an endpoint for it. Added `GET`/`PATCH /auth/me/preferences` to the existing auth module (not a new module, per the doc's own "Dependencies: Auth"), backed by a get-or-create in the service layer so a user without a preferences row (shouldn't happen given the seed, but not guaranteed forever) still resolves instead of 404ing.
  - Completed: 2026-07-23
- **`/settings`** — read-only profile card (avatar, name, email, role) + a preferences card (Theme select, Default page size select), per §6.10. No role gate — unlike Categories/Tags, this is personal, not admin-only.
  - Completed: 2026-07-23
- **Both preferences are wired into real consumers, not just stored.** The topbar's `ThemeToggle` (Phase 4.1) now also calls `useUpdatePreferences()` alongside `next-themes`' `setTheme()`, so a theme change from *either* the topbar or Settings persists identically and survives to the next login. The Explorer's page size, hardcoded to `25` since Phase 4.3, now reads `usePreferences().defaultPageSize` as its default — verified by changing it to 50 in Settings and confirming the Explorer immediately showed "Showing 1–50."
  - Completed: 2026-07-23
  - Notes: Found and fixed a real bug via browser testing, twice, in the same component. First pass: gating the Select's `value` with a `mounted` boolean (`mounted ? theme : undefined`) triggered a genuine Base UI warning — "changing the uncontrolled value state of Select to be controlled" — since `undefined` reads as uncontrolled and a later string flips it controlled. Removing the `mounted` guard entirely fixed that but caused a **real hydration mismatch** (not just a warning): `next-themes` resolves `theme` from `localStorage` via a lazy `useState` initializer that runs synchronously on the client's first render, so the client's actual first paint already shows the real theme while the server (no `localStorage`) rendered a fallback — a genuine SSR/client text mismatch, not a false positive. Correct fix: value is *always* a string (`mounted ? (theme ?? "system") : "system"`) — the `undefined`-vs-string toggle is what Base UI warns about, not which string is shown, and using `"system"` (matching the server's fallback) as the pre-mount placeholder instead of `undefined` satisfies both constraints at once. Documented as a decision (§9) since next-themes' own docs only warn about the FOUC/flash case, not this specific controlled-component interaction with Base UI's `Select`.
  - Verified end-to-end with headless-Chromium Playwright as an Employee persona (confirming Settings isn't Admin-gated): profile display, theme change to Light with immediate visual effect, persistence confirmed across a page reload, page-size change to 50 with the Explorer immediately reflecting it, and both preferences restored to their original seeded values afterward. Zero console errors after the fix. TypeScript, ESLint, and `next build` all clean.

**Phase 4 (Frontend) is now complete — every screen from architecture doc §6 (S1–S10) is built and verified in a real browser, not just code-reviewed.**

### Frontend — Pending Reviews & Trash (S6, S8 — outside the 4.1–4.9 module order)

- **Architectural gap found and fixed before implementing**: no backend endpoint existed to list trashed documents at all (`GET /documents` hardcodes `status=ACTIVE`, and §8.3 never specified a Trash-listing route despite §6.8 documenting the full screen). Added `GET /api/v1/documents/trash` to the existing `documents` module (not a new module — it's a status-filtered list alongside the soft-delete/restore/hard-delete endpoints already there), scoped identically to those existing endpoints (owner-or-Admin).
  - Completed: 2026-07-23
- **`/reviews`** (Reviewer/Admin only, 403 for everyone else) — table of due/overdue documents (title, category, owner, due date with days-overdue, status badge), category/owner filters, `[Open]`/`[Mark as reviewed]` per row. Backed entirely by the already-built `GET /reviews/pending` and `POST /documents/{id}/reviews` (Phase 3) — only the frontend wiring (`features/reviews/`) and page were new. Reuses the existing `MarkReviewedDialog` from Document Details (Phase 4.5) as-is rather than building a second one.
  - Completed: 2026-07-23
- **`/trash`** (all users, no role gate — scoping happens server-side) — table (title, category, owner, deleted by, deleted at), `[Restore]` on every row (always valid for whatever rows are visible, since the list itself is already scoped to what that user is allowed to restore), and an Admin-only `[Delete permanently]` using a new `TypeToConfirmDialog` (generalizes the existing `ConfirmDialog` — the architecture doc explicitly requires type-to-confirm for this one destructive action, unlike every other delete in the app).
  - Completed: 2026-07-23
- **`documentsApi.hardDelete()`** added (the one CRUD action on documents that had no frontend wiring yet — `DELETE /documents/{id}/permanent` existed on the backend since Phase 3 but nothing called it). The shared `invalidateAfterDocumentChange()` helper (used by mark-reviewed/soft-delete/restore/update) now also invalidates `["reviews"]`/`["trash"]`, so any document mutation keeps both queues in lockstep automatically instead of each call site remembering to do it.
  - Completed: 2026-07-23
  - Notes: Verified end-to-end with headless-Chromium Playwright. Reviews: logged in as Rahul (Reviewer), confirmed the queue renders real overdue/due-soon seed documents, marked one as reviewed and confirmed the row count dropped by one and the toast showed the new due date; confirmed an Employee persona sees no "Pending Reviews" nav link and gets `ForbiddenState` hitting `/reviews` directly by URL. Trash: created a throwaway document as Priya, soft-deleted it, confirmed it appeared in her own scoped Trash view, restored it, confirmed it reappeared in Documents, soft-deleted it again, logged in as Anita (Admin) and confirmed she sees it too (org-wide scope), opened the type-to-confirm dialog and confirmed the delete button stays disabled with no input and with the wrong text typed, only enabling once the exact title is typed, then permanently deleted it and confirmed Trash was empty again. Zero console errors in either flow. One leftover throwaway document from an early failed test iteration (a Playwright selector bug, fixed before the passing run) was found afterward via a direct API count check and cleaned up — document/Trash counts confirmed back at the documented baseline (53 documents, 0 in Trash, 12 categories) once the console errors and 404s from a stale query invalidation (see §10) were confirmed to be a pre-existing, non-blocking issue rather than something this phase introduced. TypeScript, ESLint, and `next build` all clean.

### Phase 5 — Integration (§19.6)

An audit pass, not new construction — every screen was already wired to the real backend from Phase 4's build-and-verify-as-you-go approach. This phase checked two things: the canonical J2 loop end-to-end, and error-handling consistency against the architecture doc's own §16.5 HTTP-status contract.

- **J2 flow verified live** (§4.3: Dashboard → Upload → fill metadata → submit → toast → topbar search → Document Details → Upload new version with a mandatory change note → Version 2 current, v1 preserved → Dashboard reflects the update) — every step done through the UI, zero terminal/API calls mid-flow, zero console errors. This is §19.6's literal exit criteria and it passed on the first fully-corrected run.
  - Completed: 2026-07-23
- **Error-handling audit against §16.5** — a dedicated research pass read every mutation and error-display site in the frontend and checked it against the documented status→behavior table (400/401/403/404/409/413/415/422/500). Findings and fixes:
  - **422/409 field-level errors were never mapped onto form fields anywhere in the app** — `ApiError.fields` was fully plumbed from the backend envelope but zero call sites ever read it; every field-specific rejection (duplicate category name, duplicate tag name, invalid category on document edit/upload, etc.) surfaced only as a generic toast. Added one shared helper, `applyApiFieldErrors()` (`lib/form-errors.ts`), and wired it into all 5 `react-hook-form`-backed mutations in the app (login, category create/edit, tag rename, document upload, document metadata edit). A duplicate category/tag name — the most common real-world 409 in this app — now shows an inline error under the exact field, in the same still-open dialog, instead of a toast the user has to mentally connect back to a field. `edit-metadata-form.tsx`'s category field had no error-display slot at all before this — added one, since the new field-error plumbing would otherwise set an error that never rendered.
    - Completed: 2026-07-23
  - **The XHR upload path (`xhrUpload()`, used by document/version upload — the two request types that can't go through `apiClient` because `fetch` can't report upload progress) didn't redirect to `/login` on a 401**, unlike every other request type. Added the same status check `handleResponse` already does.
    - Completed: 2026-07-23
  - **A real logic bug in Version History's restore-conflict handling**: the ternary meant to show a 409-specific "someone uploaded a new version" message had its condition inverted — it fired on network failures (not `ApiError`) and showed the generic backend message for actual 409s, the opposite of its evident intent. Fixed the condition and added a "Refresh" toast action wired to the tab's own `refetch()`, giving the 409 case the "contextual... resolution path" §16.5 actually asks for, not just a corrected message.
    - Completed: 2026-07-23
  - **`useLogout()` had no `onError` at all** (silent failure on a genuine network error) and **Settings' two preference-update handlers hardcoded generic strings instead of reading `error.message`** (inconsistent with the identical pattern used correctly everywhere else in the app) — including the topbar `ThemeToggle`'s equivalent call, which had the same gap but sat outside the audit's `features/`/`app/` scope since it lives in `components/layout/`. All three fixed to match the established `error instanceof ApiError ? error.message : "<fallback>"` pattern.
    - Completed: 2026-07-23
  - **`correlationId` (§16.6 — always present on the backend envelope) was passed to `ErrorState` at only 4 of 10 call sites.** Added it to the other 6 (dashboard activity widget, document detail page, Categories admin, Tags admin, Versions tab, Activity tab) so a 500 shows the same support-traceable reference everywhere, not just on some screens.
    - Completed: 2026-07-23
  - **No `not-found.tsx`/`error.tsx` existed anywhere under `frontend/src/app/`** — a route the router itself can't resolve, or a render-time exception outside any page's own try/catch-equivalent, fell through to Next.js's unstyled defaults with no way back into the app and no correlation reference. Added both, reusing the app's existing `ErrorState`/`EmptyState` visual language and the exact §6.10 copy ("We couldn't find that page" + [Go to Dashboard]) for the 404 case.
    - Completed: 2026-07-23
  - Notes: A handful of findings were deliberately left as-is rather than fixed in this pass — see §10 Known Issues for what and why (the audit's full findings, including the non-issues it confirmed were already correct, are not reproduced here). Verified with headless-Chromium Playwright: duplicate category name and duplicate tag rename now show the inline field error instead of a bare toast (confirmed the dialog stays open, no redundant toast fires alongside it, and the offending data was never actually mutated); an unmatched route now renders the new styled 404 with a working "Go to Dashboard" link; normal category-create and normal document-upload were re-verified to still succeed (no regression from the new field-error path intercepting the success case). TypeScript, ESLint, and `next build` all clean.

### AI Feature Track — Text Extraction Foundation (pre-Gemini)

*First increment of a separate, planned initiative — "Smart Rename & Auto-Tag" — scoped and phased outside the §19 hackathon roadmap. No Gemini integration and no user-facing surface yet; this is the deterministic, non-AI foundation the eventual suggestion pipeline reads from.*

- **`document_extracted_text` table** — one row per `document_version_id` (FK, unique), storing only a pointer (`extracted_text_path`) plus status/method/char_count/error metadata — never the extracted text content itself. The content lives on disk as a `.txt` sibling of the source file (`{version.storage_path}.txt`), read/written through the existing `StoragePort` (`save_temp`/`commit`/`open_for_read`/`delete` — zero new methods needed). Mirrors exactly how `document_versions` itself never stores file bytes in Postgres, just a `storage_path`.
  - Completed: 2026-07-24
- **`ai_jobs` table** — a shared background-work queue (`job_type`, `status`, `attempt_count`, `last_error`, `next_retry_at`), designed to be reused by every future AI processing stage (extraction today; embedding/metadata-suggestion jobs later), not extraction-specific. Composite index on `(status, next_retry_at)` for the worker's claim query.
  - Completed: 2026-07-24
- **`app/text_extraction/`** — pure, DB-decoupled extractors (`PdfExtractor`, `DocxExtractor`, `XlsxExtractor`, `PptxExtractor`, `PlainTextExtractor`), each a bytes-in/text-out function with zero DB or HTTP knowledge, dispatched via a small extension→extractor `registry.py`. Legacy binary Office formats (`.doc`, `.ppt`, `.xls`) have no reliable pure-Python parser and deliberately resolve to `None` from the registry (→ `ExtractionStatus.UNSUPPORTED`) rather than a bad-faith attempt.
  - Completed: 2026-07-24
- **`app/ai_jobs/`** — `AiJobRepository` (enqueue, `claim_batch` via `SELECT ... FOR UPDATE SKIP LOCKED` — the same row-locking pattern already used for version-number allocation — `mark_succeeded`/`mark_failed` with exponential backoff capped at 5 attempts) and `worker.py` (`run_once`/`run_forever`, a pluggable `job_type → handler` registry). Deliberately not wired into `main.py` or app startup — runs as its own process once a real handler exists to register.
  - Completed: 2026-07-24
  - Notes: **The first pytest suite in this project** (`tests/text_extraction/test_extractors.py`, 6 tests) — `tests/` had been empty since Phase 2. Each format's extractor is tested against a real, in-memory fixture generated with that format's own writer library (`python-docx`, `openpyxl`, `python-pptx`) rather than committing binary fixture files; the PDF case uses `pypdf.PdfWriter` to build a real, valid, blank PDF and confirms the extractor handles it without raising (pypdf's own read-path correctness isn't re-tested — that's a well-tested third-party concern). Added `[tool.pytest.ini_options]` to `pyproject.toml` (`pythonpath = ["."]`) since this was the first test that needed to import `app.*` at all. `mypy`/`ruff` both clean on all new code (added `types-openpyxl` as a dev dependency to close the one stub gap); the live dev server, migration, and a direct DB/registry smoke check were all re-verified after wiring.
- **`TextExtractionService.process_job`** — the `AiJobType.EXTRACT` handler that ties everything above together: loads the `DocumentVersion`, dispatches via the registry, runs the extractor against the source file (`StoragePort.open_for_read`), writes the result to the `.txt` sibling (`save_temp`/`commit`), and upserts `document_extracted_text`. An unsupported extension (registry returns `None`) writes `ExtractionStatus.UNSUPPORTED` rather than retrying — not a transient failure, retrying it would never succeed. A parent document hard-deleted between enqueue and claim (job's `document_version_id` no longer resolves) is treated as a no-op, not an error — the job's reason to exist is already gone.
  - Completed: 2026-07-24
- **Wired live**: `documents/service.py::create_document`, `versions/service.py::upload_version`, and `versions/service.py::restore_version` each now enqueue one `AiJob(EXTRACT)` in the same transaction as their existing `ActivityEvent` insert — the only touch to this "core" code, purely additive. Restores enqueue too, even though the content is byte-identical to an existing version's already-extracted text (re-deriving is cheap and not an AI call, so uniformity — every new `document_versions` row gets exactly one `EXTRACT` job, no special-casing — won over reusing a prior result). `hard_delete` now also collects and deletes each version's `.txt` sibling (the DB rows already cascade for free via FK `ondelete`; only the files needed an explicit call, same reasoning as the pre-existing source-file cleanup one line above it). `app/ai_jobs/main.py` is the worker's first real runnable entrypoint (`uv run python -m app.ai_jobs.main`), registering this handler.
  - Completed: 2026-07-24
  - Notes: Verified fully live, not just unit-tested: uploaded a real throwaway document via the actual API → confirmed an `AiJob` row appeared automatically with the correct `document_version_id` → ran the worker (`run_once`) → confirmed `document_extracted_text` showed `SUCCEEDED` with the exact right `char_count` and the `.txt` file on disk byte-for-byte matched the source content → soft-deleted then hard-deleted the document via the API → confirmed both the source file and its `.txt` sibling were gone from disk *and* both the `document_extracted_text` and `ai_jobs` rows were gone from the DB (cascade). Document count confirmed back at baseline afterward (the one throwaway fully cleaned up; the count still reflects unrelated concurrent manual testing in the live app, not this work). `mypy`/`ruff`/`pytest` all clean; the 3 pre-existing `mypy` findings elsewhere in the codebase (a stub gap, two `reviews/router.py` nullable-date findings) are unrelated and untouched. **Still explicitly deferred:** everything Gemini-related — no metadata/tag/title suggestion yet, still nothing user-facing.

---

## 4. Pending Features

### High Priority

*(Phase 4 — Frontend — is complete, and so are the two S6/S8 screens that sat outside its module order. What's below is everything else in the roadmap, not yet prioritized into a phase.)*

- Automated backend test suite (`pytest`) — unit tests for permission checks, version allocation, search ranking; one integration test covering the full upload→version→search→download loop (roadmap Phase 6)

### Low Priority

- FR-19: Naming policy per category (live filename preview at upload time)
- FR-21: Duplicate-detection warning on upload (checksum is already computed and stored — the "warn if identical content already exists" UX flow itself isn't built)
- FR-22: Content text extraction from PDF/DOCX for search (search currently covers title/description/tags/category/original-filename only, not document body text)
- FR-23: Bulk actions in the Explorer (multi-select re-tag/re-categorise/delete)
- FR-25: Starred/favourites (not in the DB schema at all yet)

---

## 5. Current Folder Structure

```
DocBrain/
├── PROJECT_STATUS.md          # this file
├── README.md
├── docs/
│   ├── DOCBRAIN-ARCHITECTURE.md   # authoritative architecture doc
│   └── PHASE-1-ARCHITECTURE.md    # superseded draft, kept for product-thinking sections
├── .vscode/
│   └── settings.json           # points Pylance at backend/.venv
│
├── backend/
│   ├── pyproject.toml / uv.lock
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   │       ├── d3070d18c042_initial_schema.py
│   │       ├── e97f9d207d17_fix_restored_from_version_id_ondelete_.py
│   │       └── a8e785ca1e16_add_document_extracted_text_and_ai_jobs_.py
│   ├── app/
│   │   ├── main.py                 # FastAPI app, middleware, router registration
│   │   ├── core/                   # config, security (JWT), dependencies, exceptions,
│   │   │                           # error_handlers, middleware (correlation ID), logging
│   │   ├── db/
│   │   │   ├── base.py / session.py
│   │   │   └── models/             # user, category, document, document_version, tag,
│   │   │                           # activity_event, user_preference, ai_job,
│   │   │                           # document_extracted_text, enums
│   │   ├── schemas/                # Pydantic DTOs: auth, document, version, taxonomy,
│   │   │                           # review, trash, dashboard, mappers.py (ORM → DTO)
│   │   ├── modules/                # package-by-feature
│   │   │   ├── auth/                (router, service, repository — also owns
│   │   │   │                        #   GET/PATCH /auth/me/preferences, Phase 4.9)
│   │   │   ├── documents/           (router, service, repository — also owns
│   │   │   │                        #   GET /documents/trash, added for the Trash screen)
│   │   │   ├── versions/            (router, service, repository)
│   │   │   ├── taxonomy/            (router, service, repository)
│   │   │   ├── reviews/             (router, service, repository)
│   │   │   └── dashboard/           (router, service, repository)
│   │   ├── storage/                 # StoragePort, LocalFileSystemStorage, checksum
│   │   ├── text_extraction/         # AI feature track (pre-Gemini) — pure, DB-decoupled
│   │   │   ├── port.py              #   TextExtractor protocol, ExtractionResult
│   │   │   ├── extractors/          #   pdf, docx, xlsx, pptx, plain
│   │   │   ├── registry.py          #   extension -> (extractor, ExtractionMethod)
│   │   │   ├── repository.py        #   DocumentExtractedTextRepository
│   │   │   └── service.py           #   TextExtractionService — the AiJobType.EXTRACT handler
│   │   ├── ai_jobs/                 # AI feature track — shared background job queue
│   │   │   ├── repository.py        #   enqueue, claim_batch (SKIP LOCKED), mark_succeeded/failed
│   │   │   ├── worker.py            #   run_once/run_forever, pluggable job_type -> handler
│   │   │   └── main.py              #   runnable entrypoint: uv run python -m app.ai_jobs.main
│   │   └── utils/                   # file_validation, slugify
│   ├── scripts/
│   │   └── seed.py
│   ├── tests/
│   │   └── text_extraction/
│   │       └── test_extractors.py   # first pytest suite in the project (6 tests)
│   └── uploads/                     # local file storage (gitignored contents)
│       ├── tmp/
│       └── documents/{document_id}/
│           ├── v{n}__{slugified-filename}       # source file
│           └── v{n}__{slugified-filename}.txt   # extracted text sibling, once Step 5 wires it
│
└── frontend/
    ├── package.json / components.json
    ├── src/
    │   ├── proxy.ts                 # auth guard (Next.js 16's renamed middleware.ts)
    │   ├── app/
    │   │   ├── layout.tsx           # root layout — Theme/Query/Tooltip providers, Toaster
    │   │   ├── not-found.tsx        # router-level 404 (Phase 5) — unmatched routes only
    │   │   ├── error.tsx            # root error boundary (Phase 5) — render-time exceptions
    │   │   ├── globals.css          # design tokens: full color palette, light+dark
    │   │   ├── (auth)/login/page.tsx
    │   │   ├── (app)/
    │   │   │   ├── layout.tsx       # sidebar + topbar shell
    │   │   │   ├── page.tsx         # dashboard (Phase 4.2 — real widgets, not a placeholder)
    │   │   │   ├── documents/
    │   │   │   │   ├── page.tsx     # Explorer (Phase 4.3) — Suspense-wrapped (useSearchParams)
    │   │   │   │   └── [id]/page.tsx  # Document Details (4.5) + Version History (4.6)
    │   │   │   ├── admin/
    │   │   │   │   ├── categories/page.tsx  # Categories admin (Phase 4.7) — Admin-only, 403 guard
    │   │   │   │   └── tags/page.tsx        # Tags admin (Phase 4.8) — rename/merge/delete
    │   │   │   ├── reviews/page.tsx         # Pending Reviews (S6) — Reviewer/Admin-only, 403 guard
    │   │   │   ├── trash/page.tsx           # Trash (S8) — all users, server-side owner-or-Admin scoping
    │   │   │   └── settings/page.tsx        # Settings (Phase 4.9) — profile, theme, page size —
    │   │   │                                #   Phase 4 complete after this
    │   │   └── api/
    │   │       ├── auth/login/route.ts    # sets the httpOnly session cookie
    │   │       ├── auth/logout/route.ts   # clears it
    │   │       └── bff/[...path]/route.ts # cookie -> Bearer header proxy to FastAPI
    │   ├── components/
    │   │   ├── ui/                  # 23 shadcn primitives (Base UI, not Radix)
    │   │   ├── layout/              # Sidebar, Topbar, UserMenu, ThemeToggle, AppBreadcrumb, nav-items.ts
    │   │   ├── shared/               # PageHeader, EmptyState, ErrorState, ReviewStatusBadge,
    │   │   │                        # FileTypeIcon, UserAvatar, ConfirmDialog, TypeToConfirmDialog,
    │   │   │                        # KpiCard, DocumentListItem, ActivityFeedItem, SearchBox,
    │   │   │                        # PaginationBar, UploadDropzone, DownloadLink, ForbiddenState
    │   │   └── providers/           # QueryProvider, ThemeProvider
    │   ├── features/
    │   │   ├── auth/                # types.ts, api.ts, hooks.ts (login/logout/me/personas +
    │   │   │                        #   getPreferences/updatePreferences, Phase 4.9),
    │   │   │                        # components/login-form.tsx
    │   │   ├── taxonomy/            # types.ts, api.ts (categories: list/create/update/delete;
    │   │   │                        #   tags: list/rename/merge/delete), hooks.ts,
    │   │   │                        # components/ (CategoryFormDialog, RenameTagDialog,
    │   │   │                        #   MergeTagDialog)
    │   │   ├── documents/           # types.ts, api.ts (list/get/update/delete/restore/hardDelete/
    │   │   │                        #   markReviewed/listVersions/uploadVersion/restoreVersion/
    │   │   │                        #   create — all upload paths share an xhrUpload<T>() helper),
    │   │   │                        # hooks.ts, components/ (DocumentFilters, DocumentsTable,
    │   │   │                        #   DocumentsMobileList, TagFilterCombobox, TagInput,
    │   │   │                        #   UploadDocumentDialog, UploadVersionDialog, DocumentHeader,
    │   │   │                        #   DocumentPreview, MetadataPanel, EditMetadataForm,
    │   │   │                        #   MarkReviewedDialog, VersionsTab, DocumentActivityTab)
    │   │   ├── reviews/             # types.ts, api.ts, hooks.ts — GET /reviews/pending only;
    │   │   │                        #   mark-as-reviewed is reused from features/documents/
    │   │   ├── trash/               # types.ts, api.ts, hooks.ts — GET /documents/trash only;
    │   │   │                        #   restore/hardDelete are reused from features/documents/
    │   │   └── dashboard/           # types.ts, api.ts, hooks.ts,
    │   │                            # components/ (KpiSection, CategoryDistribution,
    │   │                            #   DocumentListCard, ActivityFeed, PendingReviewsBanner,
    │   │                            #   WidgetSkeleton)
    │   ├── lib/
    │   │   ├── api-client.ts        # typed fetch wrapper + ApiError, targets /api/bff;
    │   │   │                        # getVersionContentUrl() for downloads/previews
    │   │   ├── constants.ts         # TOKEN_COOKIE, API_BASE_URL
    │   │   ├── format.ts            # getInitials(), formatRelativeTime(), getReviewStatus(),
    │   │   │                        # formatFileSize()
    │   │   ├── upload-constants.ts  # extension allowlist + size limit, mirrors backend config
    │   │   ├── form-errors.ts       # applyApiFieldErrors() (Phase 5) — maps ApiError.fields onto
    │   │   │                        #   react-hook-form field errors
    │   │   └── utils.ts             # cn()
    │   ├── hooks/                   # empty — cross-feature hooks land here as needed
    │   └── types/
    │       ├── api.ts               # UserRole, ApiErrorBody, PagedResponse<T>
    │       └── document.ts          # ReviewStatus, CategorySummary, TagSummary,
    │                                 # VersionSummary, DocumentSummary, DocumentDetail,
    │                                 # VersionDetail — shared across dashboard/Explorer/
    │                                 # Upload/Details
    └── public/
```

---

## 6. Database Status

**Hosted on:** Supabase Postgres (free tier), accessed directly via SQLAlchemy — no PostgREST/client SDK.

### Tables (10)

| Table | Purpose |
|---|---|
| `users` | Seeded identities; role = EMPLOYEE / REVIEWER / ADMIN |
| `categories` | Controlled vocabulary; case-insensitive unique name, optional default review period |
| `documents` | Logical document identity; owns `search_vector`, `current_version_id`, review/trash state |
| `document_versions` | Append-only version history; unique `(document_id, version_number)` |
| `tags` / `document_tags` | Normalised tags + join table (composite PK) |
| `activity_events` | Append-only audit trail |
| `user_preferences` | Theme, page size |
| `document_extracted_text` | *(AI feature track, pre-Gemini)* One row per `document_version_id` (unique FK) — a pointer (`extracted_text_path`) + status/method/char_count/error, never the text content itself. Content lives on disk as a `.txt` sibling of the source file. |
| `ai_jobs` | *(AI feature track)* Shared background-work queue — `job_type`/`status`/`attempt_count`/`next_retry_at`. Designed for reuse by every future AI stage (extraction today; embedding/suggestion jobs later), not extraction-specific. |

### Relationships

- `users` → `documents` (owner), `document_versions` (uploader), `activity_events` (actor) — 1:N
- `categories` → `documents` — 1:N, RESTRICT (must archive, not delete, while in use)
- `documents` ↔ `document_versions` — circular reference (`current_version_id` → a version; `document_id` → parent doc), resolved via `use_alter` FK added after both tables exist
- `documents` ↔ `tags` via `document_tags` — M:N, CASCADE from either side
- `document_versions.restored_from_version_id` — self-referential, `ON DELETE SET NULL` (fixed from the default RESTRICT — see Known Issues)
- `document_versions` → `document_extracted_text` / `ai_jobs` — 1:1 / 1:N, both `ON DELETE CASCADE` — hard-deleting a document cascades away extraction metadata and any pending jobs for free at the DB level; the `.txt` file on disk still needs an explicit `storage.delete()` call (planned, not yet wired — see §3's AI Feature Track notes)

### Migrations (3, all applied)

1. `d3070d18c042_initial_schema` — all 8 original tables, indexes, and the 4 triggers.
2. `e97f9d207d17_fix_restored_from_version_id_ondelete_` — bug fix (see §10 Known Issues).
3. `a8e785ca1e16_add_document_extracted_text_and_ai_jobs_` — the two new AI-feature-track tables above.

### Seed Data

Run via `uv run python -m scripts.seed` (idempotent — truncates first). Current state as of last check:

| Table | Rows |
|---|---|
| `users` | 5 |
| `categories` | 12 |
| `tags` | 30 |
| `documents` | 53 (52 seeded + 1 real upload via manual testing) |
| `document_versions` | 99 |
| `document_tags` | 146 |
| `activity_events` | 107 |

### Indexes

- GIN on `documents.search_vector`
- B-tree on `documents.category_id`, `owner_id`, `status`, `updated_at`, `review_due_date`
- Partial index: `documents (updated_at DESC) WHERE status = 'ACTIVE'`
- Functional unique index: `categories (lower(name))`
- Unique: `document_versions (document_id, version_number)`
- Unique: `document_extracted_text (document_version_id)`
- Composite: `ai_jobs (status, next_retry_at)` — the worker's claim query

---

## 7. Backend Status

**All Phase 3 modules complete.** 20 unique routes, 24 method+path combinations, all manually verified against real Supabase data (not mocks) — real PDF uploads, byte-for-byte download checks, real permission-denial tests per role.

| Module | Router | Service | Repository | Notes |
|---|---|---|---|---|
| Auth | ✅ | ✅ | ✅ | Mock login, real JWT, `/auth/me/preferences` GET+PATCH (added 2026-07-23 for Settings) |
| Documents | ✅ | ✅ | ✅ | Full CRUD + Trash (soft delete/restore/**list**, added 2026-07-23) + hard delete |
| Versions | ✅ | ✅ | ✅ | Upload, download, restore |
| Taxonomy | ✅ | ✅ | ✅ | Categories + Tags, admin-only mutations |
| Reviews | ✅ | ✅ | ✅ | Pending queue, mark-reviewed |
| Dashboard | ✅ | ✅ | ✅ | Summary + activity feed, now with an optional `documentId` filter (added 2026-07-23 for the Details page's Activity tab) |
| Text Extraction *(AI track)* | ➖ still no router — not request-facing | ✅ `TextExtractionService` | ✅ `DocumentExtractedTextRepository` + `AiJobRepository` | Fully wired end-to-end: upload/new-version/restore enqueue automatically, the worker (`app/ai_jobs/main.py`) processes them, hard-delete cleans up. Verified live against the real API + a real worker run, not just `pytest` (6 tests) — still no HTTP surface, so still no curl verification the way every other module has. |

- **Middleware:** CORS, correlation-ID (`X-Correlation-Id` on every request/response).
- **Wire format:** camelCase JSON in and out (`app/schemas/base.py`'s `CamelModel`, plus `alias=` on non-path `Query`/`Form` params) — matches architecture doc §8 exactly. Fixed 2026-07-23; previously the implementation was snake_case despite the doc specifying camelCase. Internal Python code is unaffected (still snake_case attributes/kwargs).
- **Authentication:** JWT (HS256), `HTTPBearer` security scheme (Swagger `/docs` shows one "Authorize" button).
- **File upload:** temp-write → DB commit → atomic move protocol; extension allowlist + magic-byte MIME sniffing; 25MB cap; UUID-based storage paths (never user input).
- **File download:** no signed-URL scheme needed after all — the BFF proxy's httpOnly-cookie-to-Bearer-header translation already covers plain browser navigation (same-origin request, cookie sent automatically). Corrected an earlier assumption to the contrary; see §9/§10.
- **Versioning:** row-locked version-number allocation; append-only; restore creates a new version rather than rewriting history.
- **Search:** Postgres full-text (`tsvector` + `ts_rank_cd`), trigger-maintained, weighted title > tags > description > category/filename. **Does not** yet index document body content (PDF/DOCX text) — see Pending Features.
- **Pending for backend:** automated test suite (Phase 6 — one real suite now exists, `tests/text_extraction/`, but it covers only the new AI-track extractors, not the original 20 hackathon-roadmap routes). AI feature track's next increment is entirely Gemini-side: provider abstraction (`app/ai/port.py`, mirroring `StoragePort`), the first real prompt, and the shadow-mode suggestion pipeline — the text-extraction foundation it reads from is now fully wired and verified end-to-end.

---

## 8. Frontend Status

| Area | Status |
|---|---|
| Layout / app shell | ✅ Done — sidebar, topbar, breadcrumb, user menu, theme toggle, responsive mobile drawer |
| Login | ✅ Done — persona picker (live data) + email form, RHF + Zod |
| Dashboard | ✅ Done — KPIs, category distribution, recently-added/accessed, expiring-soon, role-gated pending-reviews banner, activity feed, all live-data |
| Upload | ✅ Done — drag-and-drop dropzone, creatable tag input, RHF+Zod metadata form, determinate progress bar (XHR), non-dismissible mid-upload, client-side pre-validation, topbar button wired |
| Explorer | ✅ Done — URL-driven filters (search/category/review-status/tags/sort), table + mobile list, pagination, empty/error/loading states, topbar search wired up |
| Document Details | ✅ Done — header/action bar (role-gated), Overview tab with inline edit, Activity tab, PDF/image/text preview, mark-as-reviewed, delete-with-undo, 404 state |
| Version History | ✅ Done — version table, restore-this-version (with the two-version consequence dialog), upload-new-version, all role-gated |
| Search | ✅ Done — full-text search via the Explorer's search box (in-page, debounced) and the topbar's global search box (submit-triggered, from anywhere in the app) |
| Categories (Admin) | ✅ Done — table with usage counts, New/Edit/Archive/Unarchive, Delete disabled-with-tooltip while in use, 403 for non-Admins |
| Tags (Admin) | ✅ Done — table sorted by usage, Rename, Merge-into (with an affected-document-count dialog), Delete disabled-with-tooltip while in use, 403 for non-Admins |
| Settings | ✅ Done — profile (read-only), theme toggle (synced with the topbar's), default page size (actually wired into the Explorer, not just stored) |
| Pending Reviews | ✅ Done — Reviewer/Admin queue, category/owner filters, mark-as-reviewed (reused dialog), 403 for other roles |
| Trash | ✅ Done — owner-or-Admin scoped table, restore, Admin-only permanent delete with type-to-confirm |
| Error handling | ✅ Audited (Phase 5) — 422/409 field errors map onto the actual form field across all 5 RHF forms, `ErrorState` shows a correlation ID consistently at all 10 sites, app-wide `not-found.tsx`/`error.tsx` exist, one real logic bug fixed (Version History's 409 handling) |
| Responsive Design | ✅ Verified for the shell, Dashboard, Explorer, Upload dialog, Document Details / Version History, Categories/Tags admin, and Settings |

**Phase 4 (Frontend) is complete.** Every screen from architecture doc §6 (S1–S10) is built and verified end-to-end in a real browser, not just code-reviewed. **What exists:** Next.js 16 (App Router, Turbopack) + TypeScript + Tailwind v4 + shadcn/ui (Base UI primitives) + TanStack Query + React Hook Form + Zod + next-themes, fully wired: design tokens, API layer, BFF proxy, auth guard, login, app shell, a live Dashboard, a live Document Explorer, a live Upload flow, a live Document Details + Version History page, live Categories/Tags admin screens, and a live Settings page all working end-to-end — verified with headless-Chromium Playwright scripts (shell: 10-step flow; dashboard: full-content check across Admin/Employee personas, dark mode, tablet, mobile; Explorer: filters, pagination, row navigation, empty state, mobile layout; Upload: a real file upload through the full form, progress bar, success toast, cache invalidation; Details: view/edit/save, mark-as-reviewed, activity, 404, soft-delete-with-undo, role-gating; Version History: upload-new-version, restore-this-version, both against a throwaway test document; Categories: create/edit/archive/unarchive/delete, delete-blocked tooltip, 403 for non-Admins; Tags: rename/merge/delete against throwaway tags, delete-blocked tooltip, 403 for non-Admins; Settings: theme change with persistence across reload, page-size change actually reflected in the Explorer, non-Admin access confirmed), not just code review. Production build (`next build`) succeeds cleanly; TypeScript and ESLint are both clean.

---

## 9. Technical Decisions

*(Append-only — do not edit or remove past entries when architecture changes; add a new entry instead.)*

- **2026-07-23** — FastAPI + Python over the originally-explored Spring Boot/Java stack (per `docs/DOCBRAIN-ARCHITECTURE.md`, which supersedes `docs/PHASE-1-ARCHITECTURE.md`).
- **2026-07-23** — Supabase used purely as hosted Postgres, accessed directly via SQLAlchemy — not through Supabase's client SDK or auto-generated PostgREST layer. Reason: one source of truth for business rules (permission logic, version-number locking) instead of splitting it between the app and Postgres RLS policies.
- **2026-07-23** — Local filesystem storage (`uploads/`), explicitly not Supabase Storage, behind a `StoragePort` abstraction so swapping to S3/MinIO later is a single adapter class.
- **2026-07-23** — `uv` chosen for backend package/venv management over plain `pip`+`venv`, for install speed and removing the "did I activate my venv" failure mode.
- **2026-07-23** — Mock authentication (pick a seeded user, no password) but with **real** JWT mechanics (signed, expiring, verified every request) — so the auth *shape* is production-like even though the identity *source* is a seed list.
- **2026-07-23** — `document_versions.restored_from_version_id` uses `ON DELETE SET NULL` rather than the default RESTRICT — discovered necessary when hard-deleting a document with a restored version threw a real FK violation. Provenance metadata is acceptable to lose on a full purge.
- **2026-07-23** — Search-vector maintenance implemented via Postgres triggers (not application-level recompute-on-write), because it depends on data across 3 tables (documents, categories, tags) that a simple generated column can't reach.
- **2026-07-23** — Denormalized counters (`documents.version_count`, `tags.usage_count`) are DB-trigger-maintained, not application-computed — matches the "DB is the arbiter, not application logic" principle already established for version-number allocation.
- **2026-07-23** — No Vector Database / AI features in Phase 1 — explicitly deferred to Phase 2, per the hackathon ground rules (no external LLM API keys) and the architectural principle that a clean Phase 1 corpus is the quality gate for later AI work.
- **2026-07-23** — Backend: package-by-feature (`app/modules/{feature}/router|service|repository.py`), layered per-feature. Frontend: feature-first (`src/features/{feature}/`) — same philosophy, different codebase.
- **2026-07-23** — `HTTPBearer` security scheme (not a plain `Header()` param) for `get_current_user`, specifically so Swagger UI's `/docs` renders one global "Authorize" button — a deliberate testability/DX choice, not a functional requirement.
- **2026-07-23** — Backend switched to camelCase JSON wire format (`CamelModel` base + aliased `Query`/`Form` params), closing a gap where the implementation had drifted to snake_case despite the architecture doc specifying camelCase. Chosen over the alternative (leaving the API snake_case and adapting the frontend) because it matches the documented contract exactly and is idiomatic for the TypeScript frontend about to be built — internal Python code is untouched, only the wire format changed.
- **2026-07-23** — Frontend color palette designed from scratch (Stripe/Linear-style enterprise palette, navy/indigo primary) rather than derived from a logo — the logo initially provided for reference was a different, unrelated brand ("YMG"), not DocBrain's actual branding.
- **2026-07-23** — This shadcn/ui install uses **Base UI** (`@base-ui/react`) as its underlying primitive library, not Radix UI. API shape is similar but not identical — composition uses a `render` prop (children merge into the element passed to `render`) instead of Radix's `asChild`, and some components are stricter (e.g. `DropdownMenuLabel` requires a `DropdownMenuGroup` wrapper, which Radix didn't enforce). Worth knowing before assuming Radix docs/patterns apply.
- **2026-07-23** — Next.js 16 renamed `middleware.ts` → `proxy.ts` (exported fn `proxy`, not `middleware`); it also now runs on the full Node.js runtime rather than edge-only. Used for the auth guard (`src/proxy.ts`), presence-check only (not full JWT verification — the backend is the real authority and 401s are caught client-side as a second line of defense).
- **2026-07-23** — Auth token lives in an httpOnly cookie set by a Next.js route handler (`/api/auth/login`), never in `localStorage` or client-readable JS — matches the architecture doc's §17.5 requirement and is enforced structurally (the browser literally cannot read it), not just by convention.
- **2026-07-23** — API layer built incrementally, one module at a time, as each frontend phase needs it — not all six modules' API clients built upfront in Phase 4.1. Avoids speculative code for endpoints no page calls yet.
- **2026-07-23** — Shared domain types (`ReviewStatus`, `CategorySummary`, `TagSummary`, `VersionSummary`, `DocumentSummary`) live in `src/types/document.ts`, not inside `features/dashboard/`, because the Explorer and Document Details phases will need the exact same shapes — one definition avoids the shapes drifting apart across features.
- **2026-07-23** — Client-side review-status thresholds (`getReviewStatus()` in `lib/format.ts`) hard-mirror the backend's exact overdue/due-soon/ok cutoffs (`documents/repository.py`'s `<today` / `today..today+30` / `>today+30`), rather than inventing separate frontend thresholds — a document must never show a different badge than it would filter to via the same `reviewStatus` query param in the Explorer.
- **2026-07-23** — No date-formatting library added for the activity feed's relative timestamps (`formatRelativeTime()` uses the built-in `Intl.RelativeTimeFormat`) — matches the "no unnecessary dependencies" rule; revisit only if a real need for timezone-aware or locale-heavy formatting appears later.
- **2026-07-23** — Dashboard widgets that reuse the same card shape (Recently Added / Recently Accessed / Expiring Soon) are one generic `DocumentListCard` driven by props (`meta`, `trailing` render functions), not three near-identical components — avoids the "duplicate logic" anti-pattern the frontend spec explicitly calls out.
- **2026-07-23** — Explorer filter state lives entirely in the URL (`useSearchParams`), not React state — makes results bookmarkable/shareable and back-button-correct for free, and is *why* the Dashboard's `/documents?categoryId=…` links (built one phase earlier, dead until now) work correctly with zero Explorer-side code aware of the Dashboard.
- **2026-07-23** — Base UI's `Select.Value` does not auto-derive its label from the matching `SelectItem`'s children the way Radix's `SelectValue` does — it renders the raw `value` unless given a `children` render-function. A second Base UI-vs-Radix gotcha (after the `DropdownMenuGroup` one in Phase 4.1) — anything reaching for `Select` should expect to pass an explicit label lookup.
- **2026-07-23** — Tag filtering fetches the full tag vocabulary once (`limit: 100`) and filters client-side via cmdk's built-in matching, rather than a debounced per-keystroke server search — the vocabulary is a few dozen entries (not thousands), so a server round-trip per keystroke would be over-engineering for the current scale. Revisit if the tag count grows substantially.
- **2026-07-23** — The topbar's global search box is submit-triggered (Enter navigates to `/documents?q=…`), while the Explorer's own in-page search box is debounce-live — deliberately different UX for a cross-page entry point vs. in-page filtering, not an inconsistency.
- **2026-07-23** — Upload built as a single unified modal (dropzone + file card + metadata form together) per architecture doc §6.3, correcting an earlier `PROJECT_STATUS.md` mischaracterization of it as a "two-step stepper." Re-checked the doc before implementing, per the standing rule — the doc is authoritative over any of my own prior paraphrasing.
- **2026-07-23** — Document upload (`documentsApi.create`) uses `XMLHttpRequest` instead of `fetch` — `fetch` has no cross-browser API for observing upload progress, and the architecture doc requires a determinate progress bar with byte count. The BFF proxy needed zero changes since it already forwards multipart bodies transparently.
- **2026-07-23** — `TagInput` (Upload's creatable tag field) is a separate component from the Explorer's `TagFilterCombobox`, not a shared one — they operate on different data (tag names vs. tag IDs) and different semantics (create-on-the-fly vs. filter-existing-only). Built as a plain controlled dropdown rather than `Popover`/`Command`, since those toggle open on trigger click, which conflicts with keeping a list open while the user types.
- **2026-07-23** — Client-side upload validation (extension allowlist, 25MB size cap) mirrors the backend's `core/config.py` defaults in `lib/upload-constants.ts` — same "instant feedback, backend remains the real authority" pattern already established for `getReviewStatus()`.
- **2026-07-23** — No signed/short-lived-token URL scheme built for file downloads, correcting an assumption made earlier in this file. The BFF proxy already makes plain `<a href="/api/bff/...">` links work: same-origin requests carry the httpOnly session cookie automatically, and the proxy turns that into the Bearer header FastAPI needs. The only real fix needed was forwarding `Content-Disposition`/`X-Content-Type-Options` through the proxy, which it wasn't doing.
- **2026-07-23** — `GET /dashboard/activity` grew an optional `documentId` filter rather than a new per-document-activity endpoint — reuses the existing schema/repository/router, since Document Details' Activity tab needs exactly the same shape the Dashboard already returns, just scoped to one document.
- **2026-07-23** — Document Details' Versions tab is read-only this phase (Download only); restore-this-version and upload-new-version are deliberately deferred to Phase 4.6 (Version History) per the module order, not an oversight.
- **2026-07-23** — `DocumentPreview`'s inline-vs-fallback decision (`isPreviewable()`) hard-mirrors the backend's own `_resolve_disposition` eligibility list (`versions/router.py`: `application/pdf`, `text/plain`, any `image/*`) — the frontend must never attempt an inline preview for a type the backend would force to `attachment` anyway.
- **2026-07-23** — "Upload new version" lives in the Document Details header's action bar, not the Versions tab, per §6.5's explicit action-bar list (Download, Upload new version, Edit, Delete) — matches the doc rather than an intuitive-but-undocumented alternative placement.
- **2026-07-23** — `xhrUpload<T>()` factored out of `documentsApi.create`/`uploadVersion` once a second call site needed identical XMLHttpRequest-for-progress mechanics — avoids duplicating the same ~20 lines twice.
- **2026-07-23** — Restore-this-version's confirmation reuses the existing `ConfirmDialog` (parametrized `description` text) rather than a new dialog component — §6.6 only requires naming both version numbers in the copy, which a dynamic description string satisfies without new UI.
- **2026-07-23** — Version-history mutations (restore, upload-new-version) are tested against a throwaway document created via Upload, never the seed corpus — `DocumentVersion` rows are append-only with no delete endpoint, so testing against seed data would permanently inflate its version count.
- **2026-07-23** — Categories admin's Archive action is a separate one-click button from Edit, not a checkbox inside the edit form — §6.9 lists `[New] [Edit] [Archive]` as three distinct buttons, and semantically archiving is a reversible visibility toggle while editing changes actual data.
- **2026-07-23** — Client-side Delete-disabled precheck for categories mirrors the backend's exact `ConflictError` condition (`documentCount > 0` in `taxonomy/service.py`) — same "instant feedback, backend remains authority" pattern as upload validation and review-status thresholds.
- **2026-07-23** — Tooltips on disabled buttons need the hoverable element to be a wrapping `<span tabIndex={0}>`, not the disabled `<button>` itself — disabled native elements don't reliably fire the pointer/hover events Base UI's `Tooltip.Trigger` needs. First real usage of `Tooltip` in the app to hit this; worth remembering for any future disabled-button-with-tooltip.
- **2026-07-23** — `ForbiddenState` (403) is a new shared component, not folded into `ErrorState` — a 403 is a permissions statement ("you can't be here"), semantically distinct from a 4xx/5xx failure ("something went wrong"), and future role-gated pages (Tags, Settings) will reuse it as-is.
- **2026-07-23** — Tags admin has no "New tag" button, unlike Categories' `[New]` — §6.9 only lists Rename/Merge/Delete for Tags. Tags are created implicitly through `TagInput` when a document is uploaded or edited, never directly in this admin screen; adding a manual-create path would be scope creep beyond what the doc specifies.
- **2026-07-23** — Merge-into's confirmation states the affected document count from the tag's already-known `usageCount` rather than a new backend "preview" call — the number doesn't change between opening the dialog and confirming, so a live round-trip would be unnecessary.
- **2026-07-23** — Tag-rename/merge/delete mutations invalidate the same `taxonomyKeys.tags` cache key that `TagInput` and `TagFilterCombobox` already read (built in Phases 4.4/4.3) — a rename or merge in the admin screen is reflected in those pickers for free, no extra invalidation wiring needed.
- **2026-07-23** — `GET`/`PATCH /auth/me/preferences` added to the existing auth module rather than a new "users" module, closing a gap between the documented data model (`user_preferences`, §7), the documented UI requirement (§2.11/§6.10), and the documented API surface (§8.2), which never actually specified this endpoint. Placement follows §2.11's own "Dependencies: Auth" note.
- **2026-07-23** — Theme and default-page-size preferences are wired into real consumers, not just persisted: the topbar's `ThemeToggle` now also calls `useUpdatePreferences()` (so a theme change from either the topbar or Settings behaves identically and survives to the next login), and the Explorer's page size — hardcoded to `25` since Phase 4.3 — now reads `usePreferences().defaultPageSize`. A setting that persists but is never read by anything would be a half-finished feature.
- **2026-07-23** — A Base UI `Select`'s `value` prop must never toggle between `undefined` and a defined string across renders (triggers a real "uncontrolled → controlled" warning), but per next-themes' own documented hydration-safety requirement, theme-derived render output also can't differ between the server and the client's first paint. Resolution: keep `value` a string on every render, using the *same* placeholder string (`"system"`) before and during the mount-guard transition, rather than `undefined` before and a real value after. Two different-looking bugs (a console warning, and later a genuine hydration-mismatch error) turned out to share one root cause and one fix.
- **2026-07-23** — `GET /documents/trash` added to the existing `documents` module rather than a new `trash` module, unlike Pending Reviews (which got its own `reviews` module). Reasoning: Trash is fundamentally a status-filtered list plus the soft-delete/restore/hard-delete actions already living in `documents`, whereas Reviews introduces a genuinely separate cross-cutting query shape (`PendingReviewItem` with computed `daysOverdue`) and its own mutation (`mark_reviewed`). Frontend still gets its own `features/trash/` folder for the list query, matching the route structure — only the mutations (`restore`, `hardDelete`) are shared from `features/documents/`, since those operate on the Document resource itself.
- **2026-07-23** — The new `GET /documents/trash` route is registered in `documents/router.py` *before* `GET /documents/{document_id}`, not after. FastAPI/Starlette match routes in registration order using the raw path structure, not the parameter's declared type — a request to `/documents/trash` registered after `/documents/{document_id}` would match the dynamic route first and fail UUID parsing with a 422, never reaching the literal `/trash` route.
- **2026-07-23** — Trash listing is scoped identically to soft-delete/restore (owner sees only their own trashed documents, Admin sees every trashed document org-wide) rather than a role check — reuses the exact permission rule already established in `_assert_can_delete`, so the Restore button never needs its own client-side gating: whatever rows the scoped list returns are always ones the current user is allowed to restore.
- **2026-07-23** — `TypeToConfirmDialog` (new shared component) generalizes the existing `ConfirmDialog` for the one action in the app the architecture doc explicitly requires extra friction for — Trash's Admin-only permanent delete (§6.8: "type-to-confirm"). Every other destructive action (soft-delete, category/tag delete) uses the plain `ConfirmDialog` — this one is deliberately not the default, reserved for truly irreversible actions.
- **2026-07-23** — The shared `invalidateAfterDocumentChange()` helper (already used by mark-reviewed/soft-delete/restore/update since Phase 4.5) now also invalidates `["reviews"]` and `["trash"]` query keys. Centralizing this in one place means any future document mutation automatically keeps both queues correct, rather than requiring each new mutation hook to remember which other screens might be showing stale data as a result.
- **2026-07-23** (Phase 5) — Ran the error-handling audit as a dedicated research pass (read-only) before making any fix, rather than fixing issues as noticed while reading code ad hoc. Reasoning: §16.5's contract has 9 status rows across every mutation and error-display site in the app — a systematic pass against a fixed checklist finds the *pattern* of a gap (e.g. "422/409 fields are plumbed end-to-end but read nowhere"), which a single shared fix closes at every call site at once, versus fixing each site's symptom individually and re-deriving the same root cause five separate times.
- **2026-07-23** (Phase 5) — `applyApiFieldErrors()` (`lib/form-errors.ts`) checks the incoming field name against `Object.keys(form.getValues())` before calling `setError`, rather than calling it unconditionally. This makes it safe to use as a blanket first step in every form's `onError` — a field name the backend sends that isn't a real form field (e.g. `category_id`/`tag_id` on a delete-conflict error, which has no corresponding input in a create/edit dialog) is silently skipped rather than throwing or setting a phantom error, and the caller falls through to the normal toast for that case.
- **2026-07-23** (Phase 5) — Chose not to build a bespoke "resolution path" UI (e.g. a "rename or merge instead?" dialog) for the 409 conflict cases beyond the inline field-error mapping. Reasoning: the backend's `fields[]` message already names the exact problem, and re-opening the same still-open dialog with that field flagged already lets the user fix and resubmit without leaving the screen — a reasonable reading of §16.5's "contextual dialog with a resolution path" for a hackathon-scoped app, versus a purpose-built dialog per conflict type, which would be new construction rather than the audit-and-fix pass Phase 5 is scoped as.
- **2026-07-23** (Phase 5) — Version History's restore-conflict handling (`versions-tab.tsx`) now checks `error.status === 409` specifically (not just `error instanceof ApiError`) before showing the "someone else uploaded a new version" copy, and wires a toast action button to the tab's own `refetch()` rather than just telling the user to refresh manually — the one 409 case in the app where "refresh and see current state" is a genuinely different, more useful resolution than "look at this field."
- **2026-07-23** (Phase 5) — `frontend/src/app/not-found.tsx` and `error.tsx` reuse the existing `ErrorState`/`EmptyState` visual language (same icon-in-circle + title + description + action layout) rather than a one-off design, so an unmatched route or an uncaught exception still looks like the rest of the app instead of a jarring, unstyled fallback.
- **2026-07-24** (AI track) — Extracted text is stored on disk (`{version.storage_path}.txt`, via the existing `StoragePort`) with only a path pointer + status/metadata in Postgres (`document_extracted_text`), not the raw text content in a DB column. Reasoning: Supabase's free-tier Postgres has a real, fairly small disk quota that bulk extracted text would compete for; local disk doesn't. This mirrors — not diverges from — how `document_versions` itself already works (a `storage_path` pointer, never file bytes, in the DB). Zero new `StoragePort` methods needed; the extracted-text path is just the version's existing `storage_path` with `.txt` appended, which never collides with the source path even when the source itself is already `.txt` (`v1__notes.txt` vs `v1__notes.txt.txt` are different paths).
- **2026-07-24** (AI track) — `document_extracted_text` and `ai_jobs` are separate tables, not a column added to `document_versions`. Reasoning: `document_versions` is a strict, append-only audit record elsewhere in this codebase's own design language — bolting a `PENDING`/`FAILED` processing-status lifecycle onto it would be a category error. Extraction has its own lifecycle (pending → succeeded/failed, retryable, with an error message) that has nothing to do with what a version row represents.
- **2026-07-24** (AI track) — `app/text_extraction/` is deliberately decoupled from the DB. Its `TextExtractor` protocol and `ExtractionResult` know nothing about `ExtractionMethod`/`ExtractionStatus` (the DB-facing enums in `db/models/enums.py`) — a pure bytes-in/text-out function per format, dispatched by a small registry. This is what makes the 6-test suite possible with zero mocking: each extractor is tested against a real, in-memory fixture with no DB or FastAPI involved at all.
- **2026-07-24** (AI track) — Legacy binary Office formats (`.doc`, `.ppt`, `.xls`) are not supported by the extraction registry — no reliable pure-Python parser exists for them, and pulling in LibreOffice-headless conversion or a paid conversion API just for three extensions already in the app's upload allowlist was judged not worth the operational complexity. The registry returns `None` for them; the (planned) orchestration service maps that to `ExtractionStatus.UNSUPPORTED`, not a retried failure.
- **2026-07-24** (AI track) — Background AI processing uses a Postgres-backed job queue (`ai_jobs`, claimed via `SELECT ... FOR UPDATE SKIP LOCKED`) rather than Celery/Redis/RabbitMQ. Reasoning: this is the same row-locking pattern the codebase already uses for version-number allocation (`versions/repository.py`'s `get_document_for_update`), and this project's own established philosophy (§9.4 of the architecture doc: no infra beyond what's needed, e.g. rejecting the Supabase client SDK for portability) argues against a dedicated broker at a corpus scale measured in hundreds of documents. Revisit only if job volume genuinely outgrows a simple poll interval.
- **2026-07-24** (AI track) — `ai_jobs` is one shared queue table with a `job_type` column, not one table per processing stage. Every future AI stage (embedding, metadata suggestion) reuses the same `AiJobRepository.claim_batch`/`mark_succeeded`/`mark_failed` and the same worker's `run_once`, registering a new handler under a new `AiJobType` rather than re-deriving retry/backoff/locking logic per stage.
- **2026-07-24** (AI track) — The worker (`app/ai_jobs/worker.py`) is built but deliberately not wired into `main.py` or app startup, and has no CLI entrypoint yet. `AiJobType` currently has exactly one value (`EXTRACT`) with no registered handler — Step 5 (the extraction orchestration service) is what gives the worker something real to dispatch to and is when a runnable `python -m app.ai_jobs.worker`-style entrypoint gets added. Building an entrypoint script with an empty handler registry now would just be dead code.
- **2026-07-24** (AI track) — `TextExtractionService` lives in `app/text_extraction/service.py`, not a new `app/modules/text_extraction/` package, even though every other business-logic service in the app follows the router/service/repository module convention. Reasoning: it has no router (nothing calls it over HTTP — the worker calls it directly), so a `modules/` package would mean an empty or nonexistent `router.py` sitting next to real logic, which is more confusing than clarifying. If a management/debug endpoint for extraction status is ever added, that's the trigger to promote it into `modules/`, not before.
- **2026-07-24** (AI track) — `EXTRACT` jobs are enqueued for restored versions too, even though a restore copies bytes from an existing, already-extracted version (`versions/service.py::restore_version`). Chose uniformity (every new `document_versions` row gets exactly one job, no exceptions) over the marginal compute saved by special-casing restores to reuse a prior `document_extracted_text` row — re-running a classic parser is cheap and not an AI call, so the special-case branch wasn't worth the code it would cost.
- **2026-07-24** (AI track) — `TextExtractionService.process_job` treats a missing `DocumentVersion` (the parent document was hard-deleted between a job's enqueue and the worker claiming it) as a silent no-op, not a failure. The job's only reason to exist — a version to extract text from — is already gone; retrying or logging it as an error would be noise, not a signal anything went wrong.

### Resolved (kept for history — do not delete)

- ~~Real DB password briefly committed into `.env.example` (the tracked template file) instead of `.env`~~ — moved to gitignored `.env`, `.env.example` reverted to placeholder. Fixed 2026-07-23.
- ~~Pooler connection string had a stray `db@` merged into the hostname, breaking DNS resolution~~ — fixed 2026-07-23.
- ~~`backend/.gitignore` silently excluded `uploads/tmp/.gitkeep` and `uploads/documents/.gitkeep` (git can't un-ignore a file inside an already-ignored parent directory)~~ — fixed by also un-ignoring the parent directories explicitly. Fixed 2026-07-23.
- ~~Seed script could generate version-upload timestamps in the future relative to "today"~~ — fixed by computing `created_at` with enough backward buffer for the chosen version count. Fixed 2026-07-23.
- ~~Hard-deleting a document with a restored version (`restored_from_version_id` pointing at a version being deleted in the same batch) threw a 500 (FK violation)~~ — fixed via `ON DELETE SET NULL` migration. Fixed 2026-07-23.
- ~~User menu crashed on open (`Base UI: MenuGroupContext is missing`)~~ — `DropdownMenuLabel` needed a `DropdownMenuGroup` wrapper (Base UI is stricter than Radix here). Found via browser testing, fixed 2026-07-23.
- ~~Base UI console warning on Dashboard: `Button` rendered as a `Link` ("View all" / "Review now") expected a native `<button>`~~ — needed `nativeButton={false}` when polymorphically rendering as an `<a>`. Found via browser testing, fixed 2026-07-23.
- ~~Dashboard's `/documents?categoryId=…` and `/documents?reviewStatus=…` links 404'd because the Explorer didn't exist yet~~ — resolved by building the Explorer (Phase 4.3); those links now work exactly as designed.
- ~~Explorer's Category/Review Status/Sort selects displayed raw values (`"all"`, `"updated_at"`) instead of labels~~ — Base UI's `Select.Value` needed an explicit label-lookup render function (see Known Issues → Resolved and §9). Found via browser testing, fixed 2026-07-23.
- ~~Topbar's Upload button was a disabled placeholder~~ — resolved by building the Upload flow (Phase 4.4); it now opens a working upload dialog from anywhere in the app.
- ~~Document row/card links pointed at `/documents/{id}`, which didn't exist yet~~ — resolved by building Document Details (Phase 4.5); those links now work as designed.
- ~~**The BFF proxy crashed (500) on any 204 No Content response**~~ — the Fetch spec forbids a body (even an empty `ArrayBuffer`) on a null-body-status `Response` (204/205/304). Latent since Phase 4.1 (nothing had proxied a 204 through the generic route until `DELETE /documents/{id}` in Phase 4.5); fixed by passing `null` as the body for those statuses. Found via browser testing — the backend correctly returned 204, but the client saw a 500 — traced through the Next.js dev server's own error log.
- ~~**Downloads were assumed to need a signed/short-lived-token URL**~~ (see the entry directly below and §9) — they didn't; the real gap was two response headers the BFF proxy wasn't forwarding. Fixed 2026-07-23.
- ~~Settings' Theme `Select` triggered a Base UI "uncontrolled → controlled" warning~~ — its `value` toggled between `undefined` (pre-mount) and a string (post-mount). Found via browser testing, fixed 2026-07-23.
- ~~Removing that `mounted` guard entirely (to fix the warning above) caused a real hydration mismatch~~ — `next-themes` resolves `theme` from `localStorage` synchronously on the client's first render, differing from the server's fallback. Correct fix keeps `value` a string throughout, using `"system"` as the pre-mount placeholder instead of `undefined`. Found via browser testing (React's hydration-mismatch error, not just a console warning), fixed 2026-07-23. See §9.
- ~~`user_preferences` had no backend endpoint at all~~ — resolved by adding `GET`/`PATCH /auth/me/preferences` (Phase 4.9).

### Open

- **No automated test suite.** All backend verification so far has been manual (curl + direct DB queries); the frontend has ad hoc Playwright smoke scripts (not checked into the repo — live in the session scratchpad) rather than a real test suite. Thorough, but not regression-proof. Formal `pytest`/component-test suites are Phase 6 in the roadmap, not yet started.
- **Dashboard's "Recently Accessed" widget shows `updatedAt`, not a true "last accessed" timestamp.** `GET /dashboard/summary` returns `DocumentSummary` objects, which don't include `lastAccessedAt` (only `DocumentDetail` does, via the document-detail endpoint). Not worth a backend schema change for one dashboard widget's label right now — revisit if it's noticeably confusing in practice.
- **Upload progress reflects the browser→Next.js leg only, not Next.js→FastAPI.** The BFF proxy buffers the full response before returning it, so true end-to-end progress isn't observable from the client — acceptable on localhost where that second leg is fast; worth revisiting if the backend is ever deployed somewhere with meaningfully higher latency between the two.
- **Search doesn't cover document body text.** `search_vector` indexes title, description, tags, category name, and current filename — not the actual PDF/DOCX content (FR-22, deferred).
- **No duplicate-upload detection.** SHA-256 checksums are computed and stored per version, but nothing checks "does this content already exist?" and warns the user (FR-21, deferred).
- **PDF preview can't be visually verified in headless-Chromium Playwright testing** — the bundled headless Chromium has no active PDF-viewer plugin, so the iframe renders blank in automated screenshots even though the underlying response is a valid PDF with correct headers (verified by fetching the URL directly). Not a product bug — renders normally in every real browser — but means this one feature's visual correctness relies on the direct-fetch check rather than a screenshot, worth remembering if it's ever re-verified.
- **Testing version-history mutations (restore, upload-new-version) requires a throwaway document, not the seed corpus.** `DocumentVersion` rows are append-only with no delete endpoint, so any test upload/restore against a seeded document permanently inflates its version count and the Dashboard's `versionsTracked` total. Established pattern going forward: create a test document via Upload, test against it, hard-delete it afterward — never mutate versions on seed documents.
- **Soft-deleting a document from its own detail page (`/documents/{id}`) triggers a harmless one-off 404 on `GET /documents/{id}`.** The delete mutation's success handler invalidates `documentsKeys.detail(id)` (via `invalidateAfterDocumentChange`) before `router.push("/documents")` runs; since the query is still actively observed for that brief moment, it refetches immediately — but the document is now `DELETED`, and the detail endpoint only resolves `ACTIVE` documents, so that one refetch 404s. No visible error reaches the user (no toast, no error state renders, navigation completes normally) — found via a Playwright console listener during Trash testing, not by any visible symptom. Pre-existing since Phase 4.5 (the `documentsKeys.detail(id)` invalidation already existed before Pending Reviews/Trash added `["reviews"]`/`["trash"]` alongside it); not introduced by this phase. Low priority — would need reordering the navigation before the invalidation, or excluding the detail key from invalidation on delete specifically.
- **`DownloadLink` (a plain `<a href download>`, not routed through `apiClient`) bypasses the 401→redirect contract entirely.** If a session expires while a document detail/versions page is open, clicking Download attempts to download the BFF proxy's raw JSON error envelope instead of the file, with no redirect to `/login`. Found during the Phase 5 error-handling audit. Not fixed: converting it to a fetch-and-blob download would lose the browser's native streaming-download behavior for large files and needs its own design pass, not a quick patch. Low traffic in practice — requires the token to expire in the exact window between page load and the download click.
- **`correlationId` is included on every `ErrorState` (page/query-level errors) but not on any mutation-triggered toast.** `ApiError.correlationId` is always populated; `ErrorState` sites were brought into consistency in Phase 5, but the ~15 `toast.error()` call sites across the app's mutations were deliberately left alone — threading a correlation ref through every one of them for the 500 case specifically (the only status where it's genuinely useful — 400/403/404/409/422 already show a clear message) is a broad mechanical change better scoped as its own pass than folded into this one.
- **The server-rejected case of a 413/415 upload (e.g. a magic-byte mismatch the client-side check can't catch) shows the backend's message as a toast, not the same inline/allowlist treatment used for the client-caught version of the identical error.** The message itself is still clear and specific (e.g. "This file's content doesn't match its extension.") — just delivered differently (transient toast vs. persistent inline text) than the pre-upload case one code path earlier. Found during the Phase 5 audit, judged not worth the added complexity of reusing the dropzone's inline-error state from inside a mutation's `onError`.
- **Two low-likelihood 409 races were left with generic-toast handling rather than dedicated resolution UI**: renaming a tag to a name that collides with an existing tag (arguably should offer "merge instead?"), and deleting a category/tag in the same instant someone else starts using it (already prevented in the common case by the client-side disabled+tooltip precheck, so this only fires on a genuine race). Found during the Phase 5 audit; judged edge-case enough not to justify bespoke UI in an audit pass — see §9 for the reasoning applied to 409s generally.

---

## 11. Next Immediate Tasks

**Phase 4 (Frontend), Pending Reviews/Trash (S6/S8), and Phase 5 (Integration) are all complete.** Every screen in the architecture doc's §6 screen plan exists, the canonical J2 flow (§4.3) works end-to-end without touching a terminal, and error handling was audited and brought into consistency against §16.5 across every screen (see §3 and §9; residual, deliberately-deferred gaps are in §10 Known Issues → Open).

What's left, per the roadmap (§19):

1. Phase 6 (Testing) — automated `pytest` suite (backend), one integration test for the full upload→version→search→download loop, a scripted demo walkthrough exercising each of the six pains from the original brief in order (§19.7). This is the only major phase remaining before Deployment.

Ask before starting, per standing practice, but there's no longer a choice between candidates — Phase 6 is what's next.

---

## 12. Future Enhancements

*(Explicitly postponed — Phase 2+, not designed yet. See architecture doc §20 for the full rationale on why each is additive and doesn't require reworking Phase 1.)*

- AI metadata extraction (auto-suggest category/tags)
- Document summarization
- AI / semantic search (vector similarity alongside full-text)
- Vector database (likely `pgvector` inside the same Supabase instance)
- Conversational chat with documents (RAG)
- Real notification delivery (email/in-app) for review reminders — currently only the data + visibility half is built
- Approval workflows / formal document states (Draft → In Review → Approved → Retired)
- Granular ACLs, sharing links, external guest access
- Cloud object storage (S3/MinIO) — the `StoragePort` abstraction already makes this a single-adapter swap
- Full role & permission administration UI
- SSO / OIDC / SAML
- Multi-tenancy, retention policies, legal hold

---

## 13. Change Log

*(Reverse chronological. Never delete history — always append.)*

### 2026-07-24

- Wired the **text extraction foundation live end-to-end** — the increment immediately after the one below. Built `TextExtractionService.process_job` (`app/text_extraction/service.py`), the `AiJobType.EXTRACT` handler that ties the pure extractors, `StoragePort`, and `document_extracted_text` together: loads the version, dispatches via the registry, extracts, writes the `.txt` sibling, upserts the DB row — with a missing version (hard-deleted mid-queue) treated as a no-op, and an unsupported extension marked `UNSUPPORTED` rather than retried. Wired the enqueue hook into all three places a new `document_versions` row gets created (`documents/service.py::create_document`, `versions/service.py::upload_version` and `::restore_version`) — one additional `AiJob` insert next to each existing `ActivityEvent` insert, in the same transaction, purely additive to otherwise-untouched code. Extended `hard_delete`'s existing storage-cleanup loop to also remove each version's `.txt` sibling (the DB rows already cascade for free via FK `ondelete`). Added `app/ai_jobs/main.py`, the worker's first real runnable entrypoint. Verified fully live, not just unit tests: uploaded a real throwaway document via the actual running API, confirmed a job auto-enqueued, ran the worker, confirmed the `document_extracted_text` row and the `.txt` file's content matched exactly, then soft-deleted and hard-deleted the document and confirmed both files and both DB rows were gone. `mypy`/`ruff`/`pytest` all clean. Nothing Gemini-related or user-facing yet — that's the next increment.
- Started the **AI feature track** — "Smart Rename & Auto-Tag," planned and scoped separately from the §19 hackathon roadmap (published as its own phased rollout plan: shadow mode first, `app/ai/` provider-abstraction architecture mirroring `StoragePort`, Postgres job queue, prompt/token strategy, UX). First coded increment: the **text extraction foundation** — deliberately built before any Gemini integration, since extraction has no external API dependency and no subjective quality gate, making it the one safe-to-build-for-real piece with nothing user-facing yet. Added two new tables (`document_extracted_text`: a pointer + status/metadata only, never the text content; `ai_jobs`: a shared background-work queue reusable by every future AI stage), both cascade-deleted from `document_versions`. Extracted text is stored on disk as a `.txt` sibling of the source file via the existing `StoragePort` — zero new storage methods needed — deliberately not as a Postgres text column, both to mirror how `document_versions` itself never stores file bytes in the DB and because Supabase's free-tier disk quota is a real constraint bulk text would compete for. Built `app/text_extraction/` — five pure, DB-decoupled extractors (pdf/docx/xlsx/pptx/plain via `pypdf`/`python-docx`/`openpyxl`/`python-pptx`) dispatched through a small registry; legacy binary Office formats (`.doc`, `.ppt`, `.xls`) are explicitly unsupported, no reliable pure-Python parser exists for them. Built `app/ai_jobs/` — `AiJobRepository` (claim via `SELECT ... FOR UPDATE SKIP LOCKED`, the same row-locking pattern already used for version-number allocation; exponential backoff capped at 5 attempts) and a generic `worker.py` (`run_once`/`run_forever` over a pluggable `job_type → handler` registry) — chosen over Celery/Redis as a deliberately lighter-weight fit for this project's corpus scale and existing "no infra we don't need" philosophy. Wrote **the first pytest suite in this project** (`tests/text_extraction/`, 6 tests, `tests/` had been empty since Phase 2) — each extractor tested against a real in-memory fixture built with that format's own writer library, no committed binary fixtures and no mocking needed given the pure-function design. Added `[tool.pytest.ini_options]` (first test needing to import `app.*`) and `types-openpyxl` (closed the one new mypy stub gap). `mypy`/`ruff` both clean on all new code; migration applied and table shapes confirmed directly against the live DB; the running dev server, model registration, and registry dispatch all re-verified with a live smoke check. **Deliberately deferred, not forgotten:** the orchestration service that actually wires registry → extractor → `StoragePort` → DB row together, the enqueue hook into the existing upload/new-version transactions, hard-delete cleanup for the `.txt` sibling, and everything Gemini-related (all planned as the next increment).

### 2026-07-23

- Completed **Phase 5 (Integration, §19.6)** — an audit pass, not new construction. First verified the exit criteria directly: the canonical J2 flow (§4.3, Upload→Categorize→Search→View→Update Version→Dashboard Refresh) end-to-end through the UI with zero terminal/API touches and zero console errors. Then ran a dedicated research pass auditing every mutation and error-display site in the frontend against §16.5's documented HTTP-status contract. Findings and fixes: (1) `ApiError.fields` — fully plumbed from the backend envelope on both 422s and field-specific 409s — was read nowhere in the app; added a shared `applyApiFieldErrors()` helper and wired it into all 5 `react-hook-form` mutations, so a duplicate category/tag name now shows an inline error under the actual field in the still-open dialog instead of a disconnected toast; (2) the XHR upload path (`xhrUpload()`, used because `fetch` can't report upload progress) didn't redirect to `/login` on a 401 like every other request type — fixed; (3) a real logic bug in Version History's restore-conflict handling — the condition meant to detect a 409 was inverted, firing on network failures instead of actual conflicts — fixed, plus added a "Refresh" toast action wired to the tab's own refetch; (4) `useLogout()` had no error handling at all (silent failure) and Settings' two preference handlers (plus the topbar `ThemeToggle`'s equivalent, found outside the audit's original scope) hardcoded generic strings instead of the `error.message` pattern used correctly everywhere else — all three fixed for consistency; (5) `ErrorState`'s `correlationId` prop was only passed at 4 of 10 call sites — now all 10; (6) no `not-found.tsx`/`error.tsx` existed anywhere, so an unmatched route or uncaught exception fell through to Next's unstyled defaults — added both, reusing the app's existing error-state visual language and §6.10's exact copy. A handful of lower-value findings (a `DownloadLink` 401 edge case, correlation IDs on mutation toasts specifically, two low-likelihood 409 races) were deliberately left for later — see §10 for what and why. Verified with headless-Chromium Playwright: inline field errors confirmed for duplicate category/tag names (dialog stays open, no redundant toast, underlying data never actually mutated), the new styled 404 page, and regression checks confirming normal category-create and normal upload still succeed unaffected. TypeScript, ESLint, and `next build` all clean.
- Completed **Pending Reviews UI + Trash UI (§6.7/§6.8, screens S6/S8)** — the two documented screens that sat outside the strict 4.1–4.9 module order; every screen in the architecture doc's §6 plan now exists. Found and fixed a backend gap before implementing: there was no way to list trashed documents at all (`GET /documents` hardcodes `status=ACTIVE`, and §8.3 never specified a Trash-listing route). Added `GET /api/v1/documents/trash` to the existing `documents` module, scoped identically to the already-existing soft-delete/restore/hard-delete endpoints (owner sees their own trashed documents; Admin sees all), plus a `Document.deleted_by_user` relationship so the response can show who deleted each document. `/reviews` (Reviewer/Admin-only, 403 otherwise) reuses the already-built `GET /reviews/pending` and the existing `MarkReviewedDialog` from Document Details — only the frontend feature wiring and page were new. `/trash` (all users, no client-side role gate — scoping is server-side) adds a new `TypeToConfirmDialog` shared component for the Admin-only permanent-delete action, since the architecture doc specifically requires type-to-confirm there and nowhere else in the app. Wired `documentsApi.hardDelete()` (the one document CRUD action with no frontend caller until now) and extended the shared `invalidateAfterDocumentChange()` helper to also invalidate the reviews/trash query keys, so any document mutation keeps both queues correct automatically. Verified end-to-end with headless-Chromium Playwright: the Reviews queue against real seed data (marked a document reviewed, confirmed the row count dropped and the row disappeared, confirmed Employee-role 403), and the full Trash lifecycle against a throwaway document (soft-delete → owner-scoped visibility → restore → re-delete → Admin org-wide visibility → type-to-confirm gating (disabled empty, disabled on wrong text, enabled only on an exact match) → permanent delete → empty Trash). One leftover throwaway document from an earlier failed test iteration (a Playwright selector bug, since fixed) was found via a direct API count check and cleaned up; document/Trash/category counts confirmed back at their documented baselines afterward. TypeScript, ESLint, and `next build` all clean.
- Completed **Phase 4.9 (Settings) — Phase 4 (Frontend) is now fully complete.** Found and fixed an architectural gap before implementing: `user_preferences` existed in the schema and the seed data, and §2.11/§6.10 scoped Settings around it with "Dependencies: Auth," but §8.2's documented API surface never actually exposed it — added `GET`/`PATCH /auth/me/preferences` to the existing auth module. Built `/settings` (no role gate — personal, not admin-only): a read-only profile card and a preferences card. Both preferences are wired into real consumers rather than just stored: the topbar's `ThemeToggle` now also persists via `useUpdatePreferences()` alongside `next-themes`, and the Explorer's page size (hardcoded to 25 since Phase 4.3) now reads `usePreferences().defaultPageSize`. Found and fixed two related real bugs via browser testing in the same component: a Base UI "uncontrolled → controlled" `Select` warning, and — after a first fix attempt removed the guard causing that warning — a genuine hydration mismatch, since `next-themes` resolves `theme` from `localStorage` synchronously on the client's first render. Both share one root cause (the `Select`'s `value` must stay a string throughout, never `undefined`) and one fix. Verified end-to-end with headless-Chromium Playwright as an Employee persona: profile display, theme change with cross-reload persistence, page-size change actually reflected in the Explorer's results, and correct non-Admin access (no 403, unlike Categories/Tags). Both preferences restored to their seeded baseline afterward. TypeScript, ESLint, and `next build` all clean. Every screen from architecture doc §6 (S1–S10) is now built and verified in a real browser.
- Completed **Phase 4.8 (Tags Admin)** — `/admin/tags` per §6.9: table sorted by usage (backend already returns `usage_count desc, name asc`), Rename via `RenameTagDialog`, Merge-into via `MergeTagDialog` (confirmation states the affected document count from the tag's already-known `usageCount`, no new backend call needed), and Delete disabled-with-tooltip while `usageCount > 0` — reusing the exact precheck/tooltip/`ForbiddenState` patterns established in Categories (4.7) rather than re-deriving them. No "New tag" button, since §6.9 doesn't list one for Tags — they're created implicitly through `TagInput`. `tagsApi` grew rename/merge/delete (was list-only); mutations invalidate the same cache key `TagInput`/`TagFilterCombobox` already read, so those pickers see changes for free. This completes every module through S9 in the original screen plan — only Settings (S10, Phase 4.9) remains in Phase 4. Verified end-to-end with headless-Chromium Playwright using two throwaway tags on a throwaway document (never the seed vocabulary): rename, merge (toast correctly reported "1 document(s) updated," confirming the backend's already-tagged dedup logic, not a naive double-insert), delete-blocked-with-tooltip, freed the tag to usage=0 and confirmed delete then succeeded, and 403 for a non-Admin persona. Tag count (30) and document count (53) both confirmed back at their documented baselines after cleanup. TypeScript, ESLint, and `next build` all clean.
- Completed **Phase 4.7 (Categories Admin)** — `/admin/categories` per §6.9: table (name, description, usage count, status), New/Edit via a shared `CategoryFormDialog`, one-click Archive/Unarchive as a separate action from Edit, and Delete disabled-with-tooltip while `documentCount > 0` (client-side precheck mirrors the backend's exact `ConflictError` condition). Built the app's first 403 state (`ForbiddenState`, new shared component, per §6.10's exact copy) since `/admin/categories` is reachable directly by URL even though the sidebar already hides its nav link from non-Admins. `categoriesApi` grew create/update/delete (was list-only since Phase 4.3); `useCategories()` gained an `includeArchived` param defaulting to `false` so the Explorer's existing filter dropdown is unaffected. Found one real cross-browser quirk along the way: a disabled `<button>` doesn't reliably fire the hover events `Tooltip.Trigger` needs, so the trigger has to be a wrapping `<span tabIndex={0}>` instead — the app's first real `Tooltip` usage to hit this. Verified end-to-end with headless-Chromium Playwright: create/edit/archive/unarchive/delete on a throwaway category, delete-blocked tooltip confirmed on a real in-use seed category, and 403 for a non-Admin persona with the sidebar correctly showing no Categories link at all. Category count confirmed back at the documented baseline (12) after cleanup. TypeScript, ESLint, and `next build` all clean.
- Completed **Phase 4.6 (Version History)** — the two actions deliberately deferred from Phase 4.5: "Upload new version" added to the header's action bar (dropzone + required change note + determinate progress bar, lazy-loaded dialog) and "Restore this version" on every non-current Versions-tab row (reusing `ConfirmDialog`, confirmation names both version numbers per §6.6). Factored a shared `xhrUpload<T>()` helper out of the now-two call sites needing XMLHttpRequest-for-progress. This closes out Document Details / Version History (S5–S6) as originally scoped. Verified end-to-end with headless-Chromium Playwright against a throwaway test document — never the seed corpus, since `DocumentVersion` rows are append-only with no delete endpoint and would permanently inflate the seed's version counts: upload-new-version, restore, Current-badge/Restore-button visibility at every step, both activity events, and Employee-role gating. Confirmed the seed corpus's documented baseline (53 documents, 99 versions) was unaffected after cleanup. TypeScript, ESLint, and `next build` all clean.
- Completed **Phase 4.5 (Document Details)** — header/role-gated action bar, Overview tab with inline edit mode (reusing `TagInput` from Upload), a read-only Versions tab, an Activity tab, PDF/image/text preview, mark-as-reviewed, and delete-with-undo. Found and fixed two real architectural gaps before implementing: (1) corrected an earlier assumption that downloads needed a signed-URL scheme — they don't, the BFF proxy's cookie-to-Bearer translation already covers plain links; the actual fix was forwarding `Content-Disposition`/`X-Content-Type-Options` through the generic proxy, which it was silently dropping; (2) added an optional `documentId` filter to the existing `GET /dashboard/activity` endpoint for the Activity tab, reusing the schema rather than adding a new route. Also found and fixed a **real, previously-latent bug via browser testing**: the BFF proxy crashed with a 500 on any 204 No Content response (the Fetch spec forbids a body on null-body-status Responses) — `DELETE /documents/{id}` was the first 204 this proxy ever had to forward, so the bug had been dormant since Phase 4.1. Verified end-to-end with headless-Chromium Playwright: view→edit→save, mark-as-reviewed, versions table, activity feed (including the test's own trash/restore cycle, proving the audit trail is genuine), a 404 state, soft-delete→redirect→toast→Undo→restored, and Employee-role gating. PDF preview correctness was confirmed by fetching the content URL directly (valid 5-page PDF, correct headers) rather than a screenshot, since headless Chromium has no PDF-viewer plugin — not a product bug. TypeScript, ESLint, and `next build` all clean.
- Completed **Phase 4.4 (Upload Document)** — a single unified upload modal per architecture doc §6.3 (correcting my own earlier "two-step stepper" mischaracterization), built from a new `UploadDropzone` (shared) and `TagInput` (creatable, distinct from the Explorer's filter-only `TagFilterCombobox`). `documentsApi.create()` uses `XMLHttpRequest` for a real determinate progress bar (`fetch` can't observe upload progress). Non-dismissible mid-upload via a single `onOpenChange` guard that covers Escape/outside-click/close-button/Cancel uniformly. Client-side extension/size pre-validation mirrors the backend's `core/config.py` defaults. Topbar's Upload button is now fully wired (both topbar buttons — search and upload — are live as of this phase). Verified end-to-end with headless-Chromium Playwright using a real file upload: validation-disabled submit button, auto-filled title, category selection, tag creation (existing + brand-new), progress bar, success toast, dialog auto-close, the new document appearing in the Explorer and the Dashboard's activity feed (cache invalidation confirmed, not assumed), and a rejected unsupported file type — zero console errors. Test artifacts deleted afterward via the API so the seed corpus stays at its documented 53-document baseline. TypeScript, ESLint, and `next build` all clean.
- Completed **Phase 4.3 (Document Explorer)** — `documentsApi` + `taxonomyApi` feature modules, URL-driven filter state (search/category/review-status/tags/sort/page — the same query params the Dashboard already links to), a debounced `SearchBox` and `PaginationBar` (new shared components), a `TagFilterCombobox`, a desktop `DocumentsTable` collapsing to a mobile stacked list below `lg`, and the topbar's search box wired up for real. Verified end-to-end with headless-Chromium Playwright: filters, pagination, row navigation, empty state for a nonsense query, and mobile layout — zero console errors except the expected 404 from clicking into `/documents/{id}` (Phase 4.5, not yet built). Found and fixed one real Base UI gotcha along the way — `Select.Value` needs an explicit label-lookup render function; it doesn't auto-derive labels from `SelectItem` children like Radix does. TypeScript, ESLint, and `next build` all clean.
- Completed **Phase 4.2 (Dashboard)** — `dashboardApi` feature module, KPI section, role-gated Pending Reviews banner, Documents by Category bar chart, Recently Added / Recently Accessed / Expiring Soon (one generic `DocumentListCard`, not three duplicates), and a Recent Activity feed, all consuming the live `GET /dashboard/summary` and `GET /dashboard/activity` endpoints. New shared types (`src/types/document.ts`) and shared components (`KpiCard`, `DocumentListItem`, `ActivityFeedItem`) built for reuse by the Explorer and Document Details phases. Verified end-to-end with headless-Chromium Playwright scripts across an Admin persona (all widgets + banner visible) and an Employee persona (banner and admin-only nav correctly hidden), plus dark mode, tablet, and mobile viewports — zero console errors after fixing one real Base UI warning (`nativeButton={false}` needed when rendering `Button` as a `Link`). TypeScript, ESLint, and `next build` all clean.
- Completed **Phase 4.1 (Application Shell)** — design tokens (from-scratch enterprise palette + a fixed font-loading bug), API layer foundation, BFF proxy, auth guard, login page, reusable component library, and the full sidebar/topbar shell. Verified end-to-end with a real headless-Chromium Playwright script (10-step flow, screenshots, console-error check) — not just code review. Found and fixed one real bug along the way (`DropdownMenuLabel` needing a `DropdownMenuGroup` wrapper under Base UI). TypeScript, ESLint, and `next build` all clean.
- Converted the entire backend API to camelCase JSON (was snake_case, doc specifies camelCase) — new `CamelModel` schema base + aliased query/form params across all 6 modules. Re-verified all 12 endpoint categories end-to-end with the new wire format, including nested objects, list filters, multipart form fields, and validation-error field names.
- Created `PROJECT_STATUS.md` as the project's single source of truth.
- Cleaned up two leftover zero-usage test tags (`smoke`, `curl-test`) from earlier manual API testing.
- Switched `get_current_user` to a proper `HTTPBearer` security scheme so Swagger UI's `/docs` shows a single global "Authorize" button.
- Built and verified the **Reviews module** (pending queue, mark-reviewed) and **Dashboard module** (summary aggregate, activity feed) end-to-end against the real seeded corpus.
- Built and verified the **Taxonomy module** (categories CRUD + archive, tags list/rename/merge/delete) — specifically stress-tested tag merge against a real 4-document tag-overlap case.
- Built and verified the **Documents + Versions modules** — full upload/list/search/detail/patch/delete/restore/version-upload/download/version-restore flow, with real file uploads and byte-for-byte content checks. Found and fixed a real FK bug (`restored_from_version_id` needed `ON DELETE SET NULL`).
- Built and verified the **Auth module** — mock login, real JWT, `get_current_user`/`require_role` dependencies, domain exception hierarchy, correlation-ID middleware.
- Completed **Phase 2 (Database)** — SQLAlchemy models, initial Alembic migration (tables, indexes, 4 triggers), seed script (fixed a future-dated-rows bug along the way).
- Completed **Phase 1 (Setup)** — backend (`uv` + FastAPI) and frontend (Next.js + Tailwind + shadcn) scaffolded, Supabase pooler connection established and verified (fixed a leaked-credential and a hostname-typo issue along the way).

---

## Important Rules

1. This file is the single source of truth for the project.
2. Every significant change to the project must also update this file.
3. Never remove completed work.
4. Never overwrite the changelog — always append.
5. Keep completion percentages / checkboxes updated.
6. Keep TODO items (§11) synchronized with the actual codebase.
7. If architecture changes, update both §9 (Technical Decisions) and §2 (Current Status).
8. This document should always allow a new developer to understand the entire project within 5 minutes.
9. Before finishing any future development task, always check whether this file needs updating — and update it.
