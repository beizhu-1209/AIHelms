from pydantic import BaseModel, Field, field_validator


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("邮箱格式不正确")
        return v.lower()


class UpdateUserRequest(BaseModel):
    email: str | None = Field(None, max_length=255)
    is_active: bool | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v is not None and "@" not in v:
            raise ValueError("邮箱格式不正确")
        return v.lower() if v else v


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128)


class UpdateUserRolesRequest(BaseModel):
    role_ids: list[int]


class UpdateUserOrganizationsRequest(BaseModel):
    organization_ids: list[int]


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: str
    roles: list[dict] = []
    organizations: list[dict] = []
