#!/usr/bin/env python
"""
Celery worker entry point for async indexing jobs.

Run with: python -m src.worker
Or in docker: celery -A src.core.celery_app worker --loglevel=info
"""

import logging
import sys
from sqlalchemy import text
from src.core.celery_app import celery_app
from src.core.config import settings
from src.database.session import engine
from src.database.models import Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Start the Celery worker with proper initialization."""
    logger.info("Initializing worker...")

    # Validate database connectivity
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection OK")
    except Exception as exc:
        logger.error(f"Database connection failed: {exc}")
        sys.exit(1)

    # Ensure all tables exist
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema initialized")
    except Exception as exc:
        logger.error(f"Database schema initialization failed: {exc}")
        sys.exit(1)

    # Log worker configuration
    logger.info(f"Broker: {settings.celery_broker_url}")
    logger.info(f"Backend: {settings.celery_result_backend}")
    logger.info(f"Queue: {settings.celery_index_queue}")
    logger.info(f"Task name: {settings.index_document_task_name}")

    logger.info("Starting Celery worker...")
    try:
        celery_app.worker_main(
            [
                "worker",
                "--loglevel=info",
                f"--queues={settings.celery_index_queue}",
                "--concurrency=4",
            ]
        )
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        sys.exit(0)
    except Exception as exc:
        logger.error(f"Worker failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
