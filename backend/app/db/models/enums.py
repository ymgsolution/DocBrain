import enum


class UserRole(str, enum.Enum):
    EMPLOYEE = "EMPLOYEE"
    REVIEWER = "REVIEWER"
    ADMIN = "ADMIN"


class DocumentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DELETED = "DELETED"


class ActivityEventType(str, enum.Enum):
    CREATED = "CREATED"
    VERSION_UPLOADED = "VERSION_UPLOADED"
    VERSION_RESTORED = "VERSION_RESTORED"
    METADATA_UPDATED = "METADATA_UPDATED"
    REVIEWED = "REVIEWED"
    DELETED = "DELETED"
    RESTORED = "RESTORED"


class ThemePreference(str, enum.Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"
