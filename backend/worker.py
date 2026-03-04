"""Standalone background worker process.

Runs APScheduler jobs independently of the API server so that:
- Scaling API to multiple uvicorn workers doesn't duplicate jobs
- Jobs and API can be deployed/restarted independently
- OOM in a heavy job doesn't take down the API

Usage:
    python worker.py

Deploy on Railway as a separate service with:
    DISABLE_BACKGROUND_JOBS=true on the API service
    This worker runs the scheduler instead.

In development, you don't need this — the API starts the scheduler itself
(DISABLE_BACKGROUND_JOBS defaults to False).
"""

import asyncio
import logging
import signal
import sys

# Configure logging before any app imports
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
)

logger = logging.getLogger("udl.worker")


def main():
    from app.services.background_jobs import start_background_jobs, stop_background_jobs

    logger.info("Starting UDL background worker...")
    start_background_jobs()
    logger.info("Background worker running. Press Ctrl+C to stop.")

    # Block until SIGINT/SIGTERM
    shutdown_event = asyncio.Event()

    def _signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(shutdown_event.wait())
    finally:
        stop_background_jobs()
        loop.close()
        logger.info("Worker shut down cleanly.")


if __name__ == "__main__":
    main()
