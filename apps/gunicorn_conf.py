import multiprocessing
import os

workers = int(os.environ.get("GUNICORN_WORKERS", 0)) or (multiprocessing.cpu_count() * 2 + 1)
worker_class = "uvicorn.workers.UvicornWorker"
bind = f"0.0.0.0:{os.environ.get('AIHELMS_PORT', '8000')}"
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", 5))
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", 1000))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", 50))
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")

# Log to both stdout and file
log_dir = os.environ.get("LOG_DIR", "/logs")
os.makedirs(log_dir, exist_ok=True)
accesslog = os.path.join(log_dir, "gunicorn_access.log")
errorlog = os.path.join(log_dir, "gunicorn_error.log")
