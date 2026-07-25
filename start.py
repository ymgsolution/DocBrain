#!/usr/bin/env python3
"""One-command setup + run for DocBrain — for judges/reviewers running this
on a laptop that has never seen this project before.

What it does, in order:
  1. Checks that Node.js, npm, and uv are installed (won't try to install
     them itself — that's a one-time, documented prerequisite, see README).
  2. First run only: creates backend/.env and frontend/.env from their
     .env.example templates, prompting once for the two values only you can
     provide (a Supabase DATABASE_URL and a GEMINI_API_KEY). Never asks
     again once backend/.env exists.
  3. Installs dependencies (uv sync, npm install), then checks libmagic (a
     system library, not something uv/pip can install) actually works —
     fails fast with a platform-specific fix instead of a confusing crash
     later.
  4. Applies database migrations.
  5. First run only: seeds demo data.
  6. Frees ports 8000/3000 if anything's still listening on them — almost
     always a leftover process from a previous run that didn't shut down
     cleanly — instead of failing with "address already in use".
  7. Starts the API, the AI background worker, and the frontend dev server
     together, and opens your browser once they're up.

Usage:  python3 start.py   (or: ./start.sh / start.bat)
Stop:   Ctrl+C — shuts down all three processes together.
"""

import platform
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
IS_WINDOWS = platform.system() == "Windows"
APP_PORTS = {8000: "backend API", 3000: "frontend"}


def npm_cmd() -> str:
    return "npm.cmd" if IS_WINDOWS else "npm"


def die(message: str) -> None:
    print(f"\n✗ {message}\n")
    sys.exit(1)


def check_prerequisites() -> None:
    missing = []
    if shutil.which("node") is None:
        missing.append("Node.js 20+  →  https://nodejs.org")
    if shutil.which(npm_cmd()) is None:
        missing.append("npm (comes with Node.js)")
    if shutil.which("uv") is None:
        missing.append("uv  →  curl -LsSf https://astral.sh/uv/install.sh | sh")
    if missing:
        print("Missing required tools:\n")
        for m in missing:
            print(f"  - {m}")
        die("Install the above, then re-run this script.")


def check_libmagic() -> None:
    """python-magic (a backend dependency) wraps the *system* libmagic C
    library — installing the Python package (uv sync, just above) does not
    install libmagic itself. Without it, the backend fails at startup, not
    just on upload, because app/utils/file_validation.py imports it at
    module load time. Checked here, right after uv sync gives us a venv to
    check from, so this fails fast with a clear fix instead of a confusing
    crash several steps later."""
    result = subprocess.run(
        ["uv", "run", "python", "-c", "import magic"], cwd=BACKEND, capture_output=True
    )
    if result.returncode == 0:
        return

    print("\nMissing system library: libmagic (used to detect file types on upload)\n")
    if IS_WINDOWS:
        print("  Fix:  pip install python-magic-bin")
    elif platform.system() == "Darwin":
        print("  Fix:  brew install libmagic")
    else:
        print("  Fix:  sudo apt update && sudo apt install libmagic1 libmagic-dev")
    die("Install the above, then re-run this script.")


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _pids_on_port(port: int) -> list[str]:
    if IS_WINDOWS:
        result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
        pids = set()
        for line in result.stdout.splitlines():
            if f":{port} " in line and "LISTENING" in line:
                pids.add(line.split()[-1])
        return list(pids)

    result = subprocess.run(["lsof", "-ti", f"tcp:{port}"], capture_output=True, text=True)
    return [pid for pid in result.stdout.split() if pid]


def free_ports() -> None:
    """Kills whatever's already listening on the ports this app needs —
    almost always a leftover process from a previous run that didn't shut
    down cleanly (a crash, a closed terminal, Ctrl+C not fully finishing) —
    so a stale process never blocks a fresh run with 'address already in
    use'. Best-effort: if the platform tool to find/kill it isn't available
    (e.g. no lsof), this just leaves the original error to surface later
    with its own clear message, rather than failing here."""
    for port, label in APP_PORTS.items():
        if not _port_in_use(port):
            continue
        print(f"▸ Port {port} ({label}) is already in use — stopping the existing process ...")
        try:
            pids = _pids_on_port(port)
        except FileNotFoundError:
            print(f"  Couldn't check port {port} automatically (missing 'netstat'/'lsof') — continuing anyway.")
            continue
        for pid in pids:
            subprocess.run(
                ["taskkill", "/F", "/PID", pid] if IS_WINDOWS else ["kill", "-9", pid],
                capture_output=True,
            )
        time.sleep(0.5)
        if _port_in_use(port):
            print(f"  Couldn't free port {port} automatically — you may need to close it yourself.")


