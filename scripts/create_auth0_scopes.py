#!/usr/bin/env python3
"""Create user-service API permissions in Auth0.

Required environment variables:
  AUTH0_DOMAIN
  AUTH0_CLIENT_ID
  AUTH0_CLIENT_SECRET

Optional environment variables:
  AUTH0_AUDIENCE
  AUTH0_GRANT_CLIENT_ID

The client must be allowed to call the Auth0 Management API with scopes:
  read:resource_servers update:resource_servers read:client_grants create:client_grants update:client_grants
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
USER_SERVICE_ENV = REPO_ROOT / "user-service" / ".env"

USER_SERVICE_SCOPES = {
    "read:service_status": "Read user-service health and service metadata",
    "read:health_liveness": "Read user-service liveness health checks",
    "read:health_readiness": "Read user-service readiness health checks",
    "read:health_dependencies": "Read user-service non-secret dependency health details",
    "read:auth_config": "Read public Auth0 client configuration",
    "read:profile": "Read caller profile claims",
    "create:registration": "Start self-service user registration",
    "complete:registration": "Complete self-service user registration",
    "read:own_profile": "Read own user profile",
    "update:own_profile": "Update own user profile",
    "change:own_password": "Request own password change ticket",
    "read:own_mfa": "Read own MFA enrollments",
    "enroll:own_mfa": "Enroll own MFA factors",
    "challenge:own_mfa": "Challenge own MFA factors",
    "delete:own_mfa": "Delete own MFA enrollments",
    "read:users": "List and read users as an administrator",
    "update:users": "Update user attributes as an administrator",
    "reset:passwords": "Trigger password resets as an administrator",
    "reset:mfa": "Reset user MFA factors as an administrator",
    "read:groups": "List groups as an administrator",
    "create:groups": "Create groups as an administrator",
    "update:groups": "Update group memberships as an administrator",
    "delete:groups": "Delete groups or group memberships as an administrator",
}


def load_user_service_env() -> dict[str, str]:
    if not USER_SERVICE_ENV.exists():
        return {}

    values = {}
    for line in USER_SERVICE_ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")

        if key:
            values[key] = value

    return values


def config_value(env_file: dict[str, str], key: str, fallback: str | None = None) -> str | None:
    return os.getenv(key) or env_file.get(key) or fallback


@dataclass(frozen=True)
class Auth0Config:
    domain: str
    client_id: str
    client_secret: str
    audience: str
    grant_client_id: str | None

    @property
    def issuer(self) -> str:
        return f"https://{self.domain}"

    @property
    def management_audience(self) -> str:
        return f"{self.issuer}/api/v2/"


def load_config() -> Auth0Config:
    env_file = load_user_service_env()
    domain = config_value(env_file, "AUTH0_DOMAIN")
    client_id = config_value(env_file, "AUTH0_CLIENT_ID")
    client_secret = config_value(env_file, "AUTH0_CLIENT_SECRET")
    audience = config_value(env_file, "AUTH0_AUDIENCE", client_id)
    grant_client_id = config_value(env_file, "AUTH0_GRANT_CLIENT_ID")

    missing = [
        key
        for key, value in {
            "AUTH0_DOMAIN": domain,
            "AUTH0_CLIENT_ID": client_id,
            "AUTH0_CLIENT_SECRET": client_secret,
            "AUTH0_AUDIENCE": audience,
        }.items()
        if not value
    ]

    if missing:
        print(
            f"Missing required Auth0 setting(s): {', '.join(missing)}",
            file=sys.stderr,
        )
        print(
            f"Set them in the environment or in {USER_SERVICE_ENV}.",
            file=sys.stderr,
        )
        sys.exit(2)

    return Auth0Config(
        domain=str(domain),
        client_id=str(client_id),
        client_secret=str(client_secret),
        audience=str(audience),
        grant_client_id=grant_client_id,
    )


def request_json(
    method: str,
    url: str,
    *,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
    data = None
    headers = {"Content-Type": "application/json"}

    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        print(f"Auth0 request failed: {method} {url}", file=sys.stderr)
        print(f"Status: {error.code}", file=sys.stderr)
        print(body, file=sys.stderr)
        sys.exit(1)

    if not body:
        return {}

    return json.loads(body)


def get_management_token(config: Auth0Config) -> str:
    response = request_json(
        "POST",
        f"{config.issuer}/oauth/token",
        payload={
            "grant_type": "client_credentials",
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "audience": config.management_audience,
        },
    )

    if not isinstance(response, dict) or "access_token" not in response:
        print("Auth0 did not return an access token.", file=sys.stderr)
        sys.exit(1)

    return response["access_token"]


def find_resource_server(config: Auth0Config, token: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({"identifier": config.audience})
    response = request_json(
        "GET",
        f"{config.management_audience}resource-servers?{query}",
        token=token,
    )

    if not isinstance(response, list):
        print("Unexpected Auth0 resource server response.", file=sys.stderr)
        sys.exit(1)

    for resource_server in response:
        if resource_server.get("identifier") == config.audience:
            return resource_server

    print(
        f"No Auth0 API/resource server found for audience: {config.audience}",
        file=sys.stderr,
    )
    print("Create the API in Auth0 first, or set AUTH0_AUDIENCE to its identifier.", file=sys.stderr)
    sys.exit(1)


def merge_scopes(existing_scopes: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str]]:
    by_value = {scope["value"]: scope for scope in existing_scopes}
    added = []

    for value, description in USER_SERVICE_SCOPES.items():
        if value not in by_value:
            by_value[value] = {"value": value, "description": description}
            added.append(value)

    return list(by_value.values()), added


def update_resource_server_scopes(
    config: Auth0Config,
    token: str,
    resource_server: dict[str, Any],
    scopes: list[dict[str, str]],
) -> None:
    resource_server_id = resource_server["id"]
    encoded_id = urllib.parse.quote(resource_server_id, safe="")
    request_json(
        "PATCH",
        f"{config.management_audience}resource-servers/{encoded_id}",
        token=token,
        payload={"scopes": scopes},
    )


def find_client_grant(
    config: Auth0Config,
    token: str,
    client_id: str,
) -> dict[str, Any] | None:
    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "audience": config.audience,
            "subject_type": "client",
        }
    )
    response = request_json(
        "GET",
        f"{config.management_audience}client-grants?{query}",
        token=token,
    )

    if not isinstance(response, list):
        print("Unexpected Auth0 client grant response.", file=sys.stderr)
        sys.exit(1)

    for grant in response:
        if (
            grant.get("client_id") == client_id
            and grant.get("audience") == config.audience
            and grant.get("subject_type", "client") == "client"
        ):
            return grant

    return None


def create_client_grant(config: Auth0Config, token: str, client_id: str) -> dict[str, Any]:
    return request_json(
        "POST",
        f"{config.management_audience}client-grants",
        token=token,
        payload={
            "client_id": client_id,
            "audience": config.audience,
            "scope": list(USER_SERVICE_SCOPES),
            "subject_type": "client",
        },
    )


def update_client_grant(
    config: Auth0Config,
    token: str,
    grant: dict[str, Any],
) -> list[str]:
    existing_scopes = set(grant.get("scope", []))
    missing_scopes = [scope for scope in USER_SERVICE_SCOPES if scope not in existing_scopes]

    if not missing_scopes:
        return []

    merged_scopes = list(existing_scopes)
    merged_scopes.extend(missing_scopes)
    encoded_id = urllib.parse.quote(grant["id"], safe="")
    request_json(
        "PATCH",
        f"{config.management_audience}client-grants/{encoded_id}",
        token=token,
        payload={"scope": merged_scopes},
    )

    return missing_scopes


def ensure_client_grant(config: Auth0Config, token: str) -> None:
    if not config.grant_client_id:
        return

    grant = find_client_grant(config, token, config.grant_client_id)
    if grant is None:
        create_client_grant(config, token, config.grant_client_id)
        print(
            f"Created client grant for {config.grant_client_id} "
            f"with {len(USER_SERVICE_SCOPES)} scope(s)."
        )
        return

    added_scopes = update_client_grant(config, token, grant)
    if not added_scopes:
        print(
            f"Client grant for {config.grant_client_id} already has "
            f"all {len(USER_SERVICE_SCOPES)} user-service scope(s)."
        )
        return

    print(f"Added {len(added_scopes)} scope(s) to client grant for {config.grant_client_id}:")
    for scope in added_scopes:
        print(f"  - {scope}")


def main() -> int:
    config = load_config()
    token = get_management_token(config)
    resource_server = find_resource_server(config, token)
    merged_scopes, added = merge_scopes(resource_server.get("scopes", []))

    if not added:
        print(f"All {len(USER_SERVICE_SCOPES)} user-service scopes already exist.")
    else:
        update_resource_server_scopes(config, token, resource_server, merged_scopes)
        print(f"Created {len(added)} scope(s) for audience {config.audience}:")
        for scope in added:
            print(f"  - {scope}")

    ensure_client_grant(config, token)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
