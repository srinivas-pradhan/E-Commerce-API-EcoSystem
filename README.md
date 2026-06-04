# E-Commerce API EcoSystem

FastAPI-based e-commerce microservice ecosystem. The current services are:

- [user-service](user-service/README.md)
- [catalog-service](catalog-service/README.md)
- `cart-service`
- `order-service`
- `payment-service`
- `notification-service`

Each service has its own `main.py`, `requirements.txt`, and `start-*-service.sh` runner.

## User Service

`user-service` is the Auth0-backed identity and user administration service.

See [user-service/README.md](user-service/README.md) for:

- Auth0 configuration
- required Auth0 scopes
- endpoint inventory
- local development commands
- validation workflow

## Catalog Service

`catalog-service` is the Auth0-protected product catalog, promotion, and inventory-reservation service.

See [catalog-service/README.md](catalog-service/README.md) for:

- catalog Auth0 scopes
- required test personas
- product, inventory, promotion, and cart-reservation endpoints
- Postgres/ORM direction
- local development commands
- validation workflow

## Repository Notes

- `.env`, `.venv`, and `__pycache__` files are ignored.
- Do not commit service-local secrets.
- See [AGENTS.md](AGENTS.md) for repository-specific coding and operational guidelines.
