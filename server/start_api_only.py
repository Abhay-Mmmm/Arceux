"""Simple API server start without background log generator."""
import sys
import os
import threading

# Add server to path
sys.path.insert(0, os.path.dirname(__file__))

# Patch stdout for Windows encoding
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

# Just import and run api directly
from api import app
import uvicorn

print("[OK] Starting API server on port 8000...")

# Run server without threading
uvicorn.run(
    app,
    host="0.0.0.0",
    port=8000,
    log_level="info",
    access_log=False
)