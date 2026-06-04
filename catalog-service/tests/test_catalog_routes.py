import unittest

from fastapi.testclient import TestClient

from auth import verify_access_token
import main


class CatalogRoutesTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def tearDown(self):
        main.app.dependency_overrides.clear()

    def use_claims(self, scopes):
        async def override_verify_access_token():
            return {
                "sub": "auth0|user",
                "permissions": scopes,
            }

        main.app.dependency_overrides[verify_access_token] = override_verify_access_token

    def test_product_routes_require_bearer_token(self):
        requests = [
            ("get", "/products", None),
            ("get", "/products/1", None),
            ("post", "/products/1/cart-reservations", {"cart_id": "cart_1", "quantity": 1}),
            ("get", "/admin/catalog/products", None),
            ("post", "/admin/catalog/products", {}),
            ("patch", "/admin/catalog/products/1/inventory", {}),
        ]

        for method, path, body in requests:
            with self.subTest(path=path):
                response = self.client.request(method.upper(), path, json=body)

                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"detail": "Missing bearer token"})

    def test_product_routes_reject_missing_scopes(self):
        self.use_claims([])
        requests = [
            ("get", "/products", None, "read:products"),
            ("post", "/products/1/cart-reservations", {"cart_id": "cart_1", "quantity": 1}, "reserve:cart_inventory"),
            ("get", "/admin/catalog/products", None, "read:inventory"),
            ("post", "/admin/catalog/products", {}, "manage:catalog"),
            ("patch", "/admin/catalog/products/1/inventory", {}, "manage:inventory"),
            ("post", "/admin/catalog/products/1/promotions", {}, "manage:promotions"),
        ]

        for method, path, body, missing_scope in requests:
            with self.subTest(path=path):
                response = self.client.request(method.upper(), path, json=body)

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

    def test_end_user_can_list_released_products_only(self):
        self.use_claims(["read:products"])

        response = self.client.get("/products")

        self.assertEqual(response.status_code, 200)
        product_statuses = {product["status"] for product in response.json()}
        self.assertEqual(product_statuses, {"released"})

    def test_admin_can_view_inventory_including_drafts(self):
        self.use_claims(["read:inventory"])

        response = self.client.get("/admin/catalog/products")

        self.assertEqual(response.status_code, 200)
        products = response.json()
        self.assertTrue(any(product["status"] == "draft" for product in products))
        self.assertTrue(all("inventory" in product for product in products))

    def test_cart_reservation_reduces_available_inventory(self):
        self.use_claims(["read:inventory"])
        before = self.client.get("/admin/catalog/products/1").json()["inventory"]["available"]

        self.use_claims(["reserve:cart_inventory"])
        response = self.client.post(
            "/products/1/cart-reservations",
            json={"cart_id": "cart_test_reservation", "quantity": 2},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "active")

        self.use_claims(["read:inventory"])
        after = self.client.get("/admin/catalog/products/1").json()["inventory"]["available"]
        self.assertEqual(after, before - 2)


if __name__ == "__main__":
    unittest.main()
