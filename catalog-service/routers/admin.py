from typing import Any

from fastapi import APIRouter, Depends, status

from auth import require_permissions
from routers.schemas import (
    InventoryUpdateRequest,
    ProductAdminRead,
    ProductCreateRequest,
    ProductUpdateRequest,
    PromotionCreateRequest,
    RequirementsResponse,
)
from services.catalog_store import (
    add_promotion,
    create_product,
    get_product,
    list_products,
    update_inventory,
    update_product,
)

router = APIRouter(prefix="/admin/catalog", tags=["catalog-admin"])

InventoryReadPermission = Depends(require_permissions("read:inventory"))
CatalogManagePermission = Depends(require_permissions("manage:catalog"))
InventoryManagePermission = Depends(require_permissions("manage:inventory"))
PromotionManagePermission = Depends(require_permissions("manage:promotions"))


@router.get("/requirements", response_model=RequirementsResponse)
def read_catalog_requirements(claims: dict[str, Any] = InventoryReadPermission):
    return {
        "functional_requirements": [
            "End users can browse released products and active promotions.",
            "End users can reserve inventory when adding a product to a cart.",
            "Cart reservations reduce available inventory for one hour.",
            "Expired cart reservations release inventory back to the catalog.",
            "Admins can view complete product inventory counts.",
            "Super admins can create, release, archive, and feature products.",
            "Super admins can adjust inventory settings and promotion/sale metadata.",
            "Postgres is the system of record and ORM repositories own database queries.",
        ],
        "access_model": {
            "end_user": ["read:products", "reserve:cart_inventory"],
            "admin": ["read:products", "read:inventory"],
            "super_admin": [
                "read:products",
                "read:inventory",
                "manage:catalog",
                "manage:inventory",
                "manage:promotions",
            ],
        },
        "api_groups": {
            "shopper": ["GET /products", "GET /products/{product_id}", "POST /products/{product_id}/cart-reservations"],
            "admin": ["GET /admin/catalog/products", "GET /admin/catalog/products/{product_id}"],
            "super_admin": [
                "POST /admin/catalog/products",
                "PATCH /admin/catalog/products/{product_id}",
                "PATCH /admin/catalog/products/{product_id}/inventory",
                "POST /admin/catalog/products/{product_id}/promotions",
            ],
        },
    }


@router.get("/products", response_model=list[ProductAdminRead])
def list_admin_products(claims: dict[str, Any] = InventoryReadPermission):
    return list_products(include_unreleased=True)


@router.get("/products/{product_id}", response_model=ProductAdminRead)
def read_admin_product(product_id: int, claims: dict[str, Any] = InventoryReadPermission):
    return get_product(product_id, include_unreleased=True)


@router.post("/products", response_model=ProductAdminRead, status_code=status.HTTP_201_CREATED)
def create_admin_product(
    payload: ProductCreateRequest,
    claims: dict[str, Any] = CatalogManagePermission,
):
    return create_product(payload.model_dump())


@router.patch("/products/{product_id}", response_model=ProductAdminRead)
def update_admin_product(
    product_id: int,
    payload: ProductUpdateRequest,
    claims: dict[str, Any] = CatalogManagePermission,
):
    return update_product(product_id, payload.model_dump(exclude_none=True))


@router.patch("/products/{product_id}/inventory", response_model=ProductAdminRead)
def update_admin_inventory(
    product_id: int,
    payload: InventoryUpdateRequest,
    claims: dict[str, Any] = InventoryManagePermission,
):
    return update_inventory(product_id, payload.model_dump(exclude_none=True))


@router.post("/products/{product_id}/promotions", response_model=ProductAdminRead, status_code=status.HTTP_201_CREATED)
def create_admin_promotion(
    product_id: int,
    payload: PromotionCreateRequest,
    claims: dict[str, Any] = PromotionManagePermission,
):
    return add_promotion(product_id, payload.model_dump())
