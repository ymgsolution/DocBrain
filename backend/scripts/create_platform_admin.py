"""Create (or reset the password of) a platform admin — the account that
manages organizations, not documents. See app/db/models/platform_admin.py
for why this is a separate table/login from regular users.

There is no self-service way to create the first platform admin (nobody
above it to grant that access) — this script is that bootstrap step, run
once per environment. Safe to re-run for an existing email: it resets the
password rather than erroring.

Usage: uv run python -m scripts.create_platform_admin <email> <display name> <password>
"""

import sys

from sqlalchemy import select

from app.core.passwords import MIN_PASSWORD_LENGTH, hash_password
from app.db.models import PlatformAdmin
from app.db.session import SessionLocal


def main() -> None:
    if len(sys.argv) != 4:
        print("Usage: uv run python -m scripts.create_platform_admin <email> <display name> <password>")
        sys.exit(1)

    email, display_name, password = sys.argv[1], sys.argv[2], sys.argv[3]
    email = email.strip().lower()

    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        sys.exit(1)

    db = SessionLocal()
    try:
        admin = db.scalar(select(PlatformAdmin).where(PlatformAdmin.email == email))
        if admin is None:
            admin = PlatformAdmin(email=email, display_name=display_name, password_hash=hash_password(password))
            db.add(admin)
            action = "Created"
        else:
            admin.display_name = display_name
            admin.password_hash = hash_password(password)
            admin.is_active = True
            action = "Reset"
        db.commit()
        print(f"{action} platform admin {email!r}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
