#!/usr/bin/env python3
"""Grant user-service's Auth0 client the Management API scopes it needs."""

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

USER_SERVICE_MANAGEMENT_SCOPES = [
    "create:users",
    "read:users",
    "update:users",
    "read:roles",
    "create:roles",
    "update:roles",
    "delete:roles",
    "read:authentication_methods",
    "delete:authentication_methods",
    "create:user_tickets",
    "read:resource_servers",
    "update:resource_servers",
]


@dataclass(frozen=True)
class Auth0Config:
    domain: str
    client_id: str
    client_secret: str
    grant_client_id: str

    @property
    def issuer(self) -> str:
        return f"https://{self.domain}"

    @property
    def management_audience(self) -> str:
        return f"{self.issuer}/api/v2/"


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


def load_config() -> Auth0Config:
    env_file = load_user_service_env()
    domain = config_value(env_file, "AUTH0_DOMAIN")
    client_id = config_value(env_file, "AUTH0_CLIENT_ID")
    client_secret = config_value(env_file, "AUTH0_CLIENT_SECRET")
    grant_client_id = config_value(env_file, "AUTH0_MANAGEMENT_GRANT_CLIENT_ID", client_id)

    missing = [
        key
        for key, value in {
            "AUTH0_DOMAIN": domain,
            "AUTH0_CLIENT_ID": client_id,
            "AUTH0_CLIENT_SECRET": client_secret,
            "AUTH0_MANAGEMENT_GRANT_CLIENT_ID": grant_client_id,
        }.items()
        if not value
    ]

    if missing:
        print(f"Missing required Auth0 setting(s): {', '.join(missing)}", file=sys.stderr)
        print(f"Set them in the environment or in {USER_SERVICE_ENV}.", file=sys.stderr)
        sys.exit(2)

    return Auth0Config(
        domain=str(domain),
        client_id=str(client_id),
        client_secret=str(client_secret),
        grant_client_id=str(grant_client_id),
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


def find_client_grant(config: Auth0Config, token: str) -> dict[str, Any] | None:
    query = urllib.parse.urlencode(
        {
            "client_id": config.grant_client_id,
            "audience": config.management_audience,
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
            grant.get("client_id") == config.grant_client_id
            and grant.get("audience") == config.management_audience
            and grant.get("subject_type", "client") == "client"
        ):
            return grant

    return None


def create_client_grant(config: Auth0Config, token: str) -> None:
    request_json(
        "POST",
        f"{config.management_audience}client-grants",
        token=token,
        payload={
            "client_id": config.grant_client_id,
            "audience": config.management_audience,
            "scope": USER_SERVICE_MANAGEMENT_SCOPES,
            "subject_type": "client",
        },
    )


def update_client_grant(config: Auth0Config, token: str, grant: dict[str, Any]) -> list[str]:
    existing_scopes = set(grant.get("scope", []))
    missing_scopes = [scope for scope in USER_SERVICE_MANAGEMENT_SCOPES if scope not in existing_scopes]

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


def main() -> int:
    config = load_config()
    token = get_management_token(config)
    grant = find_client_grant(config, token)

    if grant is None:
        create_client_grant(config, token)
        print(
            f"Created Management API client grant for {config.grant_client_id} "
            f"with {len(USER_SERVICE_MANAGEMENT_SCOPES)} scope(s)."
        )
        return 0

    added_scopes = update_client_grant(config, token, grant)
    if not added_scopes:
        print(
            f"Management API client grant for {config.grant_client_id} already has "
            f"all {len(USER_SERVICE_MANAGEMENT_SCOPES)} required scope(s)."
        )
        return 0

    print(f"Added {len(added_scopes)} Management API scope(s) to {config.grant_client_id}:")
    for scope in added_scopes:
        print(f"  - {scope}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
