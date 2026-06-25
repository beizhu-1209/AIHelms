#!/bin/bash
set -e

# Copy frontend dist to shared volume for nginx
echo "Copying frontend dist to shared volume..."
cp -r /app/ui/packages/web/dist/* /frontend/web/
cp -r /app/ui/packages/admin/dist/* /frontend/admin/
echo "Frontend dist copied successfully."

# Ensure data directories exist
mkdir -p /app/data/celerybeat /app/data/skills /app/data/uploads /app/data/exports
mkdir -p /logs

# Run database migrations before starting application processes
cd /app/apps
python -m core.migrate

# Start supervisord
exec supervisord -c /etc/supervisor/supervisord.conf
