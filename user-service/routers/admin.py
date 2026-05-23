from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from auth import require_permissions
from routers.schemas import (
    AdminMfaResetRequest,
    GroupAssignmentRequest,
    GroupCreateRequest,
    PasswordResetRequest,
    UserAttributeUpdateRequest,
    UserListQuery,
)
from services.auth0.client import Auth0ClientError, Auth0ManagementClient, raise_http_error

router = APIRouter(prefix="/admin", tags=["user-admin"])


UserRead = Depends(require_permissions("read:users"))
UserWrite = Depends(require_permissions("update:users"))
PasswordReset = Depends(require_permissions("reset:passwords"))
MfaReset = Depends(require_permissions("reset:mfa"))
GroupRead = Depends(require_permissions("read:groups"))
GroupCreate = Depends(require_permissions("create:groups"))
GroupUpdate = Depends(require_permissions("update:groups"))
GroupDelete = Depends(require_permissions("delete:groups"))


@router.get("/users")
async def list_users(
    page: Annotated[int, Query(ge=0)] = 0,
    per_page: Annotated[int, Query(ge=1, le=100)] = 25,
    query: str | None = None,
    claims: dict[str, Any] = UserRead,
):
    UserListQuery(page=page, per_page=per_page, query=query)
    try:
        return await Auth0ManagementClient().list_users(
            page=page,
            per_page=per_page,
            query=query,
        )
    except Auth0ClientError as error:
        raise_http_error(error)


@router.get("/users/{user_id}")
async def read_user(user_id: str, claims: dict[str, Any] = UserRead):
    try:
        return await Auth0ManagementClient().get_user(user_id)
    except Auth0ClientError as error:
        raise_http_error(error)


@router.patch("/users/{user_id}/attributes")
async def update_user_attributes(
    user_id: str,
    payload: UserAttributeUpdateRequest,
    claims: dict[str, Any] = UserWrite,
):
    auth0_payload = payload.model_dump(exclude_none=True)
    try:
        return await Auth0ManagementClient().update_user(user_id, auth0_payload)
    except Auth0ClientError as error:
        raise_http_error(error)


@router.post("/users/{user_id}/password-reset")
async def reset_user_password(
    user_id: str,
    payload: PasswordResetRequest,
    claims: dict[str, Any] = PasswordReset,
):
    try:
        return await Auth0ManagementClient().create_password_change_ticket(
            user_id=user_id,
            email=str(payload.email),
            connection_id=payload.connection_id,
            result_url=payload.result_url,
        )
    except Auth0ClientError as error:
        raise_http_error(error)


@router.post("/users/{user_id}/mfa/reset")
async def reset_user_mfa(
    user_id: str,
    payload: AdminMfaResetRequest,
    claims: dict[str, Any] = MfaReset,
):
    try:
        return await Auth0ManagementClient().reset_user_mfa(
            user_id,
            authentication_method_id=payload.authentication_method_id,
        )
    except Auth0ClientError as error:
        raise_http_error(error)


@router.get("/groups")
async def list_groups(claims: dict[str, Any] = GroupRead):
    try:
        return await Auth0ManagementClient().list_roles()
    except Auth0ClientError as error:
        raise_http_error(error)


@router.post("/groups", status_code=status.HTTP_201_CREATED)
async def create_group(payload: GroupCreateRequest, claims: dict[str, Any] = GroupCreate):
    try:
        return await Auth0ManagementClient().create_role(
            name=payload.name,
            description=payload.description,
        )
    except Auth0ClientError as error:
        raise_http_error(error)


@router.post("/users/{user_id}/groups", status_code=status.HTTP_204_NO_CONTENT)
async def add_user_to_group(
    user_id: str,
    payload: GroupAssignmentRequest,
    claims: dict[str, Any] = GroupUpdate,
):
    try:
        await Auth0ManagementClient().assign_roles_to_user(user_id, [payload.group_id])
    except Auth0ClientError as error:
        raise_http_error(error)


@router.delete("/users/{user_id}/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_from_group(
    user_id: str,
    group_id: str,
    claims: dict[str, Any] = GroupDelete,
):
    try:
        await Auth0ManagementClient().remove_roles_from_user(user_id, [group_id])
    except Auth0ClientError as error:
        raise_http_error(error)
