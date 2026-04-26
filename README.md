# Playto Payout Engine

A minimal payout engine for cross-border payments. Merchants can view balances, request payouts, and track status with strong money integrity guarantees.

## Stack

- **Backend:** Django + Django REST Framework
- **Task Queue:** Django-Q with PostgreSQL ORM broker (no Redis)
- **Frontend:** React + Vite + Tailwind CSS
- **Database:** PostgreSQL
- **Deployment:** Single-container via multi-stage Dockerfile

## Quick Start (Local)

Requires Docker and Docker Compose.

```bash
# Clone and start all services
docker-compose up --build

# Access points:
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000
# - Admin: http://localhost:8000/admin/
```

The `docker-compose.yml` spins up:
- PostgreSQL database
- Django web server (auto-migrates and seeds on start)
- Django-Q worker cluster
- Vite dev server with hot reload

## API Authentication

All API endpoints require the `Authorization: Api-Key <key>` header.

## Demo Data

The seed script creates 3 merchants with fixed balances:

| Merchant | API Key | Balance |
|----------|---------|---------|
| Acme Agency | `api-key-acme-agency` | ₹10,000 |
| Freelancer Fiaz | `api-key-freelancer-fiaz` | ₹5,000 |
| Tiny Studio | `api-key-tiny-studio` | ₹100 |

Use the Tiny Studio account (₹100) to test concurrency by firing two simultaneous ₹60 payout requests.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/me/` | Merchant profile + balances |
| GET | `/api/v1/ledger/` | Recent ledger entries |
| GET | `/api/v1/payouts/` | Payout history |
| POST | `/api/v1/payouts/` | Request payout (requires `Idempotency-Key` header) |

## Running Tests

```bash
docker-compose exec web python manage.py test payouts
```

## Deployment

Build the production image (bundles React into Django static files):

```bash
docker build -t playto-payout-engine ./backend
# The multi-stage Dockerfile builds the frontend and copies dist/ into Django
```

Environment variables for production:
- `SECRET_KEY` — Django secret key
- `DATABASE_URL` — PostgreSQL connection string
- `DEBUG=0`

## Architecture Decisions

See [EXPLAINER.md](EXPLAINER.md) for detailed reasoning on ledger design, concurrency control, idempotency, state machine, and AI audit.
