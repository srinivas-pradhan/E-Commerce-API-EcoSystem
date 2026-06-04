import unittest

from services.auth0.client import Auth0AuthenticationClient, Auth0ManagementClient, compose_search_query


class Auth0ManagementClientTest(unittest.IsolatedAsyncioTestCase):
    def test_path_segment_encodes_auth0_user_ids(self):
        client = Auth0ManagementClient()

        self.assertEqual(client.path_segment("auth0|abc/123"), "auth0%7Cabc%2F123")

    def test_compose_search_query_supports_empty_single_and_bounded_queries(self):
        self.assertIsNone(compose_search_query())
        self.assertEqual(compose_search_query(query='email:"a@example.com"'), '(email:"a@example.com")')
        self.assertEqual(
            compose_search_query(
                start_query="created_at:[2026-01-01 TO *]",
                end_query="created_at:[* TO 2026-02-01]",
            ),
            "(created_at:[2026-01-01 TO *]) AND (created_at:[* TO 2026-02-01])",
        )

    async def test_list_users_uses_search_params(self):
        calls = []
        client = Auth0ManagementClient()

        async def fake_management_request(method, path, *, json=None, params=None):
            calls.append((method, path, json, params))
            return {"users": []}

        client.management_request = fake_management_request

        result = await client.list_users(
            page=1,
            per_page=10,
            query='email:"a@example.com"',
            start_query="created_at:[2026-01-01 TO *]",
            end_query="created_at:[* TO 2026-02-01]",
        )

        self.assertEqual(result, {"users": []})
        self.assertEqual(
            calls,
            [
                (
                    "GET",
                    "/users",
                    None,
                    {
                        "page": 1,
                        "per_page": 10,
                        "include_totals": "true",
                        "q": (
                            '(email:"a@example.com") AND '
                            "(created_at:[2026-01-01 TO *]) AND "
                            "(created_at:[* TO 2026-02-01])"
                        ),
                        "search_engine": "v3",
                    },
                )
            ],
        )

    async def test_list_users_without_search_uses_pagination_only(self):
        calls = []
        client = Auth0ManagementClient()

        async def fake_management_request(method, path, *, json=None, params=None):
            calls.append((method, path, json, params))
            return {"users": []}

        client.management_request = fake_management_request

        await client.list_users(page=2, per_page=50)

        self.assertEqual(
            calls,
            [
                (
                    "GET",
                    "/users",
                    None,
                    {
                        "page": 2,
                        "per_page": 50,
                        "include_totals": "true",
                    },
                )
            ],
        )

    async def test_user_profile_helpers_use_management_user_endpoints(self):
        calls = []
        client = Auth0ManagementClient()

        async def fake_management_request(method, path, *, json=None, params=None):
            calls.append((method, path, json, params))
            return {"user_id": "auth0|abc"}

        client.management_request = fake_management_request

        await client.get_user("auth0|abc")
        await client.update_user("auth0|abc", {"user_metadata": {"tier": "gold"}})
        await client.complete_registration("auth0|abc")

        self.assertEqual(
            calls,
            [
                ("GET", "/users/auth0%7Cabc", None, None),
                (
                    "PATCH",
                    "/users/auth0%7Cabc",
                    {"user_metadata": {"tier": "gold"}},
                    None,
                ),
                (
                    "PATCH",
                    "/users/auth0%7Cabc",
                    {"app_metadata": {"registration_completed": True}},
                    None,
                ),
            ],
        )

    async def test_password_change_ticket_uses_management_ticket_endpoint(self):
        calls = []
        client = Auth0ManagementClient()

        async def fake_management_request(method, path, *, json=None, params=None):
            calls.append((method, path, json, params))
            return {"ticket": "https://example.com/ticket"}

        client.management_request = fake_management_request

        await client.create_password_change_ticket(
            user_id="auth0|abc",
            connection_id="con_123",
            result_url="https://example.com/done",
        )

        self.assertEqual(
            calls,
            [
                (
                    "POST",
                    "/tickets/password-change",
                    {
                        "client_id": "hG5aklxMlkilsmsfF6HjuROKNsivDJLU",
                        "mark_email_as_verified": False,
                        "user_id": "auth0|abc",
                        "connection_id": "con_123",
                        "result_url": "https://example.com/done",
                    },
                    None,
                )
            ],
        )

    async def test_list_roles_supports_pagination_and_name_filter_parts(self):
        calls = []
        client = Auth0ManagementClient()

        async def fake_management_request(method, path, *, json=None, params=None):
            calls.append((method, path, json, params))
            return {"roles": []}

        client.management_request = fake_management_request

        await client.list_roles(
            page=3,
            per_page=20,
            query="admin",
            start_query="north",
            end_query="america",
        )

        self.assertEqual(
            calls,
            [
                (
                    "GET",
                    "/roles",
                    None,
                    {
                        "page": 3,
                        "per_page": 20,
                        "include_totals": "true",
                        "name_filter": "admin north america",
                    },
                )
            ],
        )

    async def test_create_api_permission_patches_resource_server_scopes(self):
        calls = []
        client = Auth0ManagementClient()

        async def fake_management_request(method, path, *, json=None, params=None):
            calls.append((method, path, json, params))
            if method == "GET":
                return [
                    {
                        "id": "api|user-service",
                        "identifier": "https://user-service",
                        "scopes": [{"value": "read:users", "description": "Read users"}],
                    }
                ]
            return {"id": "api|user-service", "scopes": json["scopes"]}

        client.management_request = fake_management_request

        result = await client.create_api_permission(
            value="read:orders",
            description="Read order resources",
            audience="https://user-service",
        )

        self.assertEqual(
            result,
            {
                "id": "api|user-service",
                "scopes": [
                    {"value": "read:users", "description": "Read users"},
                    {"value": "read:orders", "description": "Read order resources"},
                ],
            },
        )
        self.assertEqual(
            calls,
            [
                (
                    "GET",
                    "/resource-servers",
                    None,
                    {"identifier": "https://user-service"},
                ),
                (
                    "PATCH",
                    "/resource-servers/api%7Cuser-service",
                    {
                        "scopes": [
                            {"value": "read:users", "description": "Read users"},
                            {"value": "read:orders", "description": "Read order resources"},
                        ]
                    },
                    None,
                ),
            ],
        )

    async def test_create_api_permission_is_idempotent_for_existing_scope(self):
        calls = []
        client = Auth0ManagementClient()

        async def fake_management_request(method, path, *, json=None, params=None):
            calls.append((method, path, json, params))
            if method == "GET":
                return [
                    {
                        "id": "api|user-service",
                        "identifier": "https://user-service",
                        "scopes": [{"value": "read:orders", "description": "Read order resources"}],
                    }
                ]
            return {"id": "api|user-service", "scopes": json["scopes"]}

        client.management_request = fake_management_request

        await client.create_api_permission(
            value="read:orders",
            description="Read order resources",
            audience="https://user-service",
        )

        self.assertEqual(
            calls[-1],
            (
                "PATCH",
                "/resource-servers/api%7Cuser-service",
                {"scopes": [{"value": "read:orders", "description": "Read order resources"}]},
                None,
            ),
        )

    async def test_assign_permissions_to_user_uses_user_permissions_endpoint(self):
        calls = []
        client = Auth0ManagementClient()

        async def fake_management_request(method, path, *, json=None, params=None):
            calls.append((method, path, json, params))

        client.management_request = fake_management_request

        await client.assign_permissions_to_user(
            "auth0|abc",
            ["read:orders", "update:orders"],
            resource_server_identifier="https://orders",
        )

        self.assertEqual(
            calls,
            [
                (
                    "POST",
                    "/users/auth0%7Cabc/permissions",
                    {
                        "permissions": [
                            {
                                "permission_name": "read:orders",
                                "resource_server_identifier": "https://orders",
                            },
                            {
                                "permission_name": "update:orders",
                                "resource_server_identifier": "https://orders",
                            },
                        ]
                    },
                    None,
                )
            ],
        )

    async def test_list_user_permissions_uses_user_permissions_endpoint(self):
        calls = []
        client = Auth0ManagementClient()

        async def fake_management_request(method, path, *, json=None, params=None):
            calls.append((method, path, json, params))
            return {"permissions": []}

        client.management_request = fake_management_request

        result = await client.list_user_permissions("auth0|abc", page=2, per_page=10)

        self.assertEqual(result, {"permissions": []})
        self.assertEqual(
            calls,
            [
                (
                    "GET",
                    "/users/auth0%7Cabc/permissions",
                    None,
                    {
                        "page": 2,
                        "per_page": 10,
                        "include_totals": "true",
                    },
                )
            ],
        )

    async def test_reset_user_mfa_deletes_all_methods(self):
        client = Auth0ManagementClient()
        deleted = []

        async def fake_list_user_authentication_methods(user_id):
            self.assertEqual(user_id, "auth0|abc")
            return [{"id": "mfa1"}, {"id": "mfa2"}, {"no_id": "ignored"}]

        async def fake_delete_user_authentication_method(user_id, authentication_method_id):
            deleted.append((user_id, authentication_method_id))

        client.list_user_authentication_methods = fake_list_user_authentication_methods
        client.delete_user_authentication_method = fake_delete_user_authentication_method

        result = await client.reset_user_mfa("auth0|abc")

        self.assertEqual(result, {"deleted_authentication_method_ids": ["mfa1", "mfa2"]})
        self.assertEqual(deleted, [("auth0|abc", "mfa1"), ("auth0|abc", "mfa2")])

    async def test_authentication_method_helpers_use_management_endpoints(self):
        calls = []
        client = Auth0ManagementClient()

        async def fake_management_request(method, path, *, json=None, params=None):
            calls.append((method, path, json, params))
            return [{"id": "mfa1"}] if method == "GET" else None

        client.management_request = fake_management_request

        result = await client.list_user_authentication_methods("auth0|abc")
        await client.delete_user_authentication_method("auth0|abc", "mfa/1")

        self.assertEqual(result, [{"id": "mfa1"}])
        self.assertEqual(
            calls,
            [
                ("GET", "/users/auth0%7Cabc/authentication-methods", None, None),
                (
                    "DELETE",
                    "/users/auth0%7Cabc/authentication-methods/mfa%2F1",
                    None,
                    None,
                ),
            ],
        )


