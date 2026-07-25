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


class ExtractionMethod(str, enum.Enum):
    PDF = "PDF"
    DOCX = "DOCX"
    XLSX = "XLSX"
    PPTX = "PPTX"
    PLAIN = "PLAIN"


class ExtractionStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNSUPPORTED = "UNSUPPORTED"


class AiJobType(str, enum.Enum):
    EXTRACT = "EXTRACT"
    GENERATE_METADATA = "GENERATE_METADATA"
    GENERATE_EMBEDDING = "GENERATE_EMBEDDING"


class AiJobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class AiAnalysisStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
