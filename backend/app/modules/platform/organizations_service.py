import uuid

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.passwords import MIN_PASSWORD_LENGTH, hash_password
from app.db.models import Organization, User
from app.db.models.enums import UserRole
from app.modules.auth.repository import AuthRepository
from app.modules.platform.organizations_repository import OrganizationsRepository
from app.utils.slugify import slugify


class OrganizationsService:
    def __init__(self, repository: OrganizationsRepository, users: AuthRepository) -> None:
        self.repository = repository
        self.users = users

    def list_organizations(self) -> list[tuple[Organization, int, int, int]]:
        return self.repository.list_with_stats()

    def _unique_slug(self, base: str) -> str:
        base_slug = slugify(base)
        candidate = base_slug
        i = 2
        while self.repository.get_by_slug(candidate) is not None:
            candidate = f"{base_slug}-{i}"
            i += 1
        return candidate

    def create_organization(self, *, name: str) -> Organization:
        organization = Organization(name=name.strip(), slug=self._unique_slug(name))
        self.repository.add(organization)
        self.repository.db.commit()
        self.repository.db.refresh(organization)
        return organization

    def create_first_admin(
        self, organization_id: uuid.UUID, *, email: str, display_name: str, password: str
    ) -> User:
        """The one bootstrap exception to "admins invite people" — a brand
        new organization has no admin yet to send that invite, so a
        platform admin creates the first one directly rather than going
        through the normal Invitation flow. Everyone after this one *does*
        go through that flow, started by this new admin."""
        organization = self.repository.get_by_id(organization_id)
        if organization is None:
            raise NotFoundError("This organization doesn't exist.")

        normalised = email.strip().lower()
        if self.users.get_by_email(normalised) is not None:
            raise ConflictError(
                "Someone already has an account with that email.",
                fields=[{"field": "email", "message": "This email already has an account."}],
            )
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValidationError(
                f"Choose a password of at least {MIN_PASSWORD_LENGTH} characters.",
                fields=[{"field": "password", "message": f"At least {MIN_PASSWORD_LENGTH} characters."}],
            )

        admin = User(
            email=normalised,
            display_name=display_name.strip(),
            role=UserRole.ADMIN,
            organization_id=organization.id,
            is_active=True,
            password_hash=hash_password(password),
        )
        self.repository.db.add(admin)
        self.repository.db.commit()
        self.repository.db.refresh(admin)
        return admin
