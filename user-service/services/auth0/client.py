from typing import Any
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import httpx
from fastapi import HTTPException, status

from config import settings


class Auth0ClientError(Exception):
    def __init__(self, status_code: int, detail: Any):
        self.status_code = status_code
        self.detail = detail
        super().__init__(str(detail))


def raise_http_error(error: Auth0ClientError) -> None:
    if 400 <= error.status_code < 500:
        status_code = error.status_code
    else:
        status_code = status.HTTP_502_BAD_GATEWAY

    raise HTTPException(status_code=status_code, detail=error.detail)


class Auth0BaseClient:
    def __init__(self, timeout: float = 10):
        self.timeout = timeout

    @property
    def tenant_base_url(self) -> str:
        return settings.auth0_issuer.rstrip("/")

    async def request(
        self,
        method: str,
        url: str,
        *,
        token: str | None = None,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                json=json,
                params=params,
            )

        if response.status_code >= 400:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise Auth0ClientError(response.status_code, detail)

        if response.status_code == status.HTTP_204_NO_CONTENT or not response.content:
            return None

        return response.json()

    def path_segment(self, value: str) -> str:
        return quote(value, safe="")


def compose_search_query(
    query: str | None = None,
    start_query: str | None = None,
    end_query: str | None = None,
) -> str | None:
    clauses = [clause.strip() for clause in [query, start_query, end_query] if clause and clause.strip()]
    if not clauses:
        return None

    return " AND ".join(f"({clause})" for clause in clauses)


