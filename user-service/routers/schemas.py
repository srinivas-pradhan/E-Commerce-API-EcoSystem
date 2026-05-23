from typing import Any

from pydantic import BaseModel, EmailStr, Field


class BlueprintResponse(BaseModel):
    operation: str
    auth0_endpoint: str
    status: str = "planned"
    notes: list[str] = Field(default_factory=list)


class SelfRegistrationRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    given_name: str | None = None
    family_name: str | None = None
    user_metadata: dict[str, Any] = Field(default_factory=dict)


class RegistrationCompleteRequest(BaseModel):
    user_id: str
    verification_code: str | None = None


class MfaEnrollmentRequest(BaseModel):
    authenticator_type: str = Field(
        default="otp",
        description="Auth0 MFA authenticator type, such as otp or recovery-code.",
    )


class MfaChallengeRequest(BaseModel):
    mfa_token: str
    challenge_type: str = "otp"


class UserListQuery(BaseModel):
    page: int = Field(default=0, ge=0)
    per_page: int = Field(default=25, ge=1, le=100)
    query: str | None = None


class UserAttributeUpdateRequest(BaseModel):
    email: EmailStr | None = None
    blocked: bool | None = None
    email_verified: bool | None = None
    user_metadata: dict[str, Any] | None = None
    app_metadata: dict[str, Any] | None = None


class PasswordResetRequest(BaseModel):
    email: EmailStr
    connection: str = "Username-Password-Authentication"


class AdminMfaResetRequest(BaseModel):
    provider: str | None = Field(
        default=None,
        description="Optional Auth0 MFA provider to reset. Omit to reset all enrolled factors.",
    )


class GroupAssignmentRequest(BaseModel):
    group_id: str


class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
