import os
import unittest

from config import settings
from services.auth0.client import Auth0ManagementClient


def integration_enabled() -> bool:
    return os.getenv("RUN_AUTH0_INTEGRATION_TESTS", "").lower() == "true"


@unittest.skipUnless(integration_enabled(), "Auth0 integration tests are disabled")
class Auth0IntegrationTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        if settings.auth0_client_secret is None:
            self.skipTest("AUTH0_CLIENT_SECRET is not configured")

    async def test_management_client_can_read_user_service_api(self):
        client = Auth0ManagementClient()

        resource_server = await client.get_resource_server_by_identifier(settings.auth0_audience)

        self.assertEqual(resource_server.get("identifier"), settings.auth0_audience)
        self.assertIsInstance(resource_server.get("scopes", []), list)

    async def test_management_client_can_read_configured_test_user_permissions(self):
        test_user_id = os.getenv("AUTH0_TEST_USER_ID")
        if not test_user_id:
            self.skipTest("AUTH0_TEST_USER_ID is not configured")

        client = Auth0ManagementClient()

        response = await client.list_user_permissions(test_user_id, page=0, per_page=25)

        self.assertIsInstance(response, dict)
        self.assertIn("permissions", response)