class Auth0ManagementClient(Auth0BaseClient):
    def __init__(self, timeout: float = 10):
        super().__init__(timeout=timeout)
        self._management_token: str | None = None

    @property
    def management_base_url(self) -> str:
        return settings.auth0_management_audience.rstrip("/")

    async def management_token(self) -> str:
        if self._management_token:
            return self._management_token

        if settings.auth0_client_secret is None:
            raise Auth0ClientError(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Auth0 client secret is not configured",
            )

        response = await self.request(
            "POST",
            f"{self.tenant_base_url}/oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": settings.auth0_client_id,
                "client_secret": settings.auth0_client_secret.get_secret_value(),
                "audience": settings.auth0_management_audience,
            },
        )
        self._management_token = response["access_token"]
        return self._management_token

    async def management_request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        token = await self.management_token()
        return await self.request(
            method,
            f"{self.management_base_url}{path}",
            token=token,
            json=json,
            params=params,
        )

    async def create_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.management_request("POST", "/users", json=payload)

    async def get_user(self, user_id: str) -> dict[str, Any]:
        return await self.management_request("GET", f"/users/{self.path_segment(user_id)}")

    async def list_users(
        self,
        *,
        page: int = 0,
        per_page: int = 25,
        query: str | None = None,
        start_query: str | None = None,
        end_query: str | None = None,
    ) -> Any:
        params: dict[str, Any] = {
            "page": page,
            "per_page": per_page,
            "include_totals": "true",
        }
        composed_query = compose_search_query(query, start_query, end_query)
        if composed_query:
            params["q"] = composed_query
            params["search_engine"] = "v3"

        return await self.management_request("GET", "/users", params=params)

    async def update_user(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.management_request(
            "PATCH",
            f"/users/{self.path_segment(user_id)}",
            json=payload,
        )

    async def disable_user(
        self,
        user_id: str,
        *,
        reason: str | None = None,
        actor: str | None = None,
    ) -> dict[str, Any]:
        disabled_at = datetime.now(UTC).isoformat()
        return await self.update_user(
            user_id,
            {
                "blocked": True,
                "app_metadata": {
                    "user_service_workflow": {
                        "state": "disabled",
                        "disabled_at": disabled_at,
                        "disabled_by": actor,
                        "reason": reason,
                    }
                },
            },
        )

    async def start_user_delete_workflow(
        self,
        user_id: str,
        *,
        retention_days: int,
        reason: str | None = None,
        actor: str | None = None,
    ) -> dict[str, Any]:
        requested_at = datetime.now(UTC)
        delete_after = requested_at + timedelta(days=retention_days)
        return await self.update_user(
            user_id,
            {
                "blocked": True,
                "app_metadata": {
                    "user_service_workflow": {
                        "state": "delete_requested",
                        "delete_requested_at": requested_at.isoformat(),
                        "delete_after": delete_after.isoformat(),
                        "delete_requested_by": actor,
                        "retention_days": retention_days,
                        "reason": reason,
                    }
                },
            },
        )

    async def complete_registration(self, user_id: str) -> dict[str, Any]:
        return await self.update_user(
            user_id,
            {"app_metadata": {"registration_completed": True}},
        )

    async def create_password_change_ticket(
        self,
        *,
        user_id: str | None = None,
        email: str | None = None,
        connection_id: str | None = None,
        result_url: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "client_id": settings.auth0_client_id,
            "mark_email_as_verified": False,
        }
        if user_id:
            payload["user_id"] = user_id
        if email:
            payload["email"] = email
        if connection_id:
            payload["connection_id"] = connection_id
        if result_url:
            payload["result_url"] = result_url

        return await self.management_request(
            "POST",
            "/tickets/password-change",
            json=payload,
        )

    async def list_roles(
        self,
        *,
        page: int = 0,
        per_page: int = 25,
        query: str | None = None,
        start_query: str | None = None,
        end_query: str | None = None,
    ) -> Any:
        name_filter = " ".join(
            clause.strip() for clause in [query, start_query, end_query] if clause and clause.strip()
        )
        params: dict[str, Any] = {
            "page": page,
            "per_page": per_page,
            "include_totals": "true",
        }
        if name_filter:
            params["name_filter"] = name_filter

        return await self.management_request(
            "GET",
            "/roles",
            params=params,
        )

    async def create_role(self, *, name: str, description: str | None = None) -> dict[str, Any]:
        return await self.management_request(
            "POST",
            "/roles",
            json={"name": name, "description": description or ""},
        )

    async def get_role(self, role_id: str) -> dict[str, Any]:
        return await self.management_request("GET", f"/roles/{self.path_segment(role_id)}")

    async def update_role(self, role_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.management_request(
            "PATCH",
            f"/roles/{self.path_segment(role_id)}",
            json=payload,
        )

    async def delete_role(self, role_id: str) -> None:
        await self.management_request("DELETE", f"/roles/{self.path_segment(role_id)}")

    async def list_role_users(
        self,
        role_id: str,
        *,
        page: int = 0,
        per_page: int = 25,
    ) -> Any:
        return await self.management_request(
            "GET",
            f"/roles/{self.path_segment(role_id)}/users",
            params={
                "page": page,
                "per_page": per_page,
                "include_totals": "true",
            },
        )

    async def list_user_roles(
        self,
        user_id: str,
        *,
        page: int = 0,
        per_page: int = 25,
    ) -> Any:
        return await self.management_request(
            "GET",
            f"/users/{self.path_segment(user_id)}/roles",
            params={
                "page": page,
                "per_page": per_page,
                "include_totals": "true",
            },
        )

    async def get_resource_server_by_identifier(self, identifier: str) -> dict[str, Any]:
        resource_servers = await self.management_request(
            "GET",
            "/resource-servers",
            params={"identifier": identifier},
        )
        for resource_server in resource_servers:
            if resource_server.get("identifier") == identifier:
                return resource_server

        raise Auth0ClientError(
            status.HTTP_404_NOT_FOUND,
            {"message": f"Auth0 resource server not found for identifier {identifier}"},
        )

    async def create_api_permission(
        self,
        *,
        value: str,
        description: str,
        audience: str | None = None,
    ) -> dict[str, Any]:
        resource_server = await self.get_resource_server_by_identifier(audience or settings.auth0_audience)
        scopes = list(resource_server.get("scopes", []))

        if not any(scope.get("value") == value for scope in scopes):
            scopes.append({"value": value, "description": description})

        resource_server_id = self.path_segment(resource_server["id"])
        return await self.management_request(
            "PATCH",
            f"/resource-servers/{resource_server_id}",
            json={"scopes": scopes},
        )

    async def update_api_permission(
        self,
        *,
        value: str,
        description: str,
        audience: str | None = None,
    ) -> dict[str, Any]:
        resource_server = await self.get_resource_server_by_identifier(audience or settings.auth0_audience)
        scopes = list(resource_server.get("scopes", []))
        found = False

        for scope in scopes:
            if scope.get("value") == value:
                scope["description"] = description
                found = True
                break

        if not found:
            raise Auth0ClientError(
                status.HTTP_404_NOT_FOUND,
                {"message": f"Auth0 API permission not found: {value}"},
            )

        resource_server_id = self.path_segment(resource_server["id"])
        return await self.management_request(
            "PATCH",
            f"/resource-servers/{resource_server_id}",
            json={"scopes": scopes},
        )

    async def delete_api_permission(
        self,
        *,
        value: str,
        audience: str | None = None,
    ) -> dict[str, Any]:
        resource_server = await self.get_resource_server_by_identifier(audience or settings.auth0_audience)
        scopes = list(resource_server.get("scopes", []))
        filtered_scopes = [scope for scope in scopes if scope.get("value") != value]

        if len(filtered_scopes) == len(scopes):
            raise Auth0ClientError(
                status.HTTP_404_NOT_FOUND,
                {"message": f"Auth0 API permission not found: {value}"},
            )

        resource_server_id = self.path_segment(resource_server["id"])
        return await self.management_request(
            "PATCH",
            f"/resource-servers/{resource_server_id}",
            json={"scopes": filtered_scopes},
        )

    async def assign_permissions_to_user(
        self,
        user_id: str,
        permissions: list[str],
        *,
        resource_server_identifier: str | None = None,
    ) -> None:
        await self.management_request(
            "POST",
            f"/users/{self.path_segment(user_id)}/permissions",
            json={
                "permissions": [
                    {
                        "permission_name": permission,
                        "resource_server_identifier": (
                            resource_server_identifier or settings.auth0_audience
                        ),
                    }
                    for permission in permissions
                ]
            },
        )

    async def list_user_permissions(
        self,
        user_id: str,
        *,
        page: int = 0,
        per_page: int = 25,
    ) -> Any:
        return await self.management_request(
            "GET",
            f"/users/{self.path_segment(user_id)}/permissions",
            params={
                "page": page,
                "per_page": per_page,
                "include_totals": "true",
            },
        )

    async def remove_permissions_from_user(
        self,
        user_id: str,
        permissions: list[str],
        *,
        resource_server_identifier: str | None = None,
    ) -> None:
        await self.management_request(
            "DELETE",
            f"/users/{self.path_segment(user_id)}/permissions",
            json={
                "permissions": [
                    {
                        "permission_name": permission,
                        "resource_server_identifier": (
                            resource_server_identifier or settings.auth0_audience
                        ),
                    }
                    for permission in permissions
                ]
            },
        )

    async def assign_roles_to_user(self, user_id: str, role_ids: list[str]) -> None:
        await self.management_request(
            "POST",
            f"/users/{self.path_segment(user_id)}/roles",
            json={"roles": role_ids},
        )

    async def remove_roles_from_user(self, user_id: str, role_ids: list[str]) -> None:
        await self.management_request(
            "DELETE",
            f"/users/{self.path_segment(user_id)}/roles",
            json={"roles": role_ids},
        )

    async def list_user_authentication_methods(self, user_id: str) -> Any:
        return await self.management_request(
            "GET",
            f"/users/{self.path_segment(user_id)}/authentication-methods",
        )

    async def delete_user_authentication_method(
        self,
        user_id: str,
        authentication_method_id: str,
    ) -> None:
        await self.management_request(
            "DELETE",
            (
                f"/users/{self.path_segment(user_id)}/authentication-methods/"
                f"{self.path_segment(authentication_method_id)}"
            ),
        )

    async def reset_user_mfa(
        self,
        user_id: str,
        *,
        authentication_method_id: str | None = None,
    ) -> dict[str, Any]:
        deleted_ids = []

        if authentication_method_id:
            await self.delete_user_authentication_method(user_id, authentication_method_id)
            return {"deleted_authentication_method_ids": [authentication_method_id]}

        methods = await self.list_user_authentication_methods(user_id)
        for method in methods:
            method_id = method.get("id")
            if method_id:
                await self.delete_user_authentication_method(user_id, method_id)
                deleted_ids.append(method_id)

        return {"deleted_authentication_method_ids": deleted_ids}


class Auth0AuthenticationClient(Auth0BaseClient):
    async def start_mfa_enrollment(
        self,
        *,
        mfa_token: str,
        authenticator_types: list[str],
        oob_channels: list[str] | None = None,
        phone_number: str | None = None,
    ) -> Any:
        payload: dict[str, Any] = {"authenticator_types": authenticator_types}
        if oob_channels:
            payload["oob_channels"] = oob_channels
        if phone_number:
            payload["phone_number"] = phone_number

        return await self.request(
            "POST",
            f"{self.tenant_base_url}/mfa/associate",
            token=mfa_token,
            json=payload,
        )

    async def challenge_mfa(
        self,
        *,
        mfa_token: str,
        challenge_type: str,
        authenticator_id: str | None = None,
    ) -> Any:
        payload = {"challenge_type": challenge_type}
        if authenticator_id:
            payload["authenticator_id"] = authenticator_id

        return await self.request(
            "POST",
            f"{self.tenant_base_url}/mfa/challenge",
            token=mfa_token,
            json=payload,
        )

    async def delete_mfa_enrollment(self, *, mfa_token: str, enrollment_id: str) -> None:
        await self.request(
            "DELETE",
            f"{self.tenant_base_url}/mfa/authenticators/{self.path_segment(enrollment_id)}",
            token=mfa_token,
        )
