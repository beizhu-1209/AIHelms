from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text, Integer, Numeric, func, UniqueConstraint, DateTime
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
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
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False)
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
    mcps: Mapped[list] = mapped_column(JSONB, default=list)
    skills: Mapped[list] = mapped_column(JSONB, default=list)
    agents: Mapped[list] = mapped_column(JSONB, default=list)
    budget_limit: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    budget_used: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    budget_hard_limit: Mapped[bool] = mapped_column(Boolean, default=False)
    budget_duration: Mapped[str | None] = mapped_column(String(10), default="30d")
    budget_scope: Mapped[str] = mapped_column(String(20), default="unified")
    budget_models_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    budget_mcps_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    budget_models_per: Mapped[str] = mapped_column(String(10), default="unified")
    budget_mcps_per: Mapped[str] = mapped_column(String(10), default="unified")
    model_budgets: Mapped[dict] = mapped_column(JSONB, default=dict)
    mcp_budgets: Mapped[dict] = mapped_column(JSONB, default=dict)
    rate_limit_mode: Mapped[str] = mapped_column(String(20), default="none")
    tpm_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpm_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_parallel_requests: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scenario_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("aihelms.key_scenarios.id"), nullable=True)
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


class ProviderPrefixMap(Base):
    __tablename__ = "provider_prefix_map"
    __table_args__ = (
        UniqueConstraint("provider_type", "format", "category"),
        {"schema": "aihelms"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    prefix: Mapped[str] = mapped_column(String(50), nullable=False)
    needs_v1: Mapped[bool] = mapped_column(Boolean, default=False)


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
    model_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="chat")
    capabilities: Mapped[list] = mapped_column(JSONB, default=list)
    description: Mapped[str] = mapped_column(Text, default="")
    business_scenario_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("aihelms.business_scenarios.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    visibility_type: Mapped[str] = mapped_column(String(20), default="all")
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    deployments: Mapped[list["ModelDeployment"]] = relationship(back_populates="model", lazy="selectin")
    department_visibility: Mapped[list["ModelDepartmentVisibility"]] = relationship(back_populates="model", lazy="selectin")
    user_visibility: Mapped[list["ModelUserVisibility"]] = relationship(back_populates="model", lazy="selectin")


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


class KeyScenario(Base):
    __tablename__ = "key_scenarios"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class ModelDepartmentVisibility(Base):
    __tablename__ = "model_department_visibility"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    model_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.models.id", ondelete="CASCADE"))
    department_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.departments.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    model: Mapped["Model"] = relationship(back_populates="department_visibility")
    department: Mapped["Department"] = relationship(lazy="selectin")


class ModelUserVisibility(Base):
    __tablename__ = "model_user_visibility"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    model_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.models.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    model: Mapped["Model"] = relationship(back_populates="user_visibility")
    user: Mapped["User"] = relationship(lazy="selectin")


class McpCategory(Base):
    __tablename__ = "mcp_categories"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class McpServer(Base):
    __tablename__ = "mcp_servers"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    server_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    server_name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text, nullable=False)
    transport: Mapped[str] = mapped_column(String(10), default="sse")
    auth_type: Mapped[str] = mapped_column(String(30), default="none")
    credentials: Mapped[dict] = mapped_column(JSONB, default=dict)
    instructions: Mapped[str] = mapped_column(Text, default="")
    mcp_info: Mapped[dict] = mapped_column(JSONB, default=dict)
    extra_headers: Mapped[list] = mapped_column(ARRAY(String), default=list)
    allowed_tools: Mapped[list] = mapped_column(JSONB, default=list)
    authorization_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    registration_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="general")
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    business_scenario_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("aihelms.business_scenarios.id", ondelete="SET NULL"), nullable=True
    )
    icon_url: Mapped[str] = mapped_column(String(500), default="")
    documentation_url: Mapped[str] = mapped_column(String(500), default="")
    source_url: Mapped[str] = mapped_column(String(500), default="")
    billing_type: Mapped[str] = mapped_column(String(20), default="per_call")
    internal_cost_per_call: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=0)
    external_cost_per_call: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    visibility_type: Mapped[str] = mapped_column(String(20), default="all")
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="unknown")
    last_health_check: Mapped[datetime | None] = mapped_column(nullable=True)
    health_check_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    litellm_synced: Mapped[bool] = mapped_column(Boolean, default=False)
    litellm_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    litellm_synced_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("aihelms.users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    tools: Mapped[list["McpTool"]] = relationship(back_populates="server", lazy="selectin")


class McpTool(Base):
    __tablename__ = "mcp_tools"
    __table_args__ = (
        UniqueConstraint("server_id", "tool_name"),
        {"schema": "aihelms"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    server_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.mcp_servers.id", ondelete="CASCADE"))
    tool_name: Mapped[str] = mapped_column(String(200), nullable=False)
    namespaced_name: Mapped[str] = mapped_column(String(300), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    input_schema: Mapped[dict] = mapped_column(JSONB, default=dict)
    billing_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    internal_cost_per_call: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    external_cost_per_call: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    server: Mapped["McpServer"] = relationship(back_populates="tools")


class ResourceApplication(Base):
    __tablename__ = "resource_applications"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.users.id"))
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)
    resource_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="")
    request_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    celery_task_id: Mapped[str] = mapped_column(String(100), default="")
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    retry_of_task_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("aihelms.users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    review_notes: Mapped[str] = mapped_column(Text, default="")
    approval_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(foreign_keys=[user_id], lazy="selectin")
    reviewer: Mapped["User | None"] = relationship(foreign_keys=[reviewed_by], lazy="selectin")


class McpCallLog(Base):
    __tablename__ = "mcp_call_logs"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    server_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tool_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tool_name: Mapped[str] = mapped_column(String(300), nullable=False)
    namespaced_tool_name: Mapped[str] = mapped_column(String(400), nullable=False)
    arguments: Mapped[dict] = mapped_column(JSONB, default=dict)
    request_args: Mapped[dict] = mapped_column(JSONB, default=dict)
    response_full: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="success")
    response_summary: Mapped[str] = mapped_column(Text, default="")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    internal_cost: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=0)
    external_cost: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=0)
    ai_key_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    litellm_request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    called_at: Mapped[datetime] = mapped_column(server_default=func.now())


