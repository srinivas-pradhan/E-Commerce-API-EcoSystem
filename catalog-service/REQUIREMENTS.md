# Catalog Service Functional Requirements

## Purpose

The catalog service owns product discovery, release state, promotions, sales metadata, inventory visibility, and short-lived inventory reservations for carts.

## Access Model

- End users use Auth0-backed user-service identities and can browse released products and reserve items for a cart.
- Admins can read product inventory counts and catalog operational state.
- Super admins can manage products, releases, featured product flags, promotions, sale configuration, and inventory settings.
- Authorization is enforced with token permissions so user-service can map application groups to Auth0 roles.

## Functional Requirements

- Maintain products with SKU, name, description, category, price, currency, release status, and featured flag.
- Support dummy released products and draft products for local development and initial frontend integration.
- Expose only released products to end users.
- Expose unreleased, released, and archived products to admins.
- Maintain inventory counts: on-hand, reserved, available, low-stock threshold, and backorder setting.
- Let admins view inventory counts without changing them.
- Let super admins create products, update product metadata, change release state, and feature products.
- Let super admins update inventory settings and counts.
- Let super admins create promotions/sales with type, value, start time, end time, and active flag.
- Let end users reserve inventory when adding an item to cart-service.
- Reduce available inventory immediately while an item sits in a cart.
- Release reserved inventory back to availability when no checkout action occurs within one hour.
- Use Postgres as the backend system of record.
- Use ORM models/repositories for all database reads and writes.

## API Scaffold

### Shopper APIs

- `GET /products`
- `GET /products/{product_id}`
- `POST /products/{product_id}/cart-reservations`

### Admin APIs

- `GET /admin/catalog/requirements`
- `GET /admin/catalog/products`
- `GET /admin/catalog/products/{product_id}`

### Super Admin APIs

- `POST /admin/catalog/products`
- `PATCH /admin/catalog/products/{product_id}`
- `PATCH /admin/catalog/products/{product_id}/inventory`
- `POST /admin/catalog/products/{product_id}/promotions`

## Initial Permission Scopes

- `read:catalog_status`
- `read:catalog_health`
- `read:products`
- `reserve:cart_inventory`
- `read:inventory`
- `manage:catalog`
- `manage:inventory`
- `manage:promotions`
