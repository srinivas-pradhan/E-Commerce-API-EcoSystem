from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from auth import require_permissions
from routers.schemas import (
    BlueprintResponse,
    MfaChallengeRequest,
    MfaEnrollmentRequest,
    RegistrationCompleteRequest,
    SelfRegistrationRequest,
)

router = APIRouter(prefix="/self-service", tags=["self-service"])

CreateRegistration = Depends(require_permissions("create:registration"))
CompleteRegistration = Depends(require_permissions("complete:registration"))
ReadOwnProfile = Depends(require_permissions("read:own_profile"))
UpdateOwnProfile = Depends(require_permissions("update:own_profile"))
EnrollOwnMfa = Depends(require_permissions("enroll:own_mfa"))
ChallengeOwnMfa = Depends(require_permissions("challenge:own_mfa"))
DeleteOwnMfa = Depends(require_permissions("delete:own_mfa"))


def planned(operation: str, auth0_endpoint: str, notes: list[str]) -> BlueprintResponse:
    return BlueprintResponse(
        operation=operation,
        auth0_endpoint=auth0_endpoint,
        notes=notes,
    )


@router.post("/registration", response_model=BlueprintResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_registration(
    payload: SelfRegistrationRequest,
    claims: dict[str, Any] = CreateRegistration,
):
    return planned(
        operation="start self-service registration",
        auth0_endpoint="POST /api/v2/users",
        notes=[
            "Create an Auth0 database-connection user.",
            "Requires a trusted pre-registration or service token.",
            "Store allowed profile fields in user_metadata.",
            "Trigger verification email after user creation.",
        ],
    )


@router.post(
    "/registration/complete",
    response_model=BlueprintResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def complete_registration(
    payload: RegistrationCompleteRequest,
    claims: dict[str, Any] = CompleteRegistration,
):
    return planned(
        operation="complete self-service registration",
        auth0_endpoint="PATCH /api/v2/users/{id}",
        notes=[
            "Validate any app-specific registration proof before marking completion.",
            "Update app_metadata.registration_completed when the flow is satisfied.",
        ],
    )


@router.get("/profile")
async def read_profile(claims: dict[str, Any] = ReadOwnProfile):
    return claims


@router.patch("/profile", response_model=BlueprintResponse)
async def update_profile(
    payload: dict[str, Any],
    claims: dict[str, Any] = UpdateOwnProfile,
):
    return planned(
        operation="update own profile metadata",
        auth0_endpoint="PATCH /api/v2/users/{id}",
        notes=[
            "Resolve Auth0 user id from the token subject claim.",
            "Allow only safe self-editable fields.",
            "Write user-controlled fields to user_metadata.",
        ],
    )


@router.post("/mfa/enroll", response_model=BlueprintResponse, status_code=status.HTTP_202_ACCEPTED)
async def enroll_mfa(
    payload: MfaEnrollmentRequest,
    claims: dict[str, Any] = EnrollOwnMfa,
):
    return planned(
        operation="enroll self-service MFA factor",
        auth0_endpoint="POST /mfa/associate",
        notes=[
            "Use Auth0 MFA API with the user's MFA token during an MFA enrollment flow.",
            "Persist enrollment state in Auth0 after the challenge is verified.",
        ],
    )


@router.post("/mfa/challenge", response_model=BlueprintResponse, status_code=status.HTTP_202_ACCEPTED)
async def challenge_mfa(
    payload: MfaChallengeRequest,
    claims: dict[str, Any] = ChallengeOwnMfa,
):
    return planned(
        operation="challenge self-service MFA factor",
        auth0_endpoint="POST /mfa/challenge",
        notes=[
            "Submit challenge using Auth0 MFA token.",
            "Exchange verified challenge for tokens through Auth0 OAuth flow.",
        ],
    )


@router.delete("/mfa/enrollments/{enrollment_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def delete_own_mfa_enrollment(
    enrollment_id: str,
    claims: dict[str, Any] = DeleteOwnMfa,
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Blueprint only: implement Auth0 MFA enrollment deletion for the authenticated user.",
    )
