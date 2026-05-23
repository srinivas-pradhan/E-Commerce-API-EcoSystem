# E-Commerce API EcoSystem

FastAPI-based e-commerce microservice ecosystem. The current services are:

- [user-service](user-service/README.md)
- `catalog-service`
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

## Repository Notes

- `.env`, `.venv`, and `__pycache__` files are ignored.
- Do not commit service-local secrets.
- See [AGENTS.md](AGENTS.md) for repository-specific coding and operational guidelines.
