import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class ProductStatus(str, enum.Enum):
    draft = "draft"
    released = "released"
    archived = "archived"


class PromotionType(str, enum.Enum):
    percentage = "percentage"
    fixed_amount = "fixed_amount"


class ReservationStatus(str, enum.Enum):
    active = "active"
    released = "released"
    converted = "converted"
    expired = "expired"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(80), index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[ProductStatus] = mapped_column(Enum(ProductStatus), default=ProductStatus.draft)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    inventory: Mapped["Inventory"] = relationship(back_populates="product", cascade="all, delete-orphan")
    promotions: Mapped[list["Promotion"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class Inventory(Base):
    __tablename__ = "inventory"

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
    on_hand: Mapped[int] = mapped_column(Integer, default=0)
    reserved: Mapped[int] = mapped_column(Integer, default=0)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=5)
    allow_backorder: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product: Mapped[Product] = relationship(back_populates="inventory")


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    promotion_type: Mapped[PromotionType] = mapped_column(Enum(PromotionType))
    value: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    product: Mapped[Product] = relationship(back_populates="promotions")


class CartReservation(Base):
    __tablename__ = "cart_reservations"
    __table_args__ = (UniqueConstraint("cart_id", "product_id", name="uq_cart_product_reservation"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[str] = mapped_column(String(120), index=True)
    user_id: Mapped[str] = mapped_column(String(160), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[ReservationStatus] = mapped_column(Enum(ReservationStatus), default=ReservationStatus.active)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
