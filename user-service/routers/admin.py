from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from auth import require_permissions
from config import settings
from routers.schemas import (
    AdminMfaResetRequest,
    GroupAssignmentRequest,
    GroupCreateRequest,
    GroupListQuery,
    GroupUpdateRequest,
    PasswordResetRequest,
    PermissionCreateRequest,
    PermissionUpdateRequest,
    UserDeleteWorkflowRequest,
    UserDisableRequest,
    UserAttributeUpdateRequest,
    UserListQuery,
    UserPermissionAssignmentRequest,
)
from services.audit import audit_admin_action
from services.auth0.client import Auth0ClientError, Auth0ManagementClient, raise_http_error
from services.permission_cache import permission_cache

router = APIRouter(prefix="/admin", tags=["user-admin"])


UserRead = Depends(require_permissions("read:users"))
UserWrite = Depends(require_permissions("update:users"))
UserDisable = Depends(require_permissions("disable:users"))
UserDeleteWorkflow = Depends(require_permissions("delete:users"))
PasswordReset = Depends(require_permissions("reset:passwords"))
MfaReset = Depends(require_permissions("reset:mfa"))
GroupRead = Depends(require_permissions("read:groups"))
GroupCreate = Depends(require_permissions("create:groups"))
GroupUpdate = Depends(require_permissions("update:groups"))
GroupDelete = Depends(require_permissions("delete:groups"))
PermissionCreate = Depends(require_permissions("create:permissions"))
PermissionRead = Depends(require_permissions("read:permissions"))
PermissionUpdate = Depends(require_permissions("update:permissions"))
PermissionDelete = Depends(require_permissions("delete:permissions"))
PermissionAssign = Depends(require_permissions("assign:permissions"))
PermissionUnassign = Depends(require_permissions("unassign:permissions"))


