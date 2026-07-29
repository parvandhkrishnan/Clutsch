"""Gunicorn configuration for running Uvicorn workers in production.

Recommended worker count: 2 * CPU cores + 1
For a typical 4-core machine: 9 workers
For a 2-core machine: 5 workers
"""
import os
import multiprocessing

# Bind to the port the platform expects. Hosting platforms like Render
# assign a port dynamically via the PORT env var rather than a fixed one.
bind = f"0.0.0.0:{os.environ.get('PORT', 8001)}"

# Worker count: 2-4 per CPU core is standard for Uvicorn workers
# In production set WORKERS env var, otherwise auto-detect
cpu_count = multiprocessing.cpu_count()
workers = int(os.environ.get("CLUTSCH_WORKERS", cpu_count * 2 + 1))

# Use Uvicorn workers for async ASGI support
worker_class = "uvicorn.workers.UvicornWorker"

# Timeout settings
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("CLUTSCH_LOG_LEVEL", "info")

# Restart workers after this many requests to prevent memory leaks
max_requests = 10000
max_requests_jitter = 1000

# Preload app for faster worker startup
preload_app = True