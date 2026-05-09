# Start Dev Environment

Standard flow to start the AIHelms local development environment.

## Prerequisites

1. Docker is running
2. `.env` file exists (copy from `.env.example` if not)
3. Python environment activated (conda activate aihelms)
4. Node.js and npm available

## Startup Flow

### Step 1: First Time Setup

```bash
./dev/setup
```

Or manually:
```bash
cp .env.example .env
cd apps && pip install -e ".[dev]"
cd ui && npm install
```

### Step 2: Start Middleware

```bash
./dev/start-docker-compose
```

Verify:
```bash
docker compose -f docker-compose.middleware.yaml -p aihelms ps
```

### Step 3: Backend

```bash
./dev/start-api
```

Verify: `curl http://localhost:8000/api/health` returns `{"status":"ok"}`

Optional — start Celery worker (async tasks):
```bash
./dev/start-worker
```

### Step 4: Frontend

```bash
# Admin panel
./dev/start-web

# Or user-facing app
cd ui && npm run dev --workspace=@aihelms/web
```

## Service Ports

| Service | Port | Description |
|---------|------|-------------|
| FastAPI | 8000 | Backend API + Swagger |
| Vue Admin | 5173 | Admin dev server |
| Vue Web | 5174 | User app dev server |
| PostgreSQL | DB_PORT (default 5432) | Database |
| Redis | REDIS_PORT (default 6379) | Cache |
| LiteLLM | LITELLM_PORT (default 4000) | Model proxy |
| Nginx | WEB_PORT (default 80) | Production gateway |

## Troubleshooting

### Database connection failed
```bash
docker compose -f docker-compose.middleware.yaml -p aihelms ps db
docker compose -f docker-compose.middleware.yaml -p aihelms logs db

# Rebuild database (will clear data)
docker compose -f docker-compose.middleware.yaml -p aihelms down -v
docker compose -f docker-compose.middleware.yaml -p aihelms up -d
```

### LiteLLM startup failed
```bash
docker compose -f docker-compose.middleware.yaml -p aihelms logs litellm

# Common cause: LITELLM_MASTER_KEY or LITELLM_SALT_KEY not set
grep LITELLM .env
```

### Frontend dependency install failed
```bash
# Clear cache and reinstall
rm -rf node_modules packages/*/node_modules
npm install
```

### Port already in use
```bash
lsof -i :8000
lsof -i :5173
```