@router.get("/users")
async def list_users(
    page: Annotated[int, Query(ge=0)] = 0,
    per_page: Annotated[int, Query(ge=1, le=100)] = 25,
    query: str | None = None,
    start_query: str | None = None,
    end_query: str | None = None,
    claims: dict[str, Any] = UserRead,
):
    UserListQuery(
        page=page,
        per_page=per_page,
        query=query,
        start_query=start_query,
        end_query=end_query,
    )
    try:
        return await Auth0ManagementClient().list_users(
            page=page,
            per_page=per_page,
            query=query,
            start_query=start_query,
            end_query=end_query,
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
        result = await Auth0ManagementClient().update_user(user_id, auth0_payload)
        audit_admin_action(
            action="update_user_attributes",
            actor=claims.get("sub"),
            target=user_id,
            metadata={"fields": sorted(auth0_payload)},
        )
        return result
    except Auth0ClientError as error:
        raise_http_error(error)


@router.post("/users/{user_id}/disable")
async def disable_user(
    user_id: str,
    payload: UserDisableRequest,
    claims: dict[str, Any] = UserDisable,
):
    try:
        result = await Auth0ManagementClient().disable_user(
            user_id,
            reason=payload.reason,
            actor=claims.get("sub"),
        )
        audit_admin_action(
            action="disable_user",
            actor=claims.get("sub"),
            target=user_id,
            metadata={"reason": payload.reason},
        )
        return result
    except Auth0ClientError as error:
        raise_http_error(error)


@router.post("/users/{user_id}/delete-workflow")
async def start_user_delete_workflow(
    user_id: str,
    payload: UserDeleteWorkflowRequest,
    claims: dict[str, Any] = UserDeleteWorkflow,
):
    retention_days = payload.retention_days or settings.user_delete_workflow_retention_days
    try:
        result = await Auth0ManagementClient().start_user_delete_workflow(
            user_id,
            retention_days=retention_days,
            reason=payload.reason,
            actor=claims.get("sub"),
        )
        audit_admin_action(
            action="start_user_delete_workflow",
            actor=claims.get("sub"),
            target=user_id,
            metadata={"reason": payload.reason, "retention_days": retention_days},
        )
        return result
    except Auth0ClientError as error:
        raise_http_error(error)


@router.post("/users/{user_id}/password-reset")
async def reset_user_password(
    user_id: str,
    payload: PasswordResetRequest,
    claims: dict[str, Any] = PasswordReset,
):
    try:
        result = await Auth0ManagementClient().create_password_change_ticket(
            user_id=user_id,
            email=str(payload.email),
            connection_id=payload.connection_id,
            result_url=payload.result_url,
        )
        audit_admin_action(action="reset_user_password", actor=claims.get("sub"), target=user_id)
        return result
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
async def list_groups(
    page: Annotated[int, Query(ge=0)] = 0,
    per_page: Annotated[int, Query(ge=1, le=100)] = 25,
    query: str | None = None,
    start_query: str | None = None,
    end_query: str | None = None,
    claims: dict[str, Any] = GroupRead,
):
    GroupListQuery(
        page=page,
        per_page=per_page,
        query=query,
        start_query=start_query,
        end_query=end_query,
    )
    try:
        return await Auth0ManagementClient().list_roles(
            page=page,
            per_page=per_page,
            query=query,
            start_query=start_query,
            end_query=end_query,
        )
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


@router.get("/groups/{group_id}")
async def read_group(group_id: str, claims: dict[str, Any] = GroupRead):
    try:
        return await Auth0ManagementClient().get_role(group_id)
    except Auth0ClientError as error:
        raise_http_error(error)


@router.patch("/groups/{group_id}")
async def update_group(
    group_id: str,
    payload: GroupUpdateRequest,
    claims: dict[str, Any] = GroupUpdate,
):
    try:
        return await Auth0ManagementClient().update_role(
            group_id,
            payload.model_dump(exclude_none=True),
        )
    except Auth0ClientError as error:
        raise_http_error(error)


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(group_id: str, claims: dict[str, Any] = GroupDelete):
    try:
        await Auth0ManagementClient().delete_role(group_id)
    except Auth0ClientError as error:
        raise_http_error(error)


@router.get("/groups/{group_id}/users")
async def list_group_users(
    group_id: str,
    page: Annotated[int, Query(ge=0)] = 0,
    per_page: Annotated[int, Query(ge=1, le=100)] = 25,
    claims: dict[str, Any] = GroupRead,
):
    try:
        return await Auth0ManagementClient().list_role_users(
            group_id,
            page=page,
            per_page=per_page,
        )
    except Auth0ClientError as error:
        raise_http_error(error)


@router.post("/permissions", status_code=status.HTTP_201_CREATED)
async def create_permission(payload: PermissionCreateRequest, claims: dict[str, Any] = PermissionCreate):
    try:
        result = await Auth0ManagementClient().create_api_permission(
            value=payload.value,
            description=payload.description,
        )
        audit_admin_action(
            action="create_permission",
            actor=claims.get("sub"),
            target=payload.value,
        )
        return result
    except Auth0ClientError as error:
        raise_http_error(error)


@router.patch("/permissions/{permission}")
async def update_permission(
    permission: str,
    payload: PermissionUpdateRequest,
    claims: dict[str, Any] = PermissionUpdate,
):
    try:
        result = await Auth0ManagementClient().update_api_permission(
            value=permission,
            description=payload.description,
        )
        audit_admin_action(
            action="update_permission",
            actor=claims.get("sub"),
            target=permission,
        )
        return result
    except Auth0ClientError as error:
        raise_http_error(error)


@router.delete("/permissions/{permission}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(permission: str, claims: dict[str, Any] = PermissionDelete):
    try:
        await Auth0ManagementClient().delete_api_permission(value=permission)
        audit_admin_action(action="delete_permission", actor=claims.get("sub"), target=permission)
    except Auth0ClientError as error:
        raise_http_error(error)


@router.post("/users/{user_id}/permissions", status_code=status.HTTP_204_NO_CONTENT)
async def assign_permissions_to_user(
    user_id: str,
    payload: UserPermissionAssignmentRequest,
    claims: dict[str, Any] = PermissionAssign,
):
    try:
        await Auth0ManagementClient().assign_permissions_to_user(
            user_id,
            payload.permissions,
        )
        permission_cache.invalidate_user(user_id)
        audit_admin_action(
            action="assign_permissions_to_user",
            actor=claims.get("sub"),
            target=user_id,
            metadata={"permissions": payload.permissions},
        )
    except Auth0ClientError as error:
        raise_http_error(error)


@router.delete("/users/{user_id}/permissions", status_code=status.HTTP_204_NO_CONTENT)
async def remove_permissions_from_user(
    user_id: str,
    payload: UserPermissionAssignmentRequest,
    claims: dict[str, Any] = PermissionUnassign,
):
    try:
        await Auth0ManagementClient().remove_permissions_from_user(
            user_id,
            payload.permissions,
        )
        permission_cache.invalidate_user(user_id)
        audit_admin_action(
            action="remove_permissions_from_user",
            actor=claims.get("sub"),
            target=user_id,
            metadata={"permissions": payload.permissions},
        )
    except Auth0ClientError as error:
        raise_http_error(error)


@router.get("/users/{user_id}/permissions")
async def list_user_permissions(
    user_id: str,
    page: Annotated[int, Query(ge=0)] = 0,
    per_page: Annotated[int, Query(ge=1, le=100)] = 25,
    use_cache: bool = True,
    claims: dict[str, Any] = PermissionRead,
):
    try:
        if use_cache:
            cached = permission_cache.get(user_id, page, per_page)
            if cached is not None:
                return cached

        result = await Auth0ManagementClient().list_user_permissions(
            user_id,
            page=page,
            per_page=per_page,
        )
        permission_cache.set(user_id, page, per_page, result)
        return result
    except Auth0ClientError as error:
        raise_http_error(error)


@router.get("/users/{user_id}/groups")
async def list_user_groups(
    user_id: str,
    page: Annotated[int, Query(ge=0)] = 0,
    per_page: Annotated[int, Query(ge=1, le=100)] = 25,
    claims: dict[str, Any] = GroupRead,
):
    try:
        return await Auth0ManagementClient().list_user_roles(
            user_id,
            page=page,
            per_page=per_page,
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
