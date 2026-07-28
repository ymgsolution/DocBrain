"""Give every existing user a known password, so the seeded demo accounts
still work after login started requiring one.

These are demo identities in a portfolio project and the password is
published in the README — that is a deliberate, documented choice, not an
oversight. Any real account should be created through an invite instead
(see the invitations flow), which never routes through here.

Safe to re-run: it simply re-hashes the same password.

Usage: uv run python -m scripts.set_demo_passwords
"""

from sqlalchemy import select

from app.core.passwords import hash_password
from app.db.models import User
from app.db.session import SessionLocal

DEMO_PASSWORD = "Test@123"


def main() -> None:
    db = SessionLocal()
    try:
        users = list(db.scalars(select(User)))
        for user in users:
            user.password_hash = hash_password(DEMO_PASSWORD)
            print(f"  set password for {user.email} ({user.role.value})")
        db.commit()
        print(f"\nDone. {len(users)} user(s) can now log in with: {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
