# DocBrain

DocBrain is an AI-powered document management platform. Teams upload, version, categorize, and search their documents through a clean web app — and Gemini automatically suggests a better title, relevant tags, and a summary for every document uploaded, which users can accept or dismiss with one click.

Built for the Ahmedabad AI Hackathon.

## Features

- **Document Upload** — drag-and-drop upload with metadata (title, category, description, tags, review date)
- **Version Management** — full version history per document, upload new versions, restore any previous version
- **Categories** — organize documents into a managed category taxonomy
- **Tags** — flexible tagging with autocomplete, merge, and rename
- **🧠 AI Smart Rename** — Gemini suggests a clearer document title based on its actual content
- **🏷 AI Smart Tag Suggestions** — Gemini suggests relevant tags, applied without duplicating existing ones
- **📄 AI Document Summary** — a concise, auto-generated summary of what the document contains
- **Search** — full-text search across titles, descriptions, tags, and categories
- **Dashboard** — at-a-glance KPIs, recent activity, category breakdown, and review reminders

## Tech Stack

**Frontend** — Next.js 16 (App Router) · TypeScript · Tailwind CSS v4 · shadcn/ui · TanStack Query · React Hook Form + Zod

**Backend** — Python 3.11+ · FastAPI · SQLAlchemy 2.0 · Alembic · managed with [`uv`](https://docs.astral.sh/uv/)

**Database** — Supabase (hosted Postgres), accessed directly via SQLAlchemy

**AI** — Google Gemini (`gemini-flash-latest`), called through a small provider abstraction (`app/ai/`) with strict Pydantic-validated structured output

## Prerequisites

- **Node.js** 20 or later
- **Python** 3.11 or later
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** — Python package/venv manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **libmagic** — a system library the backend uses to detect file types on upload. It's a separate C library, not something `uv sync`/`pip` can install for you:
  - **macOS**: `brew install libmagic`
  - **Ubuntu / Debian**: `sudo apt update && sudo apt install libmagic1 libmagic-dev`
  - **Windows**: `pip install python-magic-bin` (installs a bundled libmagic — do this *instead of* the system-library step, no separate download needed)
  - Without this, the backend fails to start at all (not just file uploads) — `app/utils/file_validation.py` imports it at module load time.
- **A Supabase project** (free tier is enough) — you'll need its Postgres connection string
- **A Gemini API key** — free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

## Quick Start (recommended)

Clone the repo, then run one command:

```bash
git clone <repo-url> DocBrain
cd DocBrain

./start.sh        # macOS / Linux
start.bat         # Windows (or just double-click it)
```

That's it. On the very first run it asks you to paste in two things — a **Supabase `DATABASE_URL`** and a **Gemini API key** — then saves them and never asks again. Every time after that (and immediately after the first), it automatically installs dependencies, applies database migrations, seeds demo data (first run only), starts the API + AI worker + frontend together, and opens **http://localhost:3000** in your browser.

Press `Ctrl+C` in that terminal to stop everything cleanly.

> Needs Node.js, Python, `uv`, and libmagic already installed — see [Prerequisites](#prerequisites) below. The script checks for these and tells you exactly what's missing if not.

If you'd rather run each piece yourself (or the quick-start script doesn't work in your environment), the full manual steps are below.

## Manual Setup

### 1. Clone the repository

```bash
git clone <repo-url> DocBrain
cd DocBrain
```

### 2. Backend setup

```bash
cd backend
uv sync
```

This creates a `.venv` and installs every dependency — no `pip`/`requirements.txt` step needed.

### 3. Frontend setup

```bash
cd ../frontend
npm install
```

### 4. Configure environment variables

**`backend/.env`** (copy from `backend/.env.example`):

```env
DATABASE_URL=postgresql+psycopg://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres

JWT_SECRET=dev-only-secret-change-me
JWT_ALGORITHM=HS256
JWT_EXPIRES_MINUTES=1440

STORAGE_ROOT=uploads
MAX_UPLOAD_SIZE_MB=25
ALLOWED_EXTENSIONS=pdf,doc,docx,xls,xlsx,ppt,pptx,txt,md,csv,png,jpg

CORS_ORIGINS=http://localhost:3000

GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-flash-latest
AI_REQUEST_TIMEOUT_SECONDS=30
AI_MAX_RETRIES=3
AI_MAX_EXTRACTED_TEXT_CHARS=20000
```

**`frontend/.env`** (copy from `frontend/.env.example`):

```env
API_BASE_URL=http://localhost:8000
```

Use the Session/Transaction **pooler** connection string from your Supabase project settings, not the direct connection.

### 5. Set up the database

```bash
cd backend
uv run python -m alembic upgrade head
uv run python -m scripts.seed              # creates demo users, categories, tags, documents
uv run python -m scripts.backfill_seed_files  # writes real file content for the seeded documents
```

### 6. Run the backend

You need two backend processes running at once — the API and the AI worker:

```bash
# Terminal 1 — API server
cd backend
uv run python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 — AI worker (extraction + Gemini suggestions run here, out-of-band)
cd backend
uv run python -m app.ai_jobs.main
```

### 7. Run the frontend

```bash
# Terminal 3
cd frontend
npm run dev
```

### 8. Open the app

Go to **http://localhost:3000**. There's no signup/password — pick any seeded persona from the login screen to sign in.

## Demo Flow

```
Upload a document
        ↓
Extraction runs, then Gemini generates:
  • Smart Title
  • Smart Tags
  • AI Summary
        ↓
Open the document — the "AI Suggestions" card appears automatically
(no refresh needed; it polls for a few seconds while AI processing finishes)
        ↓
Click "Accept Title" and/or "Accept Tags"
        ↓
Changes are saved immediately
```

## Folder Structure

```
DocBrain/
├── backend/
│   ├── app/
│   │   ├── modules/          # documents, versions, taxonomy, reviews, dashboard, auth
│   │   ├── ai/                # Gemini provider, prompts, AI metadata generation
│   │   ├── text_extraction/   # PDF/DOCX/XLSX/PPTX text extraction
│   │   ├── ai_jobs/            # background job queue + worker
│   │   └── db/models/          # SQLAlchemy models
│   ├── alembic/versions/       # database migrations
│   ├── scripts/                # seed.py and one-time backfill scripts
│   └── tests/
└── frontend/
    └── src/
        ├── app/                # Next.js routes
        ├── features/            # feature-first business logic (documents, dashboard, etc.)
        └── components/          # shared UI components
```

## Deployment

DocBrain deploys as **three pieces**: the API and the AI worker (both from
`backend/Dockerfile`, same image, different start commands) and the Next.js
frontend. Postgres and file storage are already hosted on Supabase.

The browser only ever talks to the frontend, which proxies to the API
server-side — so the API needs no CORS configuration and can stay a private
service.

**Backend + worker** (Railway, Render, Fly.io — anything that runs a Dockerfile):

| | API service | Worker service |
|---|---|---|
| Root directory | `backend` | `backend` |
| Start command | *(image default)* | `python -m app.ai_jobs.main` |
| Public domain | yes | **no** — background process |

Both services need the same environment variables as `backend/.env`
(`DATABASE_URL`, `JWT_SECRET`, `GEMINI_API_KEY`, `STORAGE_PROVIDER=supabase`,
and the four `SUPABASE_STORAGE_*` values). Generate a real `JWT_SECRET` —
never deploy the placeholder from `.env.example`.

Database migrations run automatically when the API service starts. The
worker deliberately doesn't run them, so two services booting at once can't
race applying the same revision.

**Frontend** (Vercel): root directory `frontend`, with one environment
variable — `API_BASE_URL` set to the API service's public URL.

To verify the image locally before deploying:

```bash
cd backend && docker build -t docbrain-api .
docker run -p 8100:8100 -e PORT=8100 --env-file .env docbrain-api
```

## Tests

```bash
cd backend && uv run pytest
```

The API tests run against the same Postgres in `DATABASE_URL`, but each test
runs inside a transaction that is **rolled back** when it finishes — so they
exercise the real schema (full-text search triggers, cascades, enums) while
leaving the database exactly as they found it. No separate test database or
Docker setup is needed. Tests are skipped automatically if `DATABASE_URL`
isn't configured.

## Notes

- AI features run on **Google Gemini**. Without `GEMINI_API_KEY` set, everything else in the app works normally — the AI worker simply skips metadata generation and logs a warning.
- The first AI suggestion for a newly uploaded document may take a few seconds (text extraction, then a Gemini call) — the UI polls automatically and shows the suggestion as soon as it's ready.
- Unsupported/legacy formats (`.doc`, `.ppt`, `.xls`) can still be uploaded but won't get AI suggestions, since there's no reliable way to extract their text.
