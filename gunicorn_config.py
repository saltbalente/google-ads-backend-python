# Gunicorn configuration file
# https://docs.gunicorn.org/en/stable/settings.html

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"
backlog = 2048

# Worker processes
# 🔧 OPTIMIZADO PARA 512MB RAM
# Con el nuevo Design Intelligence System cargado en memoria:
# - Cada worker usa ~120-150MB
# - 512MB / 150MB = ~3 workers seguros
# - Dejamos 1 worker para evitar OOM (Out of Memory)
# IMPORTANTE: Ignoramos WEB_CONCURRENCY de Render porque suele calcularlo basado en CPU
# y nos asigna demasiados workers (ej. 8) lo que causa crash por memoria.
workers = 2 
worker_class = 'sync'
worker_connections = 1000

# Max requests per worker (helps prevent memory leaks)
max_requests = 1000
max_requests_jitter = 50

# Timeout settings
# CRITICAL: Increased for AI image optimization with Gemini
# - Image optimization can take 15-20s per image
# - 6 images × 20s = 120s minimum
# - Adding 3-minute buffer for API delays
# Professional Plan: Can handle longer timeouts safely with autoscaling
# Increased to match client timeout (600s) for consistency
timeout = 600  # 10 minutes (increased from 300s)
graceful_timeout = 120
keepalive = 5

# Threading - REDUCIDO para ahorrar memoria
# 2 workers × 1 thread = 2 concurrent requests (suficiente para tu uso)
threads = 1  # Reducido de 2 a 1 para ahorrar ~50MB por worker

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
    server.log.info(f"✅ Server ready on {bind}")
    server.log.info(f"⚙️  Configuration: {workers} workers (sync) = {workers} concurrent requests")
    server.log.info(f"⏱️  Timeout: {timeout}s (AI optimization support)")
    server.log.info(f"🚀 Professional Plan: Autoscaling enabled, 500GB bandwidth")

def worker_int(worker):
    """Called when a worker receives the INT or QUIT signal."""
    worker.log.info(f"⚠️ Worker {worker.pid} interrupted")

def worker_abort(worker):
    """Called when a worker times out."""
    worker.log.error(f"❌ Worker {worker.pid} timed out after {timeout}s")
    worker.log.error("This usually happens during AI image optimization")
    worker.log.error("Consider: 1) Reducing image count, 2) Increasing timeout")