def run(cmd: list[str], cwd: Path, label: str) -> None:
    print(f"\n▸ {label} ...")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        die(f"'{' '.join(cmd)}' failed (exit {result.returncode}) — see output above.")


def prompt(label: str, hint: str) -> str:
    print(f"\n{label}")
    print(f"  {hint}")
    value = input("  > ").strip()
    while not value:
        value = input("  (required) > ").strip()
    return value


def first_time_env_setup() -> bool:
    backend_env = BACKEND / ".env"
    frontend_env = FRONTEND / ".env"
    first_time = not backend_env.exists()

    if first_time:
        print("=" * 60)
        print("First run — one-time setup (saved locally, never re-asked)")
        print("=" * 60)
        database_url = prompt(
            "1) Supabase DATABASE_URL",
            "Project Settings → Database → Connection string → Session pooler",
        )
        gemini_key = prompt(
            "2) Gemini API key",
            "Free at https://aistudio.google.com/apikey",
        )

        example = (BACKEND / ".env.example").read_text()
        content = example.replace(
            "DATABASE_URL=postgresql+psycopg://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres",
            f"DATABASE_URL={database_url}",
        ).replace("GEMINI_API_KEY=", f"GEMINI_API_KEY={gemini_key}", 1)
        backend_env.write_text(content)
        print("\n✓ Saved backend/.env")

    if not frontend_env.exists():
        (FRONTEND / ".env.example").read_text()
        frontend_env.write_text((FRONTEND / ".env.example").read_text())
        print("✓ Saved frontend/.env")

    env_text = backend_env.read_text()
    if "DATABASE_URL=\n" in env_text or "DATABASE_URL=postgresql+psycopg://postgres.[project-ref]" in env_text:
        die("backend/.env is missing a real DATABASE_URL — edit that file and re-run this script.")

    return first_time


def stream_output(proc: subprocess.Popen, label: str) -> None:
    assert proc.stdout is not None
    for line in proc.stdout:
        print(f"[{label}] {line}", end="")


def _raise_keyboard_interrupt(signum: int, frame: object) -> None:
    raise KeyboardInterrupt


def main() -> None:
    # Ctrl+C delivers SIGINT and Python already turns that into
    # KeyboardInterrupt on its own. Also handle SIGTERM explicitly, so
    # stopping this via a process manager, IDE "stop" button, or `kill`
    # cleans up all three child processes the same way Ctrl+C does.
    signal.signal(signal.SIGTERM, _raise_keyboard_interrupt)

    print("DocBrain — one-command setup & run\n")
    check_prerequisites()
    first_time = first_time_env_setup()

    run(["uv", "sync"], BACKEND, "Installing backend dependencies")
    check_libmagic()
    run([npm_cmd(), "install"], FRONTEND, "Installing frontend dependencies")
    run(["uv", "run", "python", "-m", "alembic", "upgrade", "head"], BACKEND, "Applying database migrations")

    if first_time:
        run(["uv", "run", "python", "-m", "scripts.seed"], BACKEND, "Seeding demo data")
        run(
            ["uv", "run", "python", "-m", "scripts.backfill_seed_files"],
            BACKEND,
            "Writing demo file content",
        )

    free_ports()

    print("\n" + "=" * 60)
    print("Starting DocBrain (Ctrl+C to stop everything)")
    print("=" * 60 + "\n")

    processes: list[subprocess.Popen] = []
    try:
        api = subprocess.Popen(
            ["uv", "run", "python", "-m", "uvicorn", "app.main:app", "--port", "8000"],
            cwd=BACKEND, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        processes.append(api)
        threading.Thread(target=stream_output, args=(api, "api"), daemon=True).start()

        worker = subprocess.Popen(
            ["uv", "run", "python", "-m", "app.ai_jobs.main"],
            cwd=BACKEND, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        processes.append(worker)
        threading.Thread(target=stream_output, args=(worker, "ai-worker"), daemon=True).start()

        web = subprocess.Popen(
            [npm_cmd(), "run", "dev"],
            cwd=FRONTEND, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        processes.append(web)
        threading.Thread(target=stream_output, args=(web, "web"), daemon=True).start()

        time.sleep(6)
        print("\n✓ Opening http://localhost:3000\n")
        webbrowser.open("http://localhost:3000")

        while all(p.poll() is None for p in processes):
            time.sleep(1)
        die("One of the processes exited unexpectedly — see output above.")
    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()
        for p in processes:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        print("Stopped.")


if __name__ == "__main__":
    main()
