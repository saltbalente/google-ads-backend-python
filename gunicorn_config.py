# Gunicorn configuration file
# https://docs.gunicorn.org/en/stable/settings.html

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"
backlog = 2048

# Worker processes
# Conservative: 4 workers for Render (512MB-1GB RAM)
# Formula: CPU × 2 + 1 can create too many workers on some plans
workers = int(os.getenv('WEB_CONCURRENCY', '4'))
worker_class = 'sync'
worker_connections = 1000

# Timeout settings
# CRITICAL: Increased for AI image optimization with Gemini
# - Image optimization can take 15-20s per image
# - 6 images × 20s = 120s minimum
# - Adding 3-minute buffer for API delays
timeout = 300  # 5 minutes (was 30s default)
graceful_timeout = 120
keepalive = 5

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'google-ads-backend'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
keyfile = None
certfile = None

# Debugging
reload = os.getenv('GUNICORN_RELOAD', 'false').lower() == 'true'
reload_engine = 'auto'

# Preload app for better performance
preload_app = True

# Worker lifecycle hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("🚀 Starting Gunicorn server with AI optimization support")

def on_reload(server):
    """Called when the server is reloaded."""
    server.log.info("🔄 Reloading server")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info(f"✅ Server ready on {bind} (timeout: {timeout}s)")

def worker_int(worker):
    """Called when a worker receives the INT or QUIT signal."""
    worker.log.info(f"⚠️ Worker {worker.pid} interrupted")

def worker_abort(worker):
    """Called when a worker times out."""
    worker.log.error(f"❌ Worker {worker.pid} timed out after {timeout}s")
    worker.log.error("This usually happens during AI image optimization")
    worker.log.error("Consider: 1) Reducing image count, 2) Increasing timeout")
