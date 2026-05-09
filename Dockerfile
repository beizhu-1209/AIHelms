# Stage 1: Build frontend
FROM node:18-alpine AS frontend

WORKDIR /ui

COPY ui/package.json ./
COPY ui/packages/shared/package.json ./packages/shared/
COPY ui/packages/admin/package.json ./packages/admin/
COPY ui/packages/web/package.json ./packages/web/

RUN npm config set registry https://registry.npmmirror.com && npm install

COPY ui/ ./

RUN npm run build

# Stage 2: Build backend
FROM python:3.11

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

# Install Python dependencies
COPY apps/pyproject.toml ./apps/
RUN cd apps && uv pip install --system --index-url https://mirrors.aliyun.com/pypi/simple/ -e .

# Copy backend source
COPY apps/ ./apps/

# Copy built frontend from stage 1
COPY --from=frontend /ui/packages/web/dist ./ui/packages/web/dist/
COPY --from=frontend /ui/packages/admin/dist ./ui/packages/admin/dist/

WORKDIR /app/apps

EXPOSE 8000

CMD ["gunicorn", "main:app", "-c", "gunicorn_conf.py"]
