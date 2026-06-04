import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from auth import verify_access_token
import main


class FakeManagementClient:
    instances = []

    def __init__(self):
        self.calls = []
        self.instances.append(self)

    async def create_api_permission(self, *, value, description):
        self.calls.append(("create_api_permission", value, description))
        return {
            "identifier": "https://user-service",
            "scopes": [{"value": value, "description": description}],
        }

    async def assign_permissions_to_user(self, user_id, permissions):
        self.calls.append(("assign_permissions_to_user", user_id, permissions))

    async def list_user_permissions(self, user_id, *, page=0, per_page=25):
        self.calls.append(("list_user_permissions", user_id, page, per_page))
        return {
            "permissions": [
                {
                    "permission_name": "read:orders",
                    "resource_server_identifier": "https://orders",
                }
            ]
        }


class AdminRouterTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        FakeManagementClient.instances = []

    def tearDown(self):
        main.app.dependency_overrides.clear()

    def use_claims(self, scopes):
        async def override_verify_access_token():
            return {
                "sub": "auth0|admin",
                "permissions": scopes,
            }

        main.app.dependency_overrides[verify_access_token] = override_verify_access_token

    def test_permission_admin_routes_require_bearer_token(self):
        requests = [
            ("post", "/admin/permissions", {}),
            ("get", "/admin/users/auth0%7Cuser/permissions", None),
            ("post", "/admin/users/auth0%7Cuser/permissions", {}),
        ]

        for method, path, body in requests:
            with self.subTest(path=path):
                request = getattr(self.client, method)
                response = request(path, json=body) if body is not None else request(path)

                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"detail": "Missing bearer token"})

    def test_permission_admin_routes_reject_missing_scopes(self):
        self.use_claims([])
        requests = [
            ("post", "/admin/permissions", {"value": "read:orders", "description": "Read orders"}, "create:permissions"),
            ("get", "/admin/users/auth0%7Cuser/permissions", None, "read:permissions"),
            (
                "post",
                "/admin/users/auth0%7Cuser/permissions",
                {"permissions": ["read:orders"]},
                "assign:permissions",
            ),
        ]

        for method, path, body, missing_scope in requests:
            with self.subTest(path=path):
                request = getattr(self.client, method)
                response = request(path, json=body) if body is not None else request(path)

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

    def test_create_permission_adds_scope_to_auth0_api(self):
        self.use_claims(["create:permissions"])

        with patch("routers.admin.Auth0ManagementClient", FakeManagementClient):
            response = self.client.post(
                "/admin/permissions",
                json={
                    "value": "read:orders",
                    "description": "Read order resources",
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {
                "identifier": "https://user-service",
                "scopes": [{"value": "read:orders", "description": "Read order resources"}],
            },
        )
        self.assertEqual(
            FakeManagementClient.instances[0].calls,
            [("create_api_permission", "read:orders", "Read order resources")],
        )

    def test_assign_permissions_to_user_posts_auth0_permissions(self):
        self.use_claims(["assign:permissions"])

        with patch("routers.admin.Auth0ManagementClient", FakeManagementClient):
            response = self.client.post(
                "/admin/users/auth0%7Cuser/permissions",
                json={"permissions": ["read:orders", "update:orders"]},
            )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            FakeManagementClient.instances[0].calls,
            [
                (
                    "assign_permissions_to_user",
                    "auth0|user",
                    ["read:orders", "update:orders"],
                )
            ],
        )

    def test_list_user_permissions_reads_auth0_permissions(self):
        self.use_claims(["read:permissions"])

        with patch("routers.admin.Auth0ManagementClient", FakeManagementClient):
            response = self.client.get(
                "/admin/users/auth0%7Cuser/permissions?page=2&per_page=10",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "permissions": [
                    {
                        "permission_name": "read:orders",
                        "resource_server_identifier": "https://orders",
                    }
                ]
            },
        )
        self.assertEqual(
            FakeManagementClient.instances[0].calls,
            [("list_user_permissions", "auth0|user", 2, 10)],
        )