class Auth0AuthenticationClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_mfa_helpers_use_authentication_api_endpoints(self):
        calls = []
        client = Auth0AuthenticationClient()

        async def fake_request(method, url, *, token=None, json=None, params=None):
            calls.append((method, url, token, json, params))
            return {"ok": True}

        client.request = fake_request

        await client.start_mfa_enrollment(
            mfa_token="mfa-token",
            authenticator_types=["otp"],
        )
        await client.start_mfa_enrollment(
            mfa_token="mfa-token",
            authenticator_types=["oob"],
            oob_channels=["sms"],
            phone_number="+14155550100",
        )
        await client.challenge_mfa(
            mfa_token="mfa-token",
            challenge_type="otp",
            authenticator_id="authenticator_1",
        )

        self.assertEqual(
            calls,
            [
                (
                    "POST",
                    "https://dev-lqyjuexwhe1bupvs.us.auth0.com/mfa/associate",
                    "mfa-token",
                    {"authenticator_types": ["otp"]},
                    None,
                ),
                (
                    "POST",
                    "https://dev-lqyjuexwhe1bupvs.us.auth0.com/mfa/associate",
                    "mfa-token",
                    {
                        "authenticator_types": ["oob"],
                        "oob_channels": ["sms"],
                        "phone_number": "+14155550100",
                    },
                    None,
                ),
                (
                    "POST",
                    "https://dev-lqyjuexwhe1bupvs.us.auth0.com/mfa/challenge",
                    "mfa-token",
                    {"challenge_type": "otp", "authenticator_id": "authenticator_1"},
                    None,
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