class LlmCallLog(Base):
    __tablename__ = "llm_call_logs"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    request_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    ai_key_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    deployment_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    call_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_creation_tokens: Mapped[int] = mapped_column(Integer, default=0)
    external_cost: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=0)
    internal_cost: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ttft_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    messages: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    synced_at: Mapped[datetime] = mapped_column(server_default=func.now())


class SkillUsageLog(Base):
    __tablename__ = "skill_usage_logs"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    skill_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    ai_key_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class SyncState(Base):
    __tablename__ = "sync_state"
    __table_args__ = {"schema": "aihelms"}

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_sync_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BusinessScenario(Base):
    __tablename__ = "business_scenarios"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    icon: Mapped[str] = mapped_column(String(50), default="Target")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class SkillCategory(Base):
    __tablename__ = "skill_categories"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    skill_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    icon: Mapped[str] = mapped_column(String(20), default="📦")
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(50), default="general")
    business_scenario_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("aihelms.business_scenarios.id", ondelete="SET NULL"), nullable=True
    )
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    agent_install_prompt: Mapped[str] = mapped_column(Text, default="")
    usage_instructions: Mapped[str] = mapped_column(Text, default="")
    zip_path: Mapped[str] = mapped_column(String(500), default="")
    zip_size: Mapped[int] = mapped_column(BigInteger, default=0)
    zip_filename: Mapped[str] = mapped_column(String(200), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    install_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("aihelms.users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class AgentCategory(Base):
    __tablename__ = "agent_categories"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class AgentPlatform(Base):
    __tablename__ = "agent_platforms"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(64), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    icon: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="general")
    business_scenario_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("aihelms.business_scenarios.id", ondelete="SET NULL"), nullable=True
    )
    department_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("aihelms.departments.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("aihelms.projects.id", ondelete="SET NULL"), nullable=True
    )
    cost_attribution: Mapped[str] = mapped_column(String(20), default="owner")
    ai_key_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("aihelms.ai_keys.id", ondelete="SET NULL"), nullable=True
    )
    chat_url: Mapped[str] = mapped_column(String(500), default="")
    external_id: Mapped[str] = mapped_column(String(100), default="")
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="online")
    user_count: Mapped[int] = mapped_column(Integer, default=0)
    call_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("aihelms.users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class AgentUsageLog(Base):
    __tablename__ = "agent_usage_logs"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    agent_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.agents.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.users.id"))
    session_id: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    identity_type: Mapped[str] = mapped_column(String(16), default="user")
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    action: Mapped[str] = mapped_column(String(200), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(500), default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    request_summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())




class ExportTask(Base):
    __tablename__ = "export_tasks"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    task_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    export_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    celery_task_id: Mapped[str] = mapped_column(String(100), default="")
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    retry_of_task_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    params: Mapped[dict] = mapped_column(JSONB, default=dict)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_by_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_by_name: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApiKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    key_encrypted: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(nullable=True)


class CostSummaryDaily(Base):
    __tablename__ = "cost_summary_daily"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    summary_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    ai_key_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    department_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    project_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    server_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    cost_type: Mapped[str] = mapped_column(String(20), nullable=False)
    key_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    successful_requests: Mapped[int] = mapped_column(Integer, default=0)
    failed_requests: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    output_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    cache_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    cache_creation_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    external_cost: Mapped[Decimal] = mapped_column(Numeric(14, 6), default=0)
    internal_cost: Mapped[Decimal] = mapped_column(Numeric(14, 6), default=0)
    total_duration_ms: Mapped[int] = mapped_column(BigInteger, default=0)
    last_aggregated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class EfficiencyReport(Base):
    __tablename__ = "efficiency_reports"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    filters: Mapped[dict] = mapped_column(JSONB, default=dict)
    model_used: Mapped[str | None] = mapped_column(String(128), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    content_md: Mapped[str] = mapped_column(Text, default="")
    suggestions: Mapped[list] = mapped_column(JSONB, default=list)
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("aihelms.users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    generation_cost: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    generation_duration_ms: Mapped[int] = mapped_column(Integer, default=0)


class EfficiencySuggestion(Base):
    __tablename__ = "efficiency_suggestions"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    report_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aihelms.efficiency_reports.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    expected_impact: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    celery_task_id: Mapped[str] = mapped_column(String(100), default="")
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    retry_of_task_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status_note: Mapped[str] = mapped_column(Text, default="")
    status_updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("aihelms.users.id"), nullable=True)
    status_updated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
