"""Seed the DocBrain database with a realistic, browsable demo corpus.

Idempotent: truncates all app tables before reseeding, so it's safe to
re-run against the same (dev/demo) database as often as needed.

Usage: uv run python scripts/seed.py
"""
import hashlib
import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import (
    ActivityEvent,
    Category,
    Document,
    DocumentTag,
    DocumentVersion,
    Tag,
    User,
    UserPreference,
)
from app.db.models.enums import ActivityEventType, DocumentStatus, ThemePreference, UserRole
from app.db.session import engine

random.seed(42)

NOW = datetime(2026, 7, 23, 12, 0, 0, tzinfo=timezone.utc)

USERS = [
    ("priya@docbrain.dev", "Priya Sharma", UserRole.EMPLOYEE),
    ("arjun@docbrain.dev", "Arjun Mehta", UserRole.EMPLOYEE),
    ("neha@docbrain.dev", "Neha Kapoor", UserRole.EMPLOYEE),
    ("rahul@docbrain.dev", "Rahul Verma", UserRole.REVIEWER),
    ("anita@docbrain.dev", "Anita Desai", UserRole.ADMIN),
]

CATEGORIES = [
    ("Proposals", "Client-facing proposals and pitches", 180),
    ("Specifications", "Technical and product specifications", 180),
    ("Policies", "Internal governance and HR policies", 365),
    ("Reports", "Status, financial, and analytics reports", 90),
    ("Contracts", "Signed agreements and contracts", None),
    ("Statements of Work", "SOWs for active and past engagements", 180),
    ("Design Docs", "Architecture and design documentation", 270),
    ("Meeting Notes", "Minutes of meeting and decisions", None),
    ("Onboarding", "New-hire and new-client onboarding material", 365),
    ("Compliance", "Audit evidence and compliance records", 90),
    ("Marketing", "Marketing collateral and campaign assets", None),
    ("Templates", "Reusable document templates", 365),
]

TAGS = [
    "acme", "globex", "initech", "2026", "q1", "q2", "q3",
    "urgent", "draft", "final", "client-facing", "internal",
    "engineering", "design", "legal", "finance", "hr",
    "onboarding", "api", "backend", "frontend", "mobile",
    "roadmap", "architecture", "review-needed", "deprecated",
    "template", "guide", "checklist", "budget", "audit",
]

TITLE_TEMPLATES = {
    "Proposals": ["Proposal — {client} Platform Modernisation", "Proposal — {client} Phase {n} Extension"],
    "Specifications": ["Spec — {client} API Gateway", "Spec — {client} Mobile App v{n}"],
    "Policies": ["Data Retention Policy", "Remote Work Policy", "Information Security Policy v{n}"],
    "Reports": ["{client} Q{n} Status Report", "Monthly Analytics Report — {client}"],
    "Contracts": ["MSA — {client}", "NDA — {client}"],
    "Statements of Work": ["SOW — {client} Migration", "SOW — {client} Support Retainer"],
    "Design Docs": ["Architecture — {client} Search Service", "Design Doc — {client} Notification System"],
    "Meeting Notes": ["MoM — {client} Kickoff", "MoM — {client} Sprint Review {n}"],
    "Onboarding": ["Onboarding Guide — {client}", "New Hire Handbook v{n}"],
    "Compliance": ["SOC 2 Evidence — {client}", "Audit Log Export Q{n}"],
    "Marketing": ["{client} Case Study", "Product One-Pager v{n}"],
    "Templates": ["SOW Template v{n}", "Proposal Template v{n}"],
}

CLIENTS = ["Acme", "Globex", "Initech", "Umbrella", "Stark", "Wayne", "Hooli"]

