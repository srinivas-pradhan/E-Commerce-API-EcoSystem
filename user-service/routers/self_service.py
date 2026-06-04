from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from auth import require_permissions
from config import settings
from routers.schemas import (
    MfaChallengeRequest,
    MfaEnrollmentRequest,
    OwnPasswordChangeRequest,
    RegistrationCompleteRequest,
    SelfRegistrationRequest,
)
from services.auth0.client import (
    Auth0AuthenticationClient,
    Auth0ClientError,
    Auth0ManagementClient,
    raise_http_error,
)

router = APIRouter(prefix="/self-service", tags=["self-service"])

CreateRegistration = Depends(require_permissions("create:registration"))
CompleteRegistration = Depends(require_permissions("complete:registration"))
ReadOwnProfile = Depends(require_permissions("read:own_profile"))
UpdateOwnProfile = Depends(require_permissions("update:own_profile"))
ReadOwnMfa = Depends(require_permissions("read:own_mfa"))
EnrollOwnMfa = Depends(require_permissions("enroll:own_mfa"))
ChallengeOwnMfa = Depends(require_permissions("challenge:own_mfa"))
DeleteOwnMfa = Depends(require_permissions("delete:own_mfa"))
ChangeOwnPassword = Depends(require_permissions("change:own_password"))


@router.post("/registration", status_code=status.HTTP_201_CREATED)
async def start_registration(
    payload: SelfRegistrationRequest,
    claims: dict[str, Any] = CreateRegistration,
):
    auth0_user = {
        "connection": payload.connection or settings.auth0_connection,
        "email": str(payload.email),
        "password": payload.password,
        "email_verified": False,
        "verify_email": True,
        "user_metadata": payload.user_metadata,
    }
    if payload.given_name:
        auth0_user["given_name"] = payload.given_name
    if payload.family_name:
        auth0_user["family_name"] = payload.family_name

    try:
        return await Auth0ManagementClient().create_user(auth0_user)
    except Auth0ClientError as error:
        raise_http_error(error)


@router.post(
    "/registration/complete",
)
async def complete_registration(
    payload: RegistrationCompleteRequest,
    claims: dict[str, Any] = CompleteRegistration,
):
    if payload.user_id != claims["sub"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot complete registration for another user",
        )

    try:
        return await Auth0ManagementClient().complete_registration(payload.user_id)
    except Auth0ClientError as error:
        raise_http_error(error)


@router.get("/profile")
async def read_profile(claims: dict[str, Any] = ReadOwnProfile):
    try:
        return await Auth0ManagementClient().get_user(claims["sub"])
    except Auth0ClientError as error:
        raise_http_error(error)


@router.patch("/profile")
async def update_profile(
    payload: dict[str, Any],
    claims: dict[str, Any] = UpdateOwnProfile,
):
    try:
        return await Auth0ManagementClient().update_user(
            claims["sub"],
            {"user_metadata": payload},
        )
    except Auth0ClientError as error:
        raise_http_error(error)


@router.post("/password-change")
async def request_password_change(
    payload: OwnPasswordChangeRequest,
    claims: dict[str, Any] = ChangeOwnPassword,
):
    try:
        return await Auth0ManagementClient().create_password_change_ticket(
            user_id=claims["sub"],
            result_url=payload.result_url,
        )
    except Auth0ClientError as error:
        raise_http_error(error)


@router.get("/mfa/enrollments")
async def list_own_mfa_enrollments(claims: dict[str, Any] = ReadOwnMfa):
    try:
        return await Auth0ManagementClient().list_user_authentication_methods(claims["sub"])
    except Auth0ClientError as error:
        raise_http_error(error)


@router.post("/mfa/enroll", status_code=status.HTTP_202_ACCEPTED)
async def enroll_mfa(
    payload: MfaEnrollmentRequest,
    claims: dict[str, Any] = EnrollOwnMfa,
):
    try:
        return await Auth0AuthenticationClient().start_mfa_enrollment(
            mfa_token=payload.mfa_token,
            authenticator_types=[payload.authenticator_type],
            oob_channels=payload.oob_channels,
            phone_number=payload.phone_number,
        )
    except Auth0ClientError as error:
        raise_http_error(error)


@router.post("/mfa/challenge", status_code=status.HTTP_202_ACCEPTED)
async def challenge_mfa(
    payload: MfaChallengeRequest,
    claims: dict[str, Any] = ChallengeOwnMfa,
):
    try:
        return await Auth0AuthenticationClient().challenge_mfa(
            mfa_token=payload.mfa_token,
            challenge_type=payload.challenge_type,
            authenticator_id=payload.authenticator_id,
        )
    except Auth0ClientError as error:
        raise_http_error(error)


@router.delete("/mfa/enrollments/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_own_mfa_enrollment(
    enrollment_id: str,
    claims: dict[str, Any] = DeleteOwnMfa,
):
    try:
        await Auth0ManagementClient().delete_user_authentication_method(
            claims["sub"],
            enrollment_id,
        )
    except Auth0ClientError as error:
        raise_http_error(error)
