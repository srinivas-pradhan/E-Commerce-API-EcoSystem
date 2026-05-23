import unittest

from services.auth0.client import Auth0ManagementClient


class Auth0ManagementClientTest(unittest.IsolatedAsyncioTestCase):
    def test_path_segment_encodes_auth0_user_ids(self):
        client = Auth0ManagementClient()

        self.assertEqual(client.path_segment("auth0|abc/123"), "auth0%7Cabc%2F123")

    async def test_list_users_uses_search_params(self):
        calls = []
        client = Auth0ManagementClient()

        async def fake_management_request(method, path, *, json=None, params=None):
            calls.append((method, path, json, params))
            return {"users": []}

        client.management_request = fake_management_request

        result = await client.list_users(page=1, per_page=10, query='email:"a@example.com"')

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
                        "q": 'email:"a@example.com"',
                        "search_engine": "v3",
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


if __name__ == "__main__":
    unittest.main()
