# Stage 1: Build frontend
FROM node:18-alpine AS frontend

ARG NPM_MIRROR=https://registry.npmmirror.com

WORKDIR /ui

COPY ui/package.json ./
COPY ui/packages/shared/package.json ./packages/shared/
COPY ui/packages/admin/package.json ./packages/admin/
COPY ui/packages/web/package.json ./packages/web/

RUN npm config set registry ${NPM_MIRROR} && npm install

COPY ui/ ./

# Resolve symlinks that point to absolute paths (web/assets/providers -> admin/assets/providers)
RUN if [ -L packages/web/src/assets/providers ]; then \
      rm packages/web/src/assets/providers && \
      cp -r packages/admin/src/assets/providers packages/web/src/assets/providers; \
    fi

# Skip vue-tsc type checking in Docker build (CI handles type checks)
RUN npm run build --workspace=@aihelms/shared \
    && cd packages/admin && npx vite build && cd ../.. \
    && cd packages/web && npx vite build

# Stage 2: Build backend
FROM python:3.11-slim-bookworm

ARG APT_MIRROR=mirrors.aliyun.com
ARG PIP_INDEX=https://mirrors.aliyun.com/pypi/simple/

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

# Install Python dependencies + supervisor
COPY apps/pyproject.toml ./apps/
RUN sed -i "s|deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev \
    && cd apps && uv pip install --system --index-url ${PIP_INDEX} -e . \
    && uv pip install --system --index-url ${PIP_INDEX} supervisor \
    && apt-get purge -y gcc libffi-dev && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Copy backend source
COPY apps/ ./apps/
COPY docker/db/migrations/ ./docker/db/migrations/

# Copy built frontend from stage 1
COPY --from=frontend /ui/packages/web/dist ./ui/packages/web/dist/
COPY --from=frontend /ui/packages/admin/dist ./ui/packages/admin/dist/

# Copy supervisor config and startup script
COPY docker/supervisor/supervisord.conf /etc/supervisor/supervisord.conf
COPY docker/supervisor/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Create frontend volume mount points
RUN mkdir -p /frontend/web /frontend/admin

WORKDIR /app/apps

EXPOSE 8000

CMD ["/app/start.sh"]
