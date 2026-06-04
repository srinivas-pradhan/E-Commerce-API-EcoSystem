from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException, status

from config import settings


def _now() -> datetime:
    return datetime.now(UTC)


_products = [
    {
        "id": 1,
        "sku": "DENIM-JACKET-001",
        "name": "Classic Denim Jacket",
        "description": "Midweight denim jacket with brass buttons.",
        "category": "apparel",
        "price": Decimal("79.99"),
        "currency": "USD",
        "status": "released",
        "is_featured": True,
        "inventory": {
            "on_hand": 25,
            "reserved": 0,
            "available": 25,
            "low_stock_threshold": 5,
            "allow_backorder": False,
        },
        "active_promotions": [
            {
                "id": 1,
                "name": "Spring launch sale",
                "promotion_type": "percentage",
                "value": Decimal("15"),
                "starts_at": _now() - timedelta(days=1),
                "ends_at": _now() + timedelta(days=14),
                "is_active": True,
            }
        ],
    },
    {
        "id": 2,
        "sku": "LEATHER-WALLET-001",
        "name": "Slim Leather Wallet",
        "description": "Compact wallet with six card slots.",
        "category": "accessories",
        "price": Decimal("44.50"),
        "currency": "USD",
        "status": "released",
        "is_featured": False,
        "inventory": {
            "on_hand": 12,
            "reserved": 0,
            "available": 12,
            "low_stock_threshold": 4,
            "allow_backorder": False,
        },
        "active_promotions": [],
    },
    {
        "id": 3,
        "sku": "SNEAKER-DRAFT-001",
        "name": "Court Sneaker",
        "description": "Draft product used by admins before release.",
        "category": "footwear",
        "price": Decimal("109.00"),
        "currency": "USD",
        "status": "draft",
        "is_featured": False,
        "inventory": {
            "on_hand": 50,
            "reserved": 0,
            "available": 50,
            "low_stock_threshold": 10,
            "allow_backorder": False,
        },
        "active_promotions": [],
    },
]
_reservations = []


def _sync_available(product: dict) -> None:
    inventory = product["inventory"]
    inventory["available"] = max(inventory["on_hand"] - inventory["reserved"], 0)


def _expire_reservations() -> None:
    now = _now()
    for reservation in _reservations:
        if reservation["status"] != "active" or reservation["expires_at"] > now:
            continue

        product = get_product(reservation["product_id"], include_unreleased=True)
        product["inventory"]["reserved"] = max(
            product["inventory"]["reserved"] - reservation["quantity"],
            0,
        )
        _sync_available(product)
        reservation["status"] = "expired"


def list_products(
    *,
    include_unreleased: bool = False,
    category: str | None = None,
    featured: bool | None = None,
) -> list[dict]:
    _expire_reservations()
    products = []
    for product in _products:
        if not include_unreleased and product["status"] != "released":
            continue
        if category is not None and product["category"] != category:
            continue
        if featured is not None and product["is_featured"] != featured:
            continue
        products.append(deepcopy(product))
    return products


def get_product(product_id: int, *, include_unreleased: bool = False) -> dict:
    _expire_reservations()
    for product in _products:
        if product["id"] == product_id and (include_unreleased or product["status"] == "released"):
            return product
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")


def create_product(payload: dict) -> dict:
    if any(product["sku"] == payload["sku"] for product in _products):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU already exists")

    product_id = max(product["id"] for product in _products) + 1
    on_hand = payload.pop("on_hand", 0)
    product = {
        "id": product_id,
        **payload,
        "inventory": {
            "on_hand": on_hand,
            "reserved": 0,
            "available": on_hand,
            "low_stock_threshold": 5,
            "allow_backorder": False,
        },
        "active_promotions": [],
    }
    _products.append(product)
    return deepcopy(product)


def update_product(product_id: int, payload: dict) -> dict:
    product = get_product(product_id, include_unreleased=True)
    product.update({key: value for key, value in payload.items() if value is not None})
    return deepcopy(product)


def update_inventory(product_id: int, payload: dict) -> dict:
    product = get_product(product_id, include_unreleased=True)
    inventory = product["inventory"]
    inventory.update({key: value for key, value in payload.items() if value is not None})
    _sync_available(product)
    return deepcopy(product)


def add_promotion(product_id: int, payload: dict) -> dict:
    product = get_product(product_id, include_unreleased=True)
    promotion = {
        "id": len(product["active_promotions"]) + 1,
        **payload,
    }
    product["active_promotions"].append(promotion)
    return deepcopy(product)


def reserve_for_cart(product_id: int, *, user_id: str, cart_id: str, quantity: int) -> dict:
    product = get_product(product_id)
    inventory = product["inventory"]
    if inventory["available"] < quantity and not inventory["allow_backorder"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient inventory")

    expires_at = _now() + timedelta(seconds=settings.cart_reservation_ttl_seconds)
    inventory["reserved"] += quantity
    _sync_available(product)
    reservation = {
        "product_id": product_id,
        "cart_id": cart_id,
        "quantity": quantity,
        "status": "active",
        "expires_at": expires_at,
        "user_id": user_id,
    }
    _reservations.append(reservation)
    return deepcopy(reservation)
