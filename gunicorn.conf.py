"""Production server settings for one Python application instance."""

import os

bind = "0.0.0.0:" + os.environ.get("PORT", "8000")
preload_app = True  # Import the lightweight app before worker forks; the encoder stays lazy.
workers = 1  # Share a single transformer in memory and one local SQLite database.
threads = 4
worker_class = "gthread"
timeout = 60
graceful_timeout = 60
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
accesslog = None  # Saved-result URLs contain private bearer tokens.
errorlog = "-"
capture_output = True
