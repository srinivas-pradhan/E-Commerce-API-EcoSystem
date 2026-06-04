from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from auth import require_permissions
from routers.schemas import CartReservationRead, CartReservationRequest, ProductRead
from services.catalog_store import get_product, list_products, reserve_for_cart

router = APIRouter(prefix="/products", tags=["products"])

ProductReadPermission = Depends(require_permissions("read:products"))
CartReservePermission = Depends(require_permissions("reserve:cart_inventory"))


@router.get("", response_model=list[ProductRead])
def list_released_products(
    category: str | None = None,
    featured: Annotated[bool | None, Query()] = None,
    claims: dict[str, Any] = ProductReadPermission,
):
    return list_products(category=category, featured=featured)


@router.get("/{product_id}", response_model=ProductRead)
def read_released_product(product_id: int, claims: dict[str, Any] = ProductReadPermission):
    return get_product(product_id)


@router.post(
    "/{product_id}/cart-reservations",
    response_model=CartReservationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_cart_reservation(
    product_id: int,
    payload: CartReservationRequest,
    claims: dict[str, Any] = CartReservePermission,
):
    return reserve_for_cart(
        product_id,
        user_id=claims.get("sub", "unknown"),
        cart_id=payload.cart_id,
        quantity=payload.quantity,
    )
