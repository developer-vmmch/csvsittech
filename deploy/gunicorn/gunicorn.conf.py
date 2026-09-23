# ============================================================
# Gunicorn Configuration for CSVS IT TECH (t3.micro Optimized)
# ============================================================

import multiprocessing
import os

# Server Socket
bind = os.getenv("GUNICORN_BIND", "unix:/run/gunicorn/csvsittech.sock")
backlog = 2048

# Worker Processes & Concurrency
# t3.micro has 1 vCPU / 1GB RAM. 2 workers with 2 threads is ideal.
workers = int(os.getenv("GUNICORN_WORKERS", 2))
threads = int(os.getenv("GUNICORN_THREADS", 2))
worker_class = "gthread"
worker_connections = 1000
timeout = 120
keepalive = 5

# Memory Leak Prevention: Automatically recycle workers after processing requests
max_requests = 1000
max_requests_jitter = 50

# Process Naming & Permissions
proc_name = "csvsittech_gunicorn"
user = "ubuntu"
group = "www-data"
umask = 0o007

# Logging
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"
capture_output = True

# Preload application code for faster worker spawning and memory sharing
preload_app = False
