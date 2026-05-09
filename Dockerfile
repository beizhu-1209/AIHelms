FROM python:3.11

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

# Install Python dependencies
COPY apps/pyproject.toml ./apps/
RUN cd apps && uv pip install --system -e .

# Copy backend source
COPY apps/ ./apps/

# Copy pre-built frontend (run `cd ui && pnpm build` before docker build)
COPY ui/packages/web/dist ./ui/packages/web/dist/
COPY ui/packages/admin/dist ./ui/packages/admin/dist/

EXPOSE ${AIHELMS_PORT:-8000}

CMD uvicorn apps.main:app --host 0.0.0.0 --port ${AIHELMS_PORT:-8000}
