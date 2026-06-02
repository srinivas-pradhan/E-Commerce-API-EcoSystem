import unittest

from fastapi.testclient import TestClient

from auth import verify_access_token
from config import settings
import main


class HealthRouterTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def tearDown(self):
        main.app.dependency_overrides.clear()

    def use_claims(self, claims):
        async def override_verify_access_token():
            return claims

        main.app.dependency_overrides[verify_access_token] = override_verify_access_token

    def test_core_routes_are_registered(self):
        paths = {route.path for route in main.app.routes}

        self.assertIn("/", paths)
        self.assertIn("/health/live", paths)
        self.assertIn("/health/ready", paths)
        self.assertIn("/health/dependencies", paths)
        self.assertIn("/auth/config", paths)
        self.assertIn("/me", paths)

    def test_core_routes_require_bearer_token(self):
        for path in ["/", "/health/live", "/health/ready", "/health/dependencies", "/auth/config", "/me"]:
            with self.subTest(path=path):
                response = self.client.get(path)

                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"detail": "Missing bearer token"})

    def test_core_routes_reject_missing_scopes(self):
        self.use_claims({"sub": "auth0|user", "permissions": []})

        expected_missing_scopes = {
            "/": "read:service_status",
            "/health/live": "read:health_liveness",
            "/health/ready": "read:health_readiness",
            "/health/dependencies": "read:health_dependencies",
            "/auth/config": "read:auth_config",
            "/me": "read:profile",
        }

        for path, missing_scope in expected_missing_scopes.items():
            with self.subTest(path=path):
                response = self.client.get(path)

                self.assertEqual(response.status_code, 403)
                self.assertEqual(
                    response.json(),
                    {
                        "detail": {
                            "message": "Insufficient permissions",
                            "missing_permissions": [missing_scope],
                        }
                    },
                )

    def test_service_status_returns_contract_with_required_scope(self):
        self.use_claims({"sub": "auth0|user", "permissions": ["read:service_status"]})

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"service": "user-auth", "auth_backend": "auth0"})

    def test_liveness_returns_contract_with_required_scope(self):
        self.use_claims({"sub": "auth0|user", "permissions": ["read:health_liveness"]})

        response = self.client.get("/health/live")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"service": "user-auth", "status": "live"})

    def test_readiness_returns_config_checks_with_required_scope(self):
        self.use_claims({"sub": "auth0|user", "permissions": ["read:health_readiness"]})

        response = self.client.get("/health/ready")
        expected_checks = {
            "auth0_domain_configured": True,
            "auth0_client_id_configured": True,
            "auth0_audience_configured": True,
            "auth0_client_secret_configured": settings.auth0_client_secret is not None,
        }

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "service": "user-auth",
                "status": "ready" if all(expected_checks.values()) else "degraded",
                "checks": expected_checks,
            },
        )

    def test_dependencies_returns_non_secret_auth0_details_with_required_scope(self):
        self.use_claims({"sub": "auth0|user", "permissions": ["read:health_dependencies"]})

        response = self.client.get("/health/dependencies")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "service": "user-auth",
                "auth_backend": "auth0",
                "issuer": settings.auth0_issuer,
                "jwks_url": settings.auth0_jwks_url,
                "management_audience": settings.auth0_management_audience,
                "management_client_configured": settings.auth0_client_secret is not None,
            },
        )

    def test_auth_config_returns_public_auth0_settings_with_required_scope(self):
        self.use_claims({"sub": "auth0|user", "permissions": ["read:auth_config"]})

        response = self.client.get("/auth/config")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "domain": settings.auth0_domain,
                "client_id": settings.auth0_client_id,
                "audience": settings.auth0_audience,
                "issuer": settings.auth0_issuer,
            },
        )

    def test_me_returns_claims_with_required_scope(self):
        claims = {
            "sub": "auth0|user",
            "permissions": ["read:profile"],
            "email": "user@example.com",
        }
        self.use_claims(claims)

        response = self.client.get("/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), claims)
