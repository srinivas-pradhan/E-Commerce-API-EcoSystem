from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, model_validator


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
    connection: str | None = None
    user_metadata: dict[str, Any] = Field(default_factory=dict)


class RegistrationCompleteRequest(BaseModel):
    user_id: str
    verification_code: str | None = None


class MfaEnrollmentRequest(BaseModel):
    mfa_token: str
    authenticator_type: Literal["otp", "oob"] = Field(
        default="otp",
        description="Auth0 MFA authenticator type. Use otp for authenticator apps or oob for SMS, voice, or push.",
    )
    oob_channels: list[Literal["sms", "voice", "auth0"]] | None = Field(
        default=None,
        description="Required for oob enrollment. Use sms, voice, or auth0 for Guardian push.",
    )
    phone_number: str | None = Field(
        default=None,
        description="Required for oob sms or voice enrollment. Use E.164 format.",
    )

    @model_validator(mode="after")
    def validate_oob_enrollment(self):
        if self.authenticator_type != "oob":
            return self

        if not self.oob_channels:
            raise ValueError("oob_channels is required when authenticator_type is oob")

        phone_channels = {"sms", "voice"}
        if phone_channels.intersection(self.oob_channels) and not self.phone_number:
            raise ValueError("phone_number is required for sms or voice MFA enrollment")

        return self


class MfaChallengeRequest(BaseModel):
    mfa_token: str
    challenge_type: str = "otp"
    authenticator_id: str | None = None


class OwnPasswordChangeRequest(BaseModel):
    result_url: str | None = None


class UserListQuery(BaseModel):
    page: int = Field(default=0, ge=0)
    per_page: int = Field(default=25, ge=1, le=100)
    query: str | None = None
    start_query: str | None = None
    end_query: str | None = None


class GroupListQuery(BaseModel):
    page: int = Field(default=0, ge=0)
    per_page: int = Field(default=25, ge=1, le=100)
    query: str | None = None
    start_query: str | None = None
    end_query: str | None = None


class UserAttributeUpdateRequest(BaseModel):
    email: EmailStr | None = None
    blocked: bool | None = None
    email_verified: bool | None = None
    user_metadata: dict[str, Any] | None = None
    app_metadata: dict[str, Any] | None = None


class PasswordResetRequest(BaseModel):
    email: EmailStr
    connection_id: str | None = None
    result_url: str | None = None


class AdminMfaResetRequest(BaseModel):
    authentication_method_id: str | None = Field(
        default=None,
        description="Optional Auth0 authentication method id. Omit to reset all methods.",
    )


class GroupAssignmentRequest(BaseModel):
    group_id: str


class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
