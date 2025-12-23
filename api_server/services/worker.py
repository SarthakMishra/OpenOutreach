# api_server/services/worker.py
import logging
import threading
import time
from typing import Set

from api_server.db.engine import get_session
from api_server.db.models import Run
from api_server.services.executor import execute_run

logger = logging.getLogger(__name__)

# Global worker thread
_worker_thread: threading.Thread | None = None
_worker_running = False
_worker_lock = threading.Lock()

# Track runs currently being processed to avoid duplicates
_processing_runs: Set[str] = set()
_processing_lock = threading.Lock()


def _process_pending_runs() -> None:
    """Process pending runs from the database."""
    session = get_session()
    try:
        # Find pending runs
        pending_runs = session.query(Run).filter(Run.status == "pending").limit(10).all()

        for run in pending_runs:
            run_id = run.run_id  # type: ignore

            # Check if already being processed
            with _processing_lock:
                if run_id in _processing_runs:
                    continue
                _processing_runs.add(run_id)

            try:
                # Execute the run (this will update status in the background)
                execute_run(run_id)
                logger.debug("Started execution of pending run %s", run_id)
            except Exception as e:
                logger.error("Failed to start execution of run %s: %s", run_id, e, exc_info=True)
                # Remove from processing set on error
                with _processing_lock:
                    _processing_runs.discard(run_id)
    finally:
        session.close()


def _worker_thread_func() -> None:
    """Background worker that polls for pending runs."""
    logger.info("Background worker started")
    while _worker_running:
        try:
            _process_pending_runs()
        except Exception as e:
            logger.error("Error in background worker: %s", e, exc_info=True)

        # Sleep for 5 seconds before next poll
        for _ in range(5):
            if not _worker_running:
                break
            time.sleep(1)

    logger.info("Background worker stopped")


def start_worker() -> None:
    """Start the background worker thread."""
    global _worker_thread, _worker_running

    with _worker_lock:
        if _worker_running:
            logger.warning("Background worker already running")
            return

        _worker_running = True
        _worker_thread = threading.Thread(target=_worker_thread_func, daemon=True)
        _worker_thread.start()
        logger.info("Background worker started")


def stop_worker() -> None:
    """Stop the background worker thread."""
    global _worker_running

    with _worker_lock:
        if not _worker_running:
            return

        _worker_running = False
        if _worker_thread:
            _worker_thread.join(timeout=5.0)
        logger.info("Background worker stopped")
