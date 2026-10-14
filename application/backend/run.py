#!/usr/bin/env python3
"""
Startup script for Network Data Lakehouse Backend

Performance configuration:
- Development mode (RELOAD=1): Single worker with hot reload
- Production mode (default): 4 workers for parallel request handling
"""
import os
import uvicorn

if __name__ == "__main__":
    # Check for development mode (hot reload) vs production (multiple workers)
    # Note: reload=True and workers>1 are mutually exclusive in uvicorn
    dev_mode = os.environ.get("RELOAD", "0") == "1"
    # Listen port: defaults to 8000 (override with PORT)
    port = int(os.environ.get("PORT", "8000"))

    if dev_mode:
        # Development: single worker with hot reload
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=port,
            reload=True,
            log_level="info",
        )
    else:
        # Production: multiple workers for better throughput
        # Number of workers = 2 * CPU cores + 1 is a common formula
        # Using 4 as a reasonable default that works with connection pool
        worker_count = int(os.environ.get("WORKERS", "4"))
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=port,
            workers=worker_count,
            log_level="info",
        )
