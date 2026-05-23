from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth import require_permissions
from routers.schemas import (
    AdminMfaResetRequest,
    BlueprintResponse,
    GroupAssignmentRequest,
    GroupCreateRequest,
    PasswordResetRequest,
    UserAttributeUpdateRequest,
    UserListQuery,
)

router = APIRouter(prefix="/admin", tags=["user-admin"])


def planned(operation: str, auth0_endpoint: str, notes: list[str]) -> BlueprintResponse:
    return BlueprintResponse(
        operation=operation,
        auth0_endpoint=auth0_endpoint,
        notes=notes,
    )


UserRead = Depends(require_permissions("read:users"))
UserWrite = Depends(require_permissions("update:users"))
PasswordReset = Depends(require_permissions("reset:passwords"))
MfaReset = Depends(require_permissions("reset:mfa"))
GroupRead = Depends(require_permissions("read:groups"))
GroupCreate = Depends(require_permissions("create:groups"))
GroupUpdate = Depends(require_permissions("update:groups"))
GroupDelete = Depends(require_permissions("delete:groups"))


@router.get("/users", response_model=BlueprintResponse)
async def list_users(
    page: Annotated[int, Query(ge=0)] = 0,
    per_page: Annotated[int, Query(ge=1, le=100)] = 25,
    query: str | None = None,
    claims: dict[str, Any] = UserRead,
):
    UserListQuery(page=page, per_page=per_page, query=query)
    return planned(
        operation="list users as admin",
        auth0_endpoint="GET /api/v2/users",
        notes=[
            "Pass page, per_page, and optional Lucene query to Auth0.",
            "Return normalized user summaries rather than raw Auth0 payloads.",
        ],
    )


@router.get("/users/{user_id}", response_model=BlueprintResponse)
async def read_user(user_id: str, claims: dict[str, Any] = UserRead):
    return planned(
        operation="read user as admin",
        auth0_endpoint="GET /api/v2/users/{id}",
        notes=["Fetch one Auth0 user by id and map fields for admin display."],
    )


@router.patch("/users/{user_id}/attributes", response_model=BlueprintResponse)
async def update_user_attributes(
    user_id: str,
    payload: UserAttributeUpdateRequest,
    claims: dict[str, Any] = UserWrite,
):
    return planned(
        operation="modify user attributes as admin",
        auth0_endpoint="PATCH /api/v2/users/{id}",
        notes=[
            "Allow admin-controlled profile, blocked, email_verified, metadata updates.",
            "Audit admin identity from token claims before calling Auth0.",
        ],
    )


@router.post("/users/{user_id}/password-reset", response_model=BlueprintResponse)
async def reset_user_password(
    user_id: str,
    payload: PasswordResetRequest,
    claims: dict[str, Any] = PasswordReset,
):
    return planned(
        operation="send password reset as admin",
        auth0_endpoint="POST /dbconnections/change_password",
        notes=[
            "Send Auth0 password reset email for the user's database connection.",
            "Use user_id for audit correlation; Auth0 change_password uses email and connection.",
        ],
    )


@router.post("/users/{user_id}/mfa/reset", response_model=BlueprintResponse)
async def reset_user_mfa(
    user_id: str,
    payload: AdminMfaResetRequest,
    claims: dict[str, Any] = MfaReset,
):
    return planned(
        operation="reset user MFA as admin",
        auth0_endpoint="DELETE /api/v2/users/{id}/multifactor/{provider}",
        notes=[
            "List enrolled factors when provider is omitted.",
            "Delete selected Auth0 MFA enrollment provider for the user.",
        ],
    )


@router.get("/groups", response_model=BlueprintResponse)
async def list_groups(claims: dict[str, Any] = GroupRead):
    return planned(
        operation="list user groups",
        auth0_endpoint="GET /api/v2/roles or GET /api/v2/organizations",
        notes=[
            "Auth0 has roles and organizations, not generic groups.",
            "Decide whether this app maps groups to roles, organizations, or app_metadata.",
        ],
    )


@router.post("/groups", response_model=BlueprintResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_group(payload: GroupCreateRequest, claims: dict[str, Any] = GroupCreate):
    return planned(
        operation="create user group",
        auth0_endpoint="POST /api/v2/roles or POST /api/v2/organizations",
        notes=["Create the selected Auth0 grouping primitive after the mapping is chosen."],
    )


@router.post("/users/{user_id}/groups", response_model=BlueprintResponse)
async def add_user_to_group(
    user_id: str,
    payload: GroupAssignmentRequest,
    claims: dict[str, Any] = GroupUpdate,
):
    return planned(
        operation="add user to group",
        auth0_endpoint="POST /api/v2/users/{id}/roles or POST /api/v2/organizations/{id}/members",
        notes=["Assign the user to the mapped Auth0 role or organization."],
    )


@router.delete("/users/{user_id}/groups/{group_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def remove_user_from_group(
    user_id: str,
    group_id: str,
    claims: dict[str, Any] = GroupDelete,
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Blueprint only: implement Auth0 role or organization removal after group mapping is chosen.",
    )
