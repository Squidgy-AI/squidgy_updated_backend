# gunicorn_config.py
import os

# Force minimal workers for Heroku's 512MB memory limit
# Each worker loads the entire app, so fewer is better
workers = int(os.environ.get('WEB_CONCURRENCY', 2))
worker_class = 'uvicorn.workers.UvicornWorker'

# Timeout - set to 29 seconds (just under Heroku's 30-second limit)
timeout = 29
graceful_timeout = 29

# Keep alive
keepalive = 5

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Memory optimization
preload_app = True
worker_connections = 500
max_requests = 200  # Restart workers more frequently
max_requests_jitter = 50

# Limit threads per worker
threads = 1