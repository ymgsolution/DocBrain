# DocBrain Project Status

> **This is the single source of truth for the project.** It must be updated whenever a feature is added, modified, refactored, removed, or completed. See [Important Rules](#important-rules) at the bottom.

**Last updated:** 2026-07-23 (Phase 4.6 — Version History)

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
- 🟨 Frontend (Phase 4.1 — Application Shell — complete. Phase 4.2 — Dashboard — complete. Phase 4.3 — Document Explorer — complete. Phase 4.4 — Upload Document — complete. Phase 4.5 — Document Details — complete. Phase 4.6 — Version History — complete: restore-this-version (with the required two-version consequence dialog) and upload-new-version, closing out the Versions tab. Document Details / Version History as originally scoped (S5–S6) is now fully done. Verified end-to-end in a real browser. Phases 4.7–4.9 — Categories, Tags, Settings — not started)
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

---

## 4. Pending Features

### High Priority

- Categories admin UI (S9, Phase 4.7), next up
- Tags admin UI (S9, Phase 4.8)

### Medium Priority

- Automated backend test suite (`pytest`) — unit tests for permission checks, version allocation, search ranking; one integration test covering the full upload→version→search→download loop (roadmap Phase 6)
- Pending Reviews UI, Trash UI (S6, S8)
- Settings screen (S10)

### Low Priority

- FR-19: Naming policy per category (live filename preview at upload time)
- FR-21: Duplicate-detection warning on upload (checksum is already computed and stored — the "warn if identical content already exists" UX flow itself isn't built)
- FR-22: Content text extraction from PDF/DOCX for search (search currently covers title/description/tags/category/original-filename only, not document body text)
- FR-23: Bulk actions in the Explorer (multi-select re-tag/re-categorise/delete)
- FR-25: Starred/favourites (not in the DB schema at all yet)
- System error screens (404/403/500 pages)

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
│   │       └── e97f9d207d17_fix_restored_from_version_id_ondelete_.py
│   ├── app/
│   │   ├── main.py                 # FastAPI app, middleware, router registration
│   │   ├── core/                   # config, security (JWT), dependencies, exceptions,
│   │   │                           # error_handlers, middleware (correlation ID), logging
│   │   ├── db/
│   │   │   ├── base.py / session.py
│   │   │   └── models/             # user, category, document, document_version, tag,
│   │   │                           # activity_event, user_preference, enums
│   │   ├── schemas/                # Pydantic DTOs: auth, document, version, taxonomy,
│   │   │                           # review, dashboard, mappers.py (ORM → DTO)
│   │   ├── modules/                # package-by-feature
│   │   │   ├── auth/                (router, service, repository)
│   │   │   ├── documents/           (router, service, repository)
│   │   │   ├── versions/            (router, service, repository)
│   │   │   ├── taxonomy/            (router, service, repository)
│   │   │   ├── reviews/             (router, service, repository)
│   │   │   └── dashboard/           (router, service, repository)
│   │   ├── storage/                 # StoragePort, LocalFileSystemStorage, checksum
│   │   └── utils/                   # file_validation, slugify
│   ├── scripts/
│   │   └── seed.py
│   ├── tests/                       # empty — no automated tests yet
│   └── uploads/                     # local file storage (gitignored contents)
│       ├── tmp/
│       └── documents/{document_id}/v{n}__{slugified-filename}
│
└── frontend/
    ├── package.json / components.json
    ├── src/
    │   ├── proxy.ts                 # auth guard (Next.js 16's renamed middleware.ts)
    │   ├── app/
    │   │   ├── layout.tsx           # root layout — Theme/Query/Tooltip providers, Toaster
    │   │   ├── globals.css          # design tokens: full color palette, light+dark
    │   │   ├── (auth)/login/page.tsx
    │   │   ├── (app)/
    │   │   │   ├── layout.tsx       # sidebar + topbar shell
    │   │   │   ├── page.tsx         # dashboard (Phase 4.2 — real widgets, not a placeholder)
    │   │   │   └── documents/
    │   │   │       ├── page.tsx     # Explorer (Phase 4.3) — Suspense-wrapped (useSearchParams)
    │   │   │       └── [id]/page.tsx  # Document Details (Phase 4.5) — header, tabs, edit mode
    │   │   └── api/
    │   │       ├── auth/login/route.ts    # sets the httpOnly session cookie
    │   │       ├── auth/logout/route.ts   # clears it
    │   │       └── bff/[...path]/route.ts # cookie -> Bearer header proxy to FastAPI
    │   ├── components/
    │   │   ├── ui/                  # 23 shadcn primitives (Base UI, not Radix)
    │   │   ├── layout/              # Sidebar, Topbar, UserMenu, ThemeToggle, AppBreadcrumb, nav-items.ts
    │   │   ├── shared/               # PageHeader, EmptyState, ErrorState, ReviewStatusBadge,
    │   │   │                        # FileTypeIcon, UserAvatar, ConfirmDialog, KpiCard,
    │   │   │                        # DocumentListItem, ActivityFeedItem, SearchBox,
    │   │   │                        # PaginationBar, UploadDropzone, DownloadLink
    │   │   └── providers/           # QueryProvider, ThemeProvider
    │   ├── features/
    │   │   ├── auth/                # types.ts, api.ts, hooks.ts, components/login-form.tsx
    │   │   ├── taxonomy/            # types.ts, api.ts, hooks.ts (categories + tags, list-only —
    │   │   │                        #   full CRUD lands with the admin screens in 4.7/4.8)
    │   │   ├── documents/           # types.ts, api.ts (list/get/update/delete/restore/
    │   │   │                        #   markReviewed/listVersions/create w/ XHR progress), hooks.ts,
    │   │   │                        # components/ (DocumentFilters, DocumentsTable,
    │   │   │                        #   DocumentsMobileList, TagFilterCombobox, TagInput,
    │   │   │                        #   UploadDocumentDialog, DocumentHeader, DocumentPreview,
    │   │   │                        #   MetadataPanel, EditMetadataForm, MarkReviewedDialog,
    │   │   │                        #   VersionsTab, DocumentActivityTab)
    │   │   └── dashboard/           # types.ts, api.ts, hooks.ts,
    │   │                            # components/ (KpiSection, CategoryDistribution,
    │   │                            #   DocumentListCard, ActivityFeed, PendingReviewsBanner,
    │   │                            #   WidgetSkeleton)
    │   │                            # (remaining features' api layers get built in their own phase)
    │   ├── lib/
    │   │   ├── api-client.ts        # typed fetch wrapper + ApiError, targets /api/bff;
    │   │   │                        # getVersionContentUrl() for downloads/previews
    │   │   ├── constants.ts         # TOKEN_COOKIE, API_BASE_URL
    │   │   ├── format.ts            # getInitials(), formatRelativeTime(), getReviewStatus(),
    │   │   │                        # formatFileSize()
    │   │   ├── upload-constants.ts  # extension allowlist + size limit, mirrors backend config
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

### Tables (8)

| Table | Purpose |
|---|---|
| `users` | Seeded identities; role = EMPLOYEE / REVIEWER / ADMIN |
| `categories` | Controlled vocabulary; case-insensitive unique name, optional default review period |
| `documents` | Logical document identity; owns `search_vector`, `current_version_id`, review/trash state |
| `document_versions` | Append-only version history; unique `(document_id, version_number)` |
| `tags` / `document_tags` | Normalised tags + join table (composite PK) |
| `activity_events` | Append-only audit trail |
| `user_preferences` | Theme, page size |

### Relationships

- `users` → `documents` (owner), `document_versions` (uploader), `activity_events` (actor) — 1:N
- `categories` → `documents` — 1:N, RESTRICT (must archive, not delete, while in use)
- `documents` ↔ `document_versions` — circular reference (`current_version_id` → a version; `document_id` → parent doc), resolved via `use_alter` FK added after both tables exist
- `documents` ↔ `tags` via `document_tags` — M:N, CASCADE from either side
- `document_versions.restored_from_version_id` — self-referential, `ON DELETE SET NULL` (fixed from the default RESTRICT — see Known Issues)

### Migrations (2, both applied)

1. `d3070d18c042_initial_schema` — all 8 tables, indexes, and the 4 triggers.
2. `e97f9d207d17_fix_restored_from_version_id_ondelete_` — bug fix (see §10 Known Issues).

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

---

## 7. Backend Status

**All Phase 3 modules complete.** 20 unique routes, 24 method+path combinations, all manually verified against real Supabase data (not mocks) — real PDF uploads, byte-for-byte download checks, real permission-denial tests per role.

| Module | Router | Service | Repository | Notes |
|---|---|---|---|---|
| Auth | ✅ | ✅ | ✅ | Mock login, real JWT |
| Documents | ✅ | ✅ | ✅ | Full CRUD + Trash + hard delete |
| Versions | ✅ | ✅ | ✅ | Upload, download, restore |
| Taxonomy | ✅ | ✅ | ✅ | Categories + Tags, admin-only mutations |
| Reviews | ✅ | ✅ | ✅ | Pending queue, mark-reviewed |
| Dashboard | ✅ | ✅ | ✅ | Summary + activity feed, now with an optional `documentId` filter (added 2026-07-23 for the Details page's Activity tab) |

- **Middleware:** CORS, correlation-ID (`X-Correlation-Id` on every request/response).
- **Wire format:** camelCase JSON in and out (`app/schemas/base.py`'s `CamelModel`, plus `alias=` on non-path `Query`/`Form` params) — matches architecture doc §8 exactly. Fixed 2026-07-23; previously the implementation was snake_case despite the doc specifying camelCase. Internal Python code is unaffected (still snake_case attributes/kwargs).
- **Authentication:** JWT (HS256), `HTTPBearer` security scheme (Swagger `/docs` shows one "Authorize" button).
- **File upload:** temp-write → DB commit → atomic move protocol; extension allowlist + magic-byte MIME sniffing; 25MB cap; UUID-based storage paths (never user input).
- **File download:** no signed-URL scheme needed after all — the BFF proxy's httpOnly-cookie-to-Bearer-header translation already covers plain browser navigation (same-origin request, cookie sent automatically). Corrected an earlier assumption to the contrary; see §9/§10.
- **Versioning:** row-locked version-number allocation; append-only; restore creates a new version rather than rewriting history.
- **Search:** Postgres full-text (`tsvector` + `ts_rank_cd`), trigger-maintained, weighted title > tags > description > category/filename. **Does not** yet index document body content (PDF/DOCX text) — see Pending Features.
- **Pending for backend:** automated test suite (Phase 6).

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
| Responsive Design | ✅ Verified for the shell, Dashboard, Explorer, Upload dialog, and Document Details / Version History |

**What exists:** Next.js 16 (App Router, Turbopack) + TypeScript + Tailwind v4 + shadcn/ui (Base UI primitives) + TanStack Query + React Hook Form + Zod + next-themes, fully wired: design tokens, API layer, BFF proxy, auth guard, login, app shell, a live Dashboard, a live Document Explorer, a live Upload flow, and a live Document Details + Version History page all working end-to-end — verified with headless-Chromium Playwright scripts (shell: 10-step flow; dashboard: full-content check across Admin/Employee personas, dark mode, tablet, mobile; Explorer: filters, pagination, row navigation, empty state, mobile layout; Upload: a real file upload through the full form, progress bar, success toast, cache invalidation; Details: view/edit/save, mark-as-reviewed, activity, 404, soft-delete-with-undo, role-gating; Version History: upload-new-version, restore-this-version, both against a throwaway test document to avoid corrupting the seed corpus's version counts), not just code review. Production build (`next build`) succeeds cleanly; TypeScript and ESLint are both clean.

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

---

## 10. Known Issues

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

### Open

- **No automated test suite.** All backend verification so far has been manual (curl + direct DB queries); the frontend has ad hoc Playwright smoke scripts (not checked into the repo — live in the session scratchpad) rather than a real test suite. Thorough, but not regression-proof. Formal `pytest`/component-test suites are Phase 6 in the roadmap, not yet started.
- **Dashboard's "Recently Accessed" widget shows `updatedAt`, not a true "last accessed" timestamp.** `GET /dashboard/summary` returns `DocumentSummary` objects, which don't include `lastAccessedAt` (only `DocumentDetail` does, via the document-detail endpoint). Not worth a backend schema change for one dashboard widget's label right now — revisit if it's noticeably confusing in practice.
- **Upload progress reflects the browser→Next.js leg only, not Next.js→FastAPI.** The BFF proxy buffers the full response before returning it, so true end-to-end progress isn't observable from the client — acceptable on localhost where that second leg is fast; worth revisiting if the backend is ever deployed somewhere with meaningfully higher latency between the two.
- **Search doesn't cover document body text.** `search_vector` indexes title, description, tags, category name, and current filename — not the actual PDF/DOCX content (FR-22, deferred).
- **No duplicate-upload detection.** SHA-256 checksums are computed and stored per version, but nothing checks "does this content already exist?" and warns the user (FR-21, deferred).
- **PDF preview can't be visually verified in headless-Chromium Playwright testing** — the bundled headless Chromium has no active PDF-viewer plugin, so the iframe renders blank in automated screenshots even though the underlying response is a valid PDF with correct headers (verified by fetching the URL directly). Not a product bug — renders normally in every real browser — but means this one feature's visual correctness relies on the direct-fetch check rather than a screenshot, worth remembering if it's ever re-verified.
- **Testing version-history mutations (restore, upload-new-version) requires a throwaway document, not the seed corpus.** `DocumentVersion` rows are append-only with no delete endpoint, so any test upload/restore against a seeded document permanently inflates its version count and the Dashboard's `versionsTracked` total. Established pattern going forward: create a test document via Upload, test against it, hard-delete it afterward — never mutate versions on seed documents.

---

## 11. Next Immediate Tasks

1. Build the Categories admin screen (S9, Phase 4.7), next up — table (name, description, usage count, status), New/Edit/Archive, Delete disabled with a tooltip while in use. `taxonomyApi.categories` list already exists from the Explorer's filter dropdown; this phase adds the create/update/archive mutations.
2. Build the Tags admin screen (S9, Phase 4.8) — table sorted by usage, Rename, Merge-into (dialog stating how many documents are affected), Delete only at usage = 0.

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

### 2026-07-23

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
