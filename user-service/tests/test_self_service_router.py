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

    async def create_user(self, payload):
        self.calls.append(("create_user", payload))
        return {"user_id": "auth0|new-user", **payload}

    async def complete_registration(self, user_id):
        self.calls.append(("complete_registration", user_id))
        return {"user_id": user_id, "app_metadata": {"registration_completed": True}}

    async def get_user(self, user_id):
        self.calls.append(("get_user", user_id))
        return {"user_id": user_id, "email": "user@example.com"}

    async def update_user(self, user_id, payload):
        self.calls.append(("update_user", user_id, payload))
        return {"user_id": user_id, **payload}

    async def create_password_change_ticket(
        self,
        *,
        user_id=None,
        email=None,
        connection_id=None,
        result_url=None,
    ):
        self.calls.append(
            (
                "create_password_change_ticket",
                user_id,
                email,
                connection_id,
                result_url,
            )
        )
        return {"ticket": "https://example.com/password-change"}

    async def list_user_authentication_methods(self, user_id):
        self.calls.append(("list_user_authentication_methods", user_id))
        return [{"id": "mfa_1", "type": "otp"}]

    async def delete_user_authentication_method(self, user_id, enrollment_id):
        self.calls.append(("delete_user_authentication_method", user_id, enrollment_id))


class FakeAuthenticationClient:
    instances = []

    def __init__(self):
        self.calls = []
        self.instances.append(self)

    async def start_mfa_enrollment(
        self,
        *,
        mfa_token,
        authenticator_types,
        oob_channels=None,
        phone_number=None,
    ):
        self.calls.append(
            (
                "start_mfa_enrollment",
                mfa_token,
                authenticator_types,
                oob_channels,
                phone_number,
            )
        )
        return {"barcode_uri": "otpauth://example"}

    async def challenge_mfa(self, *, mfa_token, challenge_type, authenticator_id=None):
        self.calls.append(("challenge_mfa", mfa_token, challenge_type, authenticator_id))
        return {"challenge_type": challenge_type}


class SelfServiceRouterTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        FakeManagementClient.instances = []
        FakeAuthenticationClient.instances = []

    def tearDown(self):
        main.app.dependency_overrides.clear()

    def use_claims(self, scopes):
        async def override_verify_access_token():
            return {
                "sub": "auth0|user",
                "email": "user@example.com",
                "permissions": scopes,
            }

        main.app.dependency_overrides[verify_access_token] = override_verify_access_token

    def test_self_service_routes_require_bearer_token(self):
        requests = [
            ("post", "/self-service/registration", {}),
            ("post", "/self-service/registration/complete", {}),
            ("get", "/self-service/profile", None),
            ("patch", "/self-service/profile", {}),
            ("post", "/self-service/password-change", {}),
            ("get", "/self-service/mfa/enrollments", None),
            ("post", "/self-service/mfa/enroll", {}),
            ("post", "/self-service/mfa/challenge", {}),
            ("delete", "/self-service/mfa/enrollments/mfa_1", None),
        ]

        for method, path, body in requests:
            with self.subTest(path=path):
                request = getattr(self.client, method)
                response = request(path, json=body) if body is not None else request(path)

                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"detail": "Missing bearer token"})

    def test_self_service_routes_reject_missing_scopes(self):
        self.use_claims([])
        requests = [
            ("post", "/self-service/registration", {}, "create:registration"),
            ("post", "/self-service/registration/complete", {"user_id": "auth0|user"}, "complete:registration"),
            ("get", "/self-service/profile", None, "read:own_profile"),
            ("patch", "/self-service/profile", {}, "update:own_profile"),
            ("post", "/self-service/password-change", {}, "change:own_password"),
            ("get", "/self-service/mfa/enrollments", None, "read:own_mfa"),
            ("post", "/self-service/mfa/enroll", {}, "enroll:own_mfa"),
            ("post", "/self-service/mfa/challenge", {}, "challenge:own_mfa"),
            ("delete", "/self-service/mfa/enrollments/mfa_1", None, "delete:own_mfa"),
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

    def test_start_registration_creates_auth0_user(self):
        self.use_claims(["create:registration"])

        with patch("routers.self_service.Auth0ManagementClient", FakeManagementClient):
            response = self.client.post(
                "/self-service/registration",
                json={
                    "email": "new@example.com",
                    "password": "password123",
                    "given_name": "New",
                    "family_name": "User",
                    "user_metadata": {"source": "test"},
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            FakeManagementClient.instances[0].calls[0],
            (
                "create_user",
                {
                    "connection": "Username-Password-Authentication",
                    "email": "new@example.com",
                    "password": "password123",
                    "email_verified": False,
                    "verify_email": True,
                    "user_metadata": {"source": "test"},
                    "given_name": "New",
                    "family_name": "User",
                },
            ),
        )

    def test_complete_registration_updates_current_user_only(self):
        self.use_claims(["complete:registration"])

        with patch("routers.self_service.Auth0ManagementClient", FakeManagementClient):
            response = self.client.post(
                "/self-service/registration/complete",
                json={"user_id": "auth0|user"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            FakeManagementClient.instances[0].calls,
            [("complete_registration", "auth0|user")],
        )

    def test_complete_registration_rejects_other_user(self):
        self.use_claims(["complete:registration"])

        response = self.client.post(
            "/self-service/registration/complete",
            json={"user_id": "auth0|other"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"detail": "Cannot complete registration for another user"})

    def test_read_profile_fetches_current_auth0_user(self):
        self.use_claims(["read:own_profile"])

        with patch("routers.self_service.Auth0ManagementClient", FakeManagementClient):
            response = self.client.get("/self-service/profile")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"user_id": "auth0|user", "email": "user@example.com"})
        self.assertEqual(FakeManagementClient.instances[0].calls, [("get_user", "auth0|user")])

    def test_update_profile_updates_current_user_metadata(self):
        self.use_claims(["update:own_profile"])

        with patch("routers.self_service.Auth0ManagementClient", FakeManagementClient):
            response = self.client.patch("/self-service/profile", json={"timezone": "America/Toronto"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            FakeManagementClient.instances[0].calls,
            [("update_user", "auth0|user", {"user_metadata": {"timezone": "America/Toronto"}})],
        )

    def test_password_change_requests_current_user_ticket(self):
        self.use_claims(["change:own_password"])

        with patch("routers.self_service.Auth0ManagementClient", FakeManagementClient):
            response = self.client.post(
                "/self-service/password-change",
                json={"result_url": "https://example.com/done"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ticket": "https://example.com/password-change"})
        self.assertEqual(
            FakeManagementClient.instances[0].calls,
            [
                (
                    "create_password_change_ticket",
                    "auth0|user",
                    None,
                    None,
                    "https://example.com/done",
                )
            ],
        )

    def test_list_mfa_enrollments_fetches_current_user_methods(self):
        self.use_claims(["read:own_mfa"])

        with patch("routers.self_service.Auth0ManagementClient", FakeManagementClient):
            response = self.client.get("/self-service/mfa/enrollments")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [{"id": "mfa_1", "type": "otp"}])
        self.assertEqual(
            FakeManagementClient.instances[0].calls,
            [("list_user_authentication_methods", "auth0|user")],
        )

    def test_mfa_enrollment_uses_auth0_authentication_api(self):
        self.use_claims(["enroll:own_mfa"])

        with patch("routers.self_service.Auth0AuthenticationClient", FakeAuthenticationClient):
            response = self.client.post(
                "/self-service/mfa/enroll",
                json={"mfa_token": "mfa-token", "authenticator_type": "otp"},
            )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            FakeAuthenticationClient.instances[0].calls,
            [("start_mfa_enrollment", "mfa-token", ["otp"], None, None)],
        )

    def test_mfa_sms_enrollment_uses_oob_channel_and_phone_number(self):
        self.use_claims(["enroll:own_mfa"])

        with patch("routers.self_service.Auth0AuthenticationClient", FakeAuthenticationClient):
            response = self.client.post(
                "/self-service/mfa/enroll",
                json={
                    "mfa_token": "mfa-token",
                    "authenticator_type": "oob",
                    "oob_channels": ["sms"],
                    "phone_number": "+14155550100",
                },
            )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            FakeAuthenticationClient.instances[0].calls,
            [("start_mfa_enrollment", "mfa-token", ["oob"], ["sms"], "+14155550100")],
        )

    def test_mfa_oob_enrollment_requires_channel(self):
        self.use_claims(["enroll:own_mfa"])

        response = self.client.post(
            "/self-service/mfa/enroll",
            json={"mfa_token": "mfa-token", "authenticator_type": "oob"},
        )

        self.assertEqual(response.status_code, 422)

    def test_mfa_sms_enrollment_requires_phone_number(self):
        self.use_claims(["enroll:own_mfa"])

        response = self.client.post(
            "/self-service/mfa/enroll",
            json={
                "mfa_token": "mfa-token",
                "authenticator_type": "oob",
                "oob_channels": ["sms"],
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_mfa_challenge_uses_auth0_authentication_api(self):
        self.use_claims(["challenge:own_mfa"])

        with patch("routers.self_service.Auth0AuthenticationClient", FakeAuthenticationClient):
            response = self.client.post(
                "/self-service/mfa/challenge",
                json={
                    "mfa_token": "mfa-token",
                    "challenge_type": "otp",
                    "authenticator_id": "authenticator_1",
                },
            )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            FakeAuthenticationClient.instances[0].calls,
            [("challenge_mfa", "mfa-token", "otp", "authenticator_1")],
        )

    def test_delete_mfa_enrollment_deletes_current_user_method(self):
        self.use_claims(["delete:own_mfa"])

        with patch("routers.self_service.Auth0ManagementClient", FakeManagementClient):
            response = self.client.delete("/self-service/mfa/enrollments/mfa_1")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            FakeManagementClient.instances[0].calls,
            [("delete_user_authentication_method", "auth0|user", "mfa_1")],
        )
