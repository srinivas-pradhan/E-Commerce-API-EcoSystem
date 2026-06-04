from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError

from config import settings


bearer_scheme = HTTPBearer(auto_error=False)
jwks_client = PyJWKClient(settings.auth0_jwks_url)


def _credentials_exception(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def verify_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if credentials is None:
        raise _credentials_exception("Missing bearer token")

    token = credentials.credentials

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=settings.auth0_algorithms,
            audience=settings.auth0_audience,
            issuer=settings.auth0_issuer,
        )
    except (InvalidTokenError, PyJWKClientError):
        raise _credentials_exception()


def require_permissions(*required_permissions: str):
    async def dependency(claims: dict[str, Any] = Depends(verify_access_token)) -> dict[str, Any]:
        token_permissions = set(claims.get("permissions", []))
        missing_permissions = sorted(set(required_permissions) - token_permissions)

        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Insufficient permissions",
                    "missing_permissions": missing_permissions,
                },
            )

        return claims

    return dependency
