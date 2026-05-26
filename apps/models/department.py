from pydantic import BaseModel, Field


class CreateDepartmentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    parent_id: int | None = None
    description: str = Field("", max_length=500)


class UpdateDepartmentRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = Field(None, max_length=500)
    sort_order: int | None = None
    is_active: bool | None = None


class UpdateDepartmentManagersRequest(BaseModel):
    manager_user_ids: list[int]


class DepartmentMemberRequest(BaseModel):
    user_id: int
