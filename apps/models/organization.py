from pydantic import BaseModel, Field, field_validator


class CreateOrganizationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    type: str = Field(..., pattern="^(department|group)$")
    parent_id: int | None = None
    description: str = Field("", max_length=500)
    sort_order: int = 0

    @field_validator("parent_id")
    @classmethod
    def validate_parent_for_group(cls, v: int | None, info) -> int | None:
        if info.data.get("type") == "group" and v is not None:
            raise ValueError("项目组不能有父级")
        return v


class UpdateOrganizationRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = Field(None, max_length=500)
    sort_order: int | None = None
    is_active: bool | None = None


class UpdateOrgManagersRequest(BaseModel):
    manager_user_ids: list[int]


class OrganizationResponse(BaseModel):
    id: int
    name: str
    type: str
    parent_id: int | None
    description: str
    sort_order: int
    is_active: bool
    created_at: str
    updated_at: str
    managers: list[dict] = []


class OrgTreeNode(BaseModel):
    id: int
    name: str
    type: str
    description: str
    sort_order: int
    is_active: bool
    managers: list[dict] = []
    children: list["OrgTreeNode"] = []