EXTENSIONS = [
    ("pdf", "application/pdf"),
    ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ("pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
    ("txt", "text/plain"),
    ("md", "text/markdown"),
]


def slugify(value: str) -> str:
    return value.lower().replace(" ", "-").replace("—", "-").replace("--", "-").strip("-")


def fake_checksum(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def truncate_all(session: Session) -> None:
    session.execute(
        text(
            "TRUNCATE TABLE activity_events, document_tags, document_versions, "
            "documents, user_preferences, tags, categories, users RESTART IDENTITY CASCADE"
        )
    )


def seed_users(session: Session) -> list[User]:
    users = [User(email=email, display_name=name, role=role) for email, name, role in USERS]
    session.add_all(users)
    session.flush()
    for i, user in enumerate(users):
        session.add(
            UserPreference(
                user_id=user.id,
                theme=ThemePreference.DARK if i % 3 == 0 else ThemePreference.SYSTEM,
                default_page_size=25,
            )
        )
    return users


def seed_categories(session: Session) -> list[Category]:
    categories = [
        Category(name=name, slug=slugify(name), description=desc, default_review_period_days=period)
        for name, desc, period in CATEGORIES
    ]
    session.add_all(categories)
    session.flush()
    return categories


def seed_tags(session: Session) -> list[Tag]:
    tags = [Tag(name=name, normalized_name=name.lower()) for name in TAGS]
    session.add_all(tags)
    session.flush()
    return tags


def pick_review_due_date(bucket: str) -> date | None:
    if bucket == "overdue":
        return (NOW - timedelta(days=random.randint(5, 60))).date()
    if bucket == "due_soon":
        return (NOW + timedelta(days=random.randint(1, 29))).date()
    if bucket == "fine":
        return (NOW + timedelta(days=random.randint(60, 300))).date()
    return None


def seed_documents(
    session: Session, users: list[User], categories: list[Category], tags: list[Tag], count: int = 52
) -> None:
    employees = [u for u in users if u.role in (UserRole.EMPLOYEE, UserRole.REVIEWER, UserRole.ADMIN)]
    reviewer = next(u for u in users if u.role == UserRole.REVIEWER)

    review_buckets = (
        ["overdue"] * int(count * 0.15)
        + ["due_soon"] * int(count * 0.15)
        + ["fine"] * int(count * 0.4)
        + [None] * count
    )
    random.shuffle(review_buckets)

    for i in range(count):
        category = categories[i % len(categories)]
        templates = TITLE_TEMPLATES[category.name]
        title = random.choice(templates).format(client=random.choice(CLIENTS), n=random.randint(1, 4))
        owner = random.choice(employees)

        # Pick version_count first so created_at leaves enough runway for every
        # version's upload date to land before NOW (never in the future).
        version_count = random.choices([1, 2, 3, 4], weights=[40, 30, 20, 10])[0]
        gaps = [random.randint(2, 20) for _ in range(version_count - 1)]
        span_days = sum(gaps)
        created_at = NOW - timedelta(days=span_days + random.randint(5, 100), hours=random.randint(0, 23))

        doc = Document(
            title=title,
            description=f"{title} — maintained by {owner.display_name}.",
            category_id=category.id,
            owner_id=owner.id,
            status=DocumentStatus.ACTIVE,
            review_due_date=pick_review_due_date(review_buckets[i]),
            created_at=created_at,
            updated_at=created_at,
            last_accessed_at=min(created_at + timedelta(days=random.randint(0, 5)), NOW)
            if random.random() > 0.4
            else None,
        )
        session.add(doc)
        session.flush()

        # 20% chance of being already reviewed, resetting the due date forward
        if review_buckets[i] in ("fine",) and random.random() < 0.3:
            doc.last_reviewed_at = min(created_at + timedelta(days=random.randint(1, 10)), NOW)
            doc.last_reviewed_by = reviewer.id
            session.add(
                ActivityEvent(
                    document_id=doc.id,
                    actor_id=reviewer.id,
                    event_type=ActivityEventType.REVIEWED,
                    summary=f"{reviewer.display_name} marked “{title}” as reviewed",
                    occurred_at=doc.last_reviewed_at,
                )
            )

        doc_tags = random.sample(tags, k=random.randint(2, 4))
        for tag in doc_tags:
            session.add(DocumentTag(document_id=doc.id, tag_id=tag.id))

        ext, mime = random.choice(EXTENSIONS)
        filename = f"{title}.{ext}"
        last_version = None
        upload_offset_days = [0] + gaps
        for v in range(1, version_count + 1):
            uploaded_at = created_at + timedelta(days=sum(upload_offset_days[:v]))
            uploader = owner if v == 1 else random.choice(employees)
            version = DocumentVersion(
                document_id=doc.id,
                version_number=v,
                storage_path=f"uploads/documents/{doc.id}/v{v}__{slugify(filename)}",
                original_filename=filename,
                mime_type=mime,
                size_bytes=random.randint(50_000, 5_000_000),
                checksum_sha256=fake_checksum(f"{doc.id}-v{v}"),
                change_note=None if v == 1 else random.choice(
                    ["Fixed formatting and typos", "Updated per client feedback",
                     "Added missing section", "Refreshed figures for this quarter"]
                ),
                uploaded_by=uploader.id,
                uploaded_at=uploaded_at,
            )
            session.add(version)
            session.flush()
            last_version = version

            session.add(
                ActivityEvent(
                    document_id=doc.id,
                    actor_id=uploader.id,
                    event_type=ActivityEventType.CREATED if v == 1 else ActivityEventType.VERSION_UPLOADED,
                    summary=(
                        f"{uploader.display_name} uploaded “{title}” (v1)"
                        if v == 1
                        else f"{uploader.display_name} uploaded version {v} of “{title}”"
                    ),
                    occurred_at=uploaded_at,
                )
            )

        doc.current_version_id = last_version.id
        doc.updated_at = last_version.uploaded_at


def main() -> None:
    with Session(engine) as session:
        with session.begin():
            print("Truncating existing data...")
            truncate_all(session)

            print("Seeding users...")
            users = seed_users(session)

            print("Seeding categories...")
            categories = seed_categories(session)

            print("Seeding tags...")
            tags = seed_tags(session)

            print("Seeding documents, versions, tags, and activity...")
            seed_documents(session, users, categories, tags)

        print("Done.")

        counts = session.execute(
            text(
                "SELECT "
                "(SELECT count(*) FROM users), "
                "(SELECT count(*) FROM categories), "
                "(SELECT count(*) FROM tags), "
                "(SELECT count(*) FROM documents), "
                "(SELECT count(*) FROM document_versions), "
                "(SELECT count(*) FROM activity_events)"
            )
        ).one()
        print(
            f"users={counts[0]} categories={counts[1]} tags={counts[2]} "
            f"documents={counts[3]} document_versions={counts[4]} activity_events={counts[5]}"
        )


if __name__ == "__main__":
    main()
