from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field("", max_length=500)


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = Field(None, max_length=500)
    is_active: bool | None = None


class ProjectMemberRequest(BaseModel):
    user_id: int
