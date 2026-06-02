import unittest

from fastapi.testclient import TestClient

import main


class HealthRouterTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_core_routes_are_registered(self):
        paths = {route.path for route in main.app.routes}

        self.assertIn("/", paths)
        self.assertIn("/auth/config", paths)
        self.assertIn("/me", paths)

    def test_core_routes_require_bearer_token(self):
        for path in ["/", "/auth/config", "/me"]:
            with self.subTest(path=path):
                response = self.client.get(path)

                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"detail": "Missing bearer token"})
