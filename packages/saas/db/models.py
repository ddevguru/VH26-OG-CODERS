import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Float,
    DateTime,
    ForeignKey,
    Text,
    Enum as SQLEnum,
    Index,
)
from sqlalchemy.orm import relationship
import enum

from packages.saas.db.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RoleEnum(str, enum.Enum):
    OWNER = "Owner"
    ADMIN = "Admin"
    SECURITY = "Security"
    DEVELOPER = "Developer"
    VIEWER = "Viewer"


class FindingStatusEnum(str, enum.Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=utc_now)

    teams = relationship("Team", back_populates="organization", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="organization", cascade="all, delete-orphan")
    repositories = relationship("Repository", back_populates="organization", cascade="all, delete-orphan")
    scans = relationship("Scan", back_populates="organization", cascade="all, delete-orphan")
    user_roles = relationship("UserOrgRole", back_populates="organization", cascade="all, delete-orphan")
    policies = relationship("Policy", back_populates="organization", cascade="all, delete-orphan")
    baselines = relationship("Baseline", back_populates="organization", cascade="all, delete-orphan")
    suppressions = relationship("Suppression", back_populates="organization", cascade="all, delete-orphan")
    integrations = relationship("Integration", back_populates="organization", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    org_roles = relationship("UserOrgRole", back_populates="user", cascade="all, delete-orphan")


class UserOrgRole(Base):
    __tablename__ = "user_org_roles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    role = Column(String(50), nullable=False, default=RoleEnum.DEVELOPER.value)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="org_roles")
    organization = relationship("Organization", back_populates="user_roles")


class Team(Base):
    __tablename__ = "teams"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    organization = relationship("Organization", back_populates="teams")
    projects = relationship("Project", back_populates="team")


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    team_id = Column(String(36), ForeignKey("teams.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    key = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=utc_now)

    organization = relationship("Organization", back_populates="projects")
    team = relationship("Team", back_populates="projects")
    repositories = relationship("Repository", back_populates="project")


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(512), nullable=True)
    default_branch = Column(String(100), default="main")
    created_at = Column(DateTime, default=utc_now)

    organization = relationship("Organization", back_populates="repositories")
    project = relationship("Project", back_populates="repositories")
    scans = relationship("Scan", back_populates="repository", cascade="all, delete-orphan")
    baselines = relationship("Baseline", back_populates="repository", cascade="all, delete-orphan")
    suppressions = relationship("Suppression", back_populates="repository", cascade="all, delete-orphan")


class Scan(Base):
    __tablename__ = "scans"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    repo_id = Column(String(36), ForeignKey("repositories.id"), nullable=False, index=True)
    commit_sha = Column(String(100), nullable=True)
    branch = Column(String(100), nullable=True)
    status = Column(String(50), default="completed")
    scanned_files_count = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0.0)
    policy_passed = Column(Boolean, default=True)
    total_findings = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)

    organization = relationship("Organization", back_populates="scans")
    repository = relationship("Repository", back_populates="scans")
    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")


class Finding(Base):
    __tablename__ = "findings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    scan_id = Column(String(36), ForeignKey("scans.id"), nullable=False, index=True)
    rule_id = Column(String(100), nullable=False, index=True)
    file_path = Column(String(512), nullable=False)
    line_number = Column(Integer, nullable=False)
    severity = Column(String(50), nullable=False)
    confidence = Column(String(50), nullable=False)
    classification = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    fingerprint = Column(String(64), nullable=False, index=True)
    status = Column(String(50), default=FindingStatusEnum.OPEN.value, index=True)
    created_at = Column(DateTime, default=utc_now)

    organization = relationship("Organization")
    scan = relationship("Scan", back_populates="findings")


class Rule(Base):
    __tablename__ = "rules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    rule_id = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    default_severity = Column(String(50), nullable=False)
    default_confidence = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    is_custom = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)


class Policy(Base):
    __tablename__ = "policies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    min_severity = Column(String(50), default="MEDIUM")
    min_confidence = Column(String(50), default="MEDIUM")
    fail_on_leak = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    organization = relationship("Organization", back_populates="policies")


class Baseline(Base):
    __tablename__ = "baselines"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    repo_id = Column(String(36), ForeignKey("repositories.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    fingerprints_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=utc_now)

    organization = relationship("Organization", back_populates="baselines")
    repository = relationship("Repository", back_populates="baselines")


class Suppression(Base):
    __tablename__ = "suppressions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    repo_id = Column(String(36), ForeignKey("repositories.id"), nullable=False, index=True)
    finding_fingerprint = Column(String(64), nullable=False, index=True)
    reason = Column(Text, nullable=True)
    suppressed_by_user_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    organization = relationship("Organization", back_populates="suppressions")
    repository = relationship("Repository", back_populates="suppressions")


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    integration_type = Column(String(50), nullable=False)  # github, gitlab, slack, webhook
    config_json = Column(Text, nullable=False, default="{}")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    organization = relationship("Organization", back_populates="integrations")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=True)
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    organization = relationship("Organization", back_populates="audit_events")


class AIReview(Base):
    __tablename__ = "ai_reviews"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    scan_id = Column(String(36), ForeignKey("scans.id"), nullable=True, index=True)
    target = Column(String(255), nullable=False, default="project")
    review_mode = Column(String(50), default="detailed")
    overall_status = Column(String(50), default="PASSED")
    summary = Column(Text, nullable=True)
    details_json = Column(Text, nullable=True)
    trace_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now)


class AIAgentActivity(Base):
    __tablename__ = "ai_agent_activities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    scan_id = Column(String(36), ForeignKey("scans.id"), nullable=True, index=True)
    trace_id = Column(String(100), nullable=True, index=True)
    agent_name = Column(String(100), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    duration_ms = Column(Float, default=0.0)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class AIFixVerification(Base):
    __tablename__ = "ai_fix_verifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    finding_id = Column(String(36), nullable=False, index=True)
    status = Column(String(50), nullable=False)  # VERIFIED_FIX / REJECTED
    is_verified = Column(Boolean, default=False)
    candidate_patch = Column(Text, nullable=True)
    unified_diff = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)


# Performance and isolation indexes
Index("idx_findings_org_status", Finding.org_id, Finding.status)
Index("idx_scans_org_repo", Scan.org_id, Scan.repo_id)
Index("idx_audit_org_created", AuditEvent.org_id, AuditEvent.created_at)
Index("idx_ai_activity_org_user", AIAgentActivity.org_id, AIAgentActivity.user_id)

