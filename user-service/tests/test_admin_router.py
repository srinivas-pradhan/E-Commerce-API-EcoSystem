import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from auth import verify_access_token
import main
from services.permission_cache import permission_cache


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

    async def remove_permissions_from_user(self, user_id, permissions):
        self.calls.append(("remove_permissions_from_user", user_id, permissions))

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

    async def disable_user(self, user_id, *, reason=None, actor=None):
        self.calls.append(("disable_user", user_id, reason, actor))
        return {"user_id": user_id, "blocked": True}

    async def start_user_delete_workflow(self, user_id, *, retention_days, reason=None, actor=None):
        self.calls.append(("start_user_delete_workflow", user_id, retention_days, reason, actor))
        return {"user_id": user_id, "blocked": True}

    async def update_api_permission(self, *, value, description):
        self.calls.append(("update_api_permission", value, description))
        return {
            "identifier": "https://user-service",
            "scopes": [{"value": value, "description": description}],
        }

    async def delete_api_permission(self, *, value):
        self.calls.append(("delete_api_permission", value))

    async def get_role(self, group_id):
        self.calls.append(("get_role", group_id))
        return {"id": group_id, "name": "admins"}

    async def update_role(self, group_id, payload):
        self.calls.append(("update_role", group_id, payload))
        return {"id": group_id, **payload}

    async def delete_role(self, group_id):
        self.calls.append(("delete_role", group_id))

    async def list_role_users(self, group_id, *, page=0, per_page=25):
        self.calls.append(("list_role_users", group_id, page, per_page))
        return {"users": [{"user_id": "auth0|user"}]}

    async def list_user_roles(self, user_id, *, page=0, per_page=25):
        self.calls.append(("list_user_roles", user_id, page, per_page))
        return {"roles": [{"id": "rol_1", "name": "admins"}]}


class AdminRouterTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        FakeManagementClient.instances = []

    def tearDown(self):
        main.app.dependency_overrides.clear()
        permission_cache.clear()

    def use_claims(self, scopes):
        async def override_verify_access_token():
            return {
                "sub": "auth0|admin",
                "permissions": scopes,
            }

        main.app.dependency_overrides[verify_access_token] = override_verify_access_token

    def send_request(self, method, path, body=None):
        if body is None:
            return getattr(self.client, method)(path)

        return self.client.request(method.upper(), path, json=body)

    def test_permission_admin_routes_require_bearer_token(self):
        requests = [
            ("post", "/admin/permissions", {}),
            ("patch", "/admin/permissions/read:orders", {}),
            ("delete", "/admin/permissions/read:orders", None),
            ("get", "/admin/users/auth0%7Cuser/permissions", None),
            ("post", "/admin/users/auth0%7Cuser/permissions", {}),
            ("delete", "/admin/users/auth0%7Cuser/permissions", {}),
            ("post", "/admin/users/auth0%7Cuser/disable", {}),
            ("post", "/admin/users/auth0%7Cuser/delete-workflow", {}),
            ("get", "/admin/groups/rol_1", None),
            ("patch", "/admin/groups/rol_1", {}),
            ("delete", "/admin/groups/rol_1", None),
            ("get", "/admin/groups/rol_1/users", None),
            ("get", "/admin/users/auth0%7Cuser/groups", None),
        ]

        for method, path, body in requests:
            with self.subTest(path=path):
                response = self.send_request(method, path, body)

                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"detail": "Missing bearer token"})

    def test_permission_admin_routes_reject_missing_scopes(self):
        self.use_claims([])
        requests = [
            ("post", "/admin/permissions", {"value": "read:orders", "description": "Read orders"}, "create:permissions"),
            ("patch", "/admin/permissions/read:orders", {"description": "Read orders"}, "update:permissions"),
            ("delete", "/admin/permissions/read:orders", None, "delete:permissions"),
            ("get", "/admin/users/auth0%7Cuser/permissions", None, "read:permissions"),
            (
                "post",
                "/admin/users/auth0%7Cuser/permissions",
                {"permissions": ["read:orders"]},
                "assign:permissions",
            ),
            (
                "delete",
                "/admin/users/auth0%7Cuser/permissions",
                {"permissions": ["read:orders"]},
                "unassign:permissions",
            ),
            ("post", "/admin/users/auth0%7Cuser/disable", {}, "disable:users"),
            ("post", "/admin/users/auth0%7Cuser/delete-workflow", {}, "delete:users"),
            ("get", "/admin/groups/rol_1", None, "read:groups"),
            ("patch", "/admin/groups/rol_1", {"description": "Admins"}, "update:groups"),
            ("delete", "/admin/groups/rol_1", None, "delete:groups"),
            ("get", "/admin/groups/rol_1/users", None, "read:groups"),
            ("get", "/admin/users/auth0%7Cuser/groups", None, "read:groups"),
        ]

        for method, path, body, missing_scope in requests:
            with self.subTest(path=path):
                response = self.send_request(method, path, body)

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

    def test_update_permission_updates_auth0_api_scope(self):
        self.use_claims(["update:permissions"])

        with patch("routers.admin.Auth0ManagementClient", FakeManagementClient):
            response = self.client.patch(
                "/admin/permissions/read:orders",
                json={"description": "Updated read order resources"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            FakeManagementClient.instances[0].calls,
            [("update_api_permission", "read:orders", "Updated read order resources")],
        )

    def test_delete_permission_removes_auth0_api_scope(self):
        self.use_claims(["delete:permissions"])

        with patch("routers.admin.Auth0ManagementClient", FakeManagementClient):
            response = self.client.delete("/admin/permissions/read:orders")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            FakeManagementClient.instances[0].calls,
            [("delete_api_permission", "read:orders")],
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

    def test_remove_permissions_from_user_deletes_auth0_permissions(self):
        self.use_claims(["unassign:permissions"])

        with patch("routers.admin.Auth0ManagementClient", FakeManagementClient):
            response = self.client.request(
                "DELETE",
                "/admin/users/auth0%7Cuser/permissions",
                json={"permissions": ["read:orders"]},
            )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            FakeManagementClient.instances[0].calls,
            [("remove_permissions_from_user", "auth0|user", ["read:orders"])],
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

    def test_list_user_permissions_uses_cache_when_enabled(self):
        self.use_claims(["read:permissions"])

        with patch("routers.admin.Auth0ManagementClient", FakeManagementClient):
            first = self.client.get("/admin/users/auth0%7Cuser/permissions?page=2&per_page=10")
            second = self.client.get("/admin/users/auth0%7Cuser/permissions?page=2&per_page=10")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(
            FakeManagementClient.instances[0].calls,
            [("list_user_permissions", "auth0|user", 2, 10)],
        )

    def test_list_user_permissions_can_bypass_cache(self):
        self.use_claims(["read:permissions"])

        with patch("routers.admin.Auth0ManagementClient", FakeManagementClient):
            self.client.get("/admin/users/auth0%7Cuser/permissions?page=2&per_page=10")
            self.client.get("/admin/users/auth0%7Cuser/permissions?page=2&per_page=10&use_cache=false")

        self.assertEqual(
            [instance.calls for instance in FakeManagementClient.instances],
            [
                [("list_user_permissions", "auth0|user", 2, 10)],
                [("list_user_permissions", "auth0|user", 2, 10)],
            ],
        )

    def test_disable_and_delete_workflow_update_auth0_user(self):
        requests = [
            (
                ["disable:users"],
                "/admin/users/auth0%7Cuser/disable",
                {"reason": "policy"},
                ("disable_user", "auth0|user", "policy", "auth0|admin"),
            ),
            (
                ["delete:users"],
                "/admin/users/auth0%7Cuser/delete-workflow",
                {"reason": "requested", "retention_days": 7},
                ("start_user_delete_workflow", "auth0|user", 7, "requested", "auth0|admin"),
            ),
        ]

        for scopes, path, body, expected_call in requests:
            with self.subTest(path=path):
                FakeManagementClient.instances = []
                self.use_claims(scopes)
                with patch("routers.admin.Auth0ManagementClient", FakeManagementClient):
                    response = self.client.post(path, json=body)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(FakeManagementClient.instances[0].calls, [expected_call])

    def test_group_management_routes_call_auth0_roles(self):
        requests = [
            ("read", ["read:groups"], "get", "/admin/groups/rol_1", None, ("get_role", "rol_1")),
            (
                "update",
                ["update:groups"],
                "patch",
                "/admin/groups/rol_1",
                {"description": "Admins"},
                ("update_role", "rol_1", {"description": "Admins"}),
            ),
            ("delete", ["delete:groups"], "delete", "/admin/groups/rol_1", None, ("delete_role", "rol_1")),
            (
                "group users",
                ["read:groups"],
                "get",
                "/admin/groups/rol_1/users?page=1&per_page=5",
                None,
                ("list_role_users", "rol_1", 1, 5),
            ),
            (
                "user groups",
                ["read:groups"],
                "get",
                "/admin/users/auth0%7Cuser/groups?page=1&per_page=5",
                None,
                ("list_user_roles", "auth0|user", 1, 5),
            ),
        ]

        for _, scopes, method, path, body, expected_call in requests:
            with self.subTest(path=path):
                FakeManagementClient.instances = []
                self.use_claims(scopes)

                with patch("routers.admin.Auth0ManagementClient", FakeManagementClient):
                    response = self.send_request(method, path, body)

                self.assertIn(response.status_code, [200, 204])
                self.assertEqual(FakeManagementClient.instances[0].calls, [expected_call])
