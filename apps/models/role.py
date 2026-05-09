from pydantic import BaseModel, Field


class CreateRoleRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=128)
    description: str = Field("", max_length=500)


class UpdateRoleRequest(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = Field(None, max_length=500)


class UpdateRolePermissionsRequest(BaseModel):
    permission_ids: list[int]


class RoleResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: str
    is_system: bool
    created_at: str
    permissions: list[dict] = []


class PermissionResponse(BaseModel):
    id: int
    code: str
    name: str
    resource: str
    action: str
    description: str
