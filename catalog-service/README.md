# Catalog Service

Auth0-protected product catalog, promotion, and inventory-reservation service for the e-commerce ecosystem.

Current responsibilities:

- Validate Auth0 bearer access tokens.
- Enforce route-level permissions from the token `permissions` claim.
- Expose released products and active promotions to end users.
- Expose product and inventory state to admins.
- Let super admins manage products, release state, inventory settings, and promotions.
- Reserve inventory when cart-service adds an item to a cart.
- Release cart reservations after the configured reservation TTL, defaulting to one hour.
- Provide SQLAlchemy/Postgres ORM scaffolding for the persisted catalog backend.

## Auth0 Configuration

`catalog-service` expects Auth0 and database settings from environment variables:

```env
DATABASE_URL=postgresql+psycopg://catalog:catalog@localhost:5432/catalog
AUTH0_DOMAIN=dev-lqyjuexwhe1bupvs.us.auth0.com
AUTH0_CLIENT_ID=hG5aklxMlkilsmsfF6HjuROKNsivDJLU
AUTH0_CLIENT_SECRET=...
AUTH0_AUDIENCE=https://user-service
AUTH0_CONNECTION=Username-Password-Authentication
CART_RESERVATION_TTL_SECONDS=3600
```

`catalog-service/.env` is intentionally ignored by Git. Do not commit secrets.

Auth0 API requirements:

- API identifier should match `AUTH0_AUDIENCE`.
- Signing algorithm: `RS256`.
- Enable RBAC.
- Enable "Add Permissions in the Access Token".
- User-service remains the access-management authority for Auth0 users, groups, roles, and permissions.

## Bootstrap Auth0 API Scopes

Create or update the custom API scopes used by user-service and catalog-service:

```bash
python3 scripts/create_auth0_scopes.py
```

The script reads Auth0 settings from exported environment variables first, then from `user-service/.env`.

Catalog API scopes:

```text
read:catalog_status
read:catalog_health
read:products
reserve:cart_inventory
read:inventory
manage:catalog
manage:inventory
manage:promotions
```

## Test Personas

Catalog testing needs three baseline human users in Auth0:

```text
end_user      Browse released products and reserve inventory through cart flows.
admin         Inspect catalog and inventory state without changing it.
super_admin   Manage catalog products, inventory settings, promotions, and user-service admin workflows.
```

Create or update active Auth0 test users and their matching roles:

```bash
python3 scripts/create_auth0_test_users.py
```

The script creates users with:

- `email_verified=true`
- `verify_email=false`
- `blocked=false`
- `app_metadata.registration_completed=true`
- one role per persona

Default test emails use `AUTH0_TEST_EMAIL_DOMAIN`, defaulting to `example.com`:

```text
test.end.user@example.com
test.admin@example.com
test.super.admin@example.com
```

Set `AUTH0_TEST_PASSWORD` to use a known password for newly created users. If omitted, the script generates a password but does not print it; set the variable when you need browser or Postman login.

## Endpoints

All application endpoints require an Auth0 bearer token and the listed scope.

Health/core:

```text
GET /                         read:catalog_status
GET /health/live              read:catalog_health
GET /health/ready             read:catalog_health
```

Shopper:

```text
GET  /products                                  read:products
GET  /products/{product_id}                     read:products
POST /products/{product_id}/cart-reservations   reserve:cart_inventory
```

Admin:

```text
GET /admin/catalog/requirements                 read:inventory
GET /admin/catalog/products                     read:inventory
GET /admin/catalog/products/{product_id}        read:inventory
```

Super admin:

```text
POST  /admin/catalog/products                          manage:catalog
PATCH /admin/catalog/products/{product_id}             manage:catalog
PATCH /admin/catalog/products/{product_id}/inventory   manage:inventory
POST  /admin/catalog/products/{product_id}/promotions  manage:promotions
```

## Inventory Reservation Behavior

When an end user adds a product to cart-service, cart-service should call:

```text
POST /products/{product_id}/cart-reservations
```

The catalog service should reduce available inventory while the cart item is active. If no checkout action occurs before `CART_RESERVATION_TTL_SECONDS`, the reservation expires and the inventory becomes available again.

The current scaffold uses seeded in-memory data for local API testing. SQLAlchemy models and database setup are present for moving this behavior to Postgres-backed repository calls.

## Local Development

Install dependencies:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

Run the service:

```bash
./start-catalog-service.sh
```

The service starts on port `8082`.

## Validation

Run from `catalog-service`:

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m compileall *.py routers/*.py services/*.py tests/*.py
```

Run from the repo root:

```bash
python3 -m compileall scripts/*.py
git diff --check
git status --short --ignored catalog-service/.env user-service/.env
```

Expected: service `.env` files are ignored, not staged.
