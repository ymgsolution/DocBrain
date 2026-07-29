"""Seed the DocBrain database with a realistic, browsable demo corpus.

Idempotent *and tenant-scoped*: deletes and reseeds only the demo
organization (DEFAULT_ORGANIZATION_ID), so it's safe to re-run against a
database that also holds real organizations. Any other organization's rows
are left alone, and a tripwire around the reset rolls the whole run back if
that ever stops being true.

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
from app.db.models.organization import DEFAULT_ORGANIZATION_ID
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


# Children first. The ON DELETE CASCADEs hanging off documents and
# document_versions do most of the work (versions, document_tags,
# activity_events, share_links, ai_jobs, ai_document_analysis,
# document_vector_embeddings, document_extracted_text); the rest of this list
# clears rows that hang off the organization directly rather than off a
# document, and users last because documents/versions/activity reference it
# with ON DELETE RESTRICT.
_RESET_ORDER = (
    "documents",
    "activity_events",
    "share_links",
    "invitations",
    "ai_jobs",
    "ai_document_analysis",
    "document_vector_embeddings",
    "document_versions",
    "tags",
    "categories",
    "users",  # cascades user_preferences and password_reset_tokens
)


def reset_default_organization(session: Session) -> None:
    """Delete every row belonging to the demo organization — and nothing else.

    This replaces a global `TRUNCATE ... CASCADE`, which emptied these tables
    for *every* organization and then reseeded only this one. Any other
    organization was left as a shell with no categories and no users: upload
    blocked, nobody able to log in — the exact "new organization can't do
    anything" bug this project has already fixed once. Since local and
    production share one database, re-running the old version against a
    multi-organization database was a live data-loss bug, not a theoretical
    one.
    """
    for table in _RESET_ORDER:
        session.execute(
            text(f"DELETE FROM {table} WHERE organization_id = :org_id"),
            {"org_id": DEFAULT_ORGANIZATION_ID},
        )


def snapshot_other_organizations(session: Session) -> dict[str, int]:
    """Row counts per organization, excluding the demo one — the tripwire that
    proves the reset above stayed inside its own tenant."""
    rows = session.execute(
        text(
            "SELECT o.name, "
            "  (SELECT count(*) FROM users u WHERE u.organization_id = o.id) "
            "+ (SELECT count(*) FROM categories c WHERE c.organization_id = o.id) "
            "+ (SELECT count(*) FROM documents d WHERE d.organization_id = o.id) "
            "+ (SELECT count(*) FROM tags t WHERE t.organization_id = o.id) "
            "FROM organizations o WHERE o.id != :org_id ORDER BY o.name"
        ),
        {"org_id": DEFAULT_ORGANIZATION_ID},
    ).all()
    return {name: total for name, total in rows}


def seed_users(session: Session) -> list[User]:
    users = [
        User(email=email, display_name=name, role=role, organization_id=DEFAULT_ORGANIZATION_ID)
        for email, name, role in USERS
    ]
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
        Category(
            name=name,
            slug=slugify(name),
            description=desc,
            default_review_period_days=period,
            organization_id=DEFAULT_ORGANIZATION_ID,
        )
        for name, desc, period in CATEGORIES
    ]
    session.add_all(categories)
    session.flush()
    return categories


def seed_tags(session: Session) -> list[Tag]:
    tags = [
        Tag(name=name, normalized_name=name.lower(), organization_id=DEFAULT_ORGANIZATION_ID) for name in TAGS
    ]
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
            organization_id=DEFAULT_ORGANIZATION_ID,
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
                    organization_id=DEFAULT_ORGANIZATION_ID,
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
                organization_id=DEFAULT_ORGANIZATION_ID,
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
                    organization_id=DEFAULT_ORGANIZATION_ID,
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
            preserved = snapshot_other_organizations(session)
            if preserved:
                print(
                    "Leaving these organizations untouched: "
                    + ", ".join(f"{name} ({count} rows)" for name, count in preserved.items())
                )

            print(f"Resetting demo organization {DEFAULT_ORGANIZATION_ID}...")
            reset_default_organization(session)

            # Inside the transaction on purpose: if the reset ever reaches
            # outside its own tenant again, this raises and the whole thing
            # rolls back rather than committing another organization's loss.
            after_reset = snapshot_other_organizations(session)
            if after_reset != preserved:
                raise RuntimeError(
                    "Refusing to continue — the reset touched another organization's data: "
                    f"{preserved} -> {after_reset}"
                )

            print("Seeding users...")
            users = seed_users(session)

            print("Seeding categories...")
            categories = seed_categories(session)

            print("Seeding tags...")
            tags = seed_tags(session)

            print("Seeding documents, versions, tags, and activity...")
            seed_documents(session, users, categories, tags)

        print("Done.")

        # Scoped to the demo organization, not global — on a database that
        # also holds real organizations, global counts would describe rows
        # this script never touched.
        counts = session.execute(
            text(
                "SELECT "
                "(SELECT count(*) FROM users WHERE organization_id = :org_id), "
                "(SELECT count(*) FROM categories WHERE organization_id = :org_id), "
                "(SELECT count(*) FROM tags WHERE organization_id = :org_id), "
                "(SELECT count(*) FROM documents WHERE organization_id = :org_id), "
                "(SELECT count(*) FROM document_versions WHERE organization_id = :org_id), "
                "(SELECT count(*) FROM activity_events WHERE organization_id = :org_id)"
            ),
            {"org_id": DEFAULT_ORGANIZATION_ID},
        ).one()
        print(
            f"users={counts[0]} categories={counts[1]} tags={counts[2]} "
            f"documents={counts[3]} document_versions={counts[4]} activity_events={counts[5]}"
        )


if __name__ == "__main__":
    main()
