from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text, Integer, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), default="")
    display_name: Mapped[str] = mapped_column(String(100), default="")
    avatar: Mapped[str] = mapped_column(String(500), default="")
    position: Mapped[str] = mapped_column(String(100), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    litellm_user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    roles: Mapped[list["UserRole"]] = relationship(back_populates="user", lazy="selectin")
    departments: Mapped[list["UserDepartment"]] = relationship(back_populates="user", lazy="selectin")
    projects: Mapped[list["UserProject"]] = relationship(back_populates="user", lazy="selectin")


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("aihelms.departments.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    litellm_team_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    members: Mapped[list["UserDepartment"]] = relationship(back_populates="department", lazy="selectin")


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    litellm_team_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    members: Mapped[list["UserProject"]] = relationship(back_populates="project", lazy="selectin")


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    permissions: Mapped[list["RolePermission"]] = relationship(back_populates="role", lazy="selectin")


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    resource: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.users.id", ondelete="CASCADE"))
    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.roles.id", ondelete="CASCADE"))

    user: Mapped["User"] = relationship(back_populates="roles")
    role: Mapped["Role"] = relationship(lazy="selectin")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.roles.id", ondelete="CASCADE"))
    permission_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.permissions.id", ondelete="CASCADE"))

    role: Mapped["Role"] = relationship(back_populates="permissions")
    permission: Mapped["Permission"] = relationship(lazy="selectin")


class UserDepartment(Base):
    __tablename__ = "user_departments"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.users.id", ondelete="CASCADE"))
    department_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.departments.id", ondelete="CASCADE"))
    is_manager: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="departments")
    department: Mapped["Department"] = relationship(back_populates="members", lazy="selectin")


class UserProject(Base):
    __tablename__ = "user_projects"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.users.id", ondelete="CASCADE"))
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.projects.id", ondelete="CASCADE"))
    joined_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="projects")
    project: Mapped["Project"] = relationship(back_populates="members", lazy="selectin")


class AiKey(Base):
    __tablename__ = "ai_keys"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    key_type: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_type: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    litellm_key_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    litellm_key_alias: Mapped[str | None] = mapped_column(String(200), nullable=True)
    models: Mapped[list] = mapped_column(JSONB, default=list)
    budget_limit: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    budget_type: Mapped[str] = mapped_column(String(10), default="money")
    budget_hard_limit: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("aihelms.users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(nullable=True)


class Provider(Base):
    __tablename__ = "providers"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)
    billing_type: Mapped[str] = mapped_column(String(20), default="token")
    monthly_budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    monthly_used: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(Text, default="")
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    credentials: Mapped[list["Credential"]] = relationship(back_populates="provider", lazy="selectin")


class Credential(Base):
    __tablename__ = "credentials"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    credential_name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    provider_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("aihelms.providers.id", ondelete="SET NULL"), nullable=True)
    credential_values: Mapped[dict] = mapped_column(JSONB, default=dict)
    credential_info: Mapped[dict] = mapped_column(JSONB, default=dict)
    litellm_synced: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    provider: Mapped["Provider | None"] = relationship(back_populates="credentials")
    deployments: Mapped[list["ModelDeployment"]] = relationship(back_populates="credential", lazy="selectin")


class Model(Base):
    __tablename__ = "models"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="chat")
    capabilities: Mapped[list] = mapped_column(JSONB, default=list)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    deployments: Mapped[list["ModelDeployment"]] = relationship(back_populates="model", lazy="selectin")


class ModelDeployment(Base):
    __tablename__ = "model_deployments"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    model_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.models.id", ondelete="CASCADE"))
    credential_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("aihelms.credentials.id", ondelete="SET NULL"), nullable=True)
    litellm_model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    litellm_params: Mapped[dict] = mapped_column(JSONB, default=dict)
    model_info: Mapped[dict] = mapped_column(JSONB, default=dict)
    deploy_name: Mapped[str] = mapped_column(String(128), default="")
    billing_type: Mapped[str] = mapped_column(String(20), default="token")
    cost_per_call: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    monthly_call_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_call_used: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    model: Mapped["Model"] = relationship(back_populates="deployments")
    credential: Mapped["Credential | None"] = relationship(back_populates="deployments", lazy="selectin")


class ModelAccessGroup(Base):
    __tablename__ = "model_access_groups"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    group_name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    model_ids: Mapped[list] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class RouterSettings(Base):
    __tablename__ = "router_settings"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    routing_strategy: Mapped[str] = mapped_column(String(50), default="simple-shuffle")
    fallbacks: Mapped[list] = mapped_column(JSONB, default=list)
    allowed_fails: Mapped[int] = mapped_column(Integer, default=3)
    cooldown_time: Mapped[int] = mapped_column(Integer, default=60)
    num_retries: Mapped[int] = mapped_column(Integer, default=2)
    timeout: Mapped[int] = mapped_column(Integer, default=30)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class AiKeyModelLimit(Base):
    __tablename__ = "ai_key_model_limits"
    __table_args__ = (
        {"schema": "aihelms"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ai_key_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.ai_keys.id", ondelete="CASCADE"))
    model_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.models.id", ondelete="CASCADE"))
    tpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_calls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
