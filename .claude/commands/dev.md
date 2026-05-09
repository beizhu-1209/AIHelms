# Start Dev Environment

Standard flow to start the AIHelms local development environment.

## Prerequisites

1. Docker is running
2. `.env` file exists (copy from `.env.example` if not)
3. Python environment activated (conda activate aihelms)
4. Node.js and pnpm available

## Startup Flow

### Step 1: Infrastructure

```bash
# Check .env exists
test -f .env || cp .env.example .env

# Start database, Redis, LiteLLM
docker compose up -d db redis litellm

# Wait for services to be ready
docker compose exec db pg_isready -U aihelms
docker compose exec redis redis-cli -a aihelms ping
```

### Step 2: Backend

```bash
cd apps

# First time: install dependencies
pip install -e ".[dev]"

# Start FastAPI (auto hot-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Verify: visit http://localhost:8000/api/docs to see Swagger UI

### Step 3: Frontend

```bash
cd ui

# First time: install dependencies
pnpm install

# Start dev servers
pnpm --filter web dev      # User app → http://localhost:3000
pnpm --filter admin dev    # Admin → http://localhost:3001
```

Verify: visit http://localhost:3000 to see the page

### Step 4: Full Integration (optional)

To test through Nginx unified gateway:

```bash
# Build frontend first
cd ui && pnpm build

# Start all services
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Verify: visit http://localhost to see the full app

## Service Ports

| Service | Port | Description |
|---------|------|-------------|
| FastAPI | 8000 | Backend API + Swagger |
| Vue Web | 3000 | User app dev server |
| Vue Admin | 3001 | Admin dev server |
| PostgreSQL | 5432 | Database (exposed in dev mode) |
| Redis | 6379 | Cache (exposed in dev mode) |
| LiteLLM | 4000 | Model proxy (container-only) |
| Nginx | 80 | Unified gateway (integration mode) |

## Troubleshooting

### Database connection failed
```bash
# Check db container status
docker compose ps db
docker compose logs db

# Rebuild database (will clear data)
docker compose down db -v && docker compose up -d db
```

### LiteLLM startup failed
```bash
# Check logs
docker compose logs litellm

# Common cause: LITELLM_MASTER_KEY or LITELLM_SALT_KEY not set
grep LITELLM .env
```

### Frontend dependency install failed
```bash
# Clear cache and reinstall
rm -rf node_modules packages/*/node_modules
pnpm install
```

### Port already in use
```bash
# Find process using the port
lsof -i :8000
lsof -i :3000
```
