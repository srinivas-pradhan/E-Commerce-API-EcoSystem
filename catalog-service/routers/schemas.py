from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PromotionRead(BaseModel):
    id: int
    name: str
    promotion_type: str
    value: Decimal
    starts_at: datetime
    ends_at: datetime
    is_active: bool


class InventoryRead(BaseModel):
    on_hand: int
    reserved: int
    available: int
    low_stock_threshold: int
    allow_backorder: bool


class ProductRead(BaseModel):
    id: int
    sku: str
    name: str
    description: str
    category: str
    price: Decimal
    currency: str
    status: str
    is_featured: bool
    active_promotions: list[PromotionRead] = []


class ProductAdminRead(ProductRead):
    inventory: InventoryRead


class ProductCreateRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    description: str = ""
    category: str = Field(min_length=1, max_length=80)
    price: Decimal = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    on_hand: int = Field(default=0, ge=0)
    status: str = "draft"
    is_featured: bool = False


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    category: str | None = Field(default=None, min_length=1, max_length=80)
    price: Decimal | None = Field(default=None, gt=0)
    status: str | None = None
    is_featured: bool | None = None


class InventoryUpdateRequest(BaseModel):
    on_hand: int | None = Field(default=None, ge=0)
    low_stock_threshold: int | None = Field(default=None, ge=0)
    allow_backorder: bool | None = None


class PromotionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    promotion_type: str
    value: Decimal = Field(gt=0)
    starts_at: datetime
    ends_at: datetime
    is_active: bool = True


class CartReservationRequest(BaseModel):
    cart_id: str = Field(min_length=1, max_length=120)
    quantity: int = Field(gt=0)


class CartReservationRead(BaseModel):
    product_id: int
    cart_id: str
    quantity: int
    status: str
    expires_at: datetime


class RequirementsResponse(BaseModel):
    functional_requirements: list[str]
    access_model: dict[str, list[str]]
    api_groups: dict[str, list[str]]
