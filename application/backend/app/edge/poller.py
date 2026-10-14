"""Primary-DC staging poller.

Runs only on the leader worker (started from main.startup_event under the
fcntl lock). Each cycle lists the staging incoming area, matches objects to
`staged` edge executions, retrieves each pcap, and runs it through the shared
pcap analysis pipeline (linking the resulting analysis back to the headend),
then marks the object processed.
"""
from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from datetime import datetime, timezone

from ..database import SessionLocal
from ..models import EdgeAnomalyExecutionModel
from ..pcap.analysis import analyze_pcap_file, persist_capture
from . import staging

log = logging.getLogger(__name__)

_POLL_INTERVAL_S = float(os.environ.get("EDGE_POLL_INTERVAL_S", "10"))

_task: asyncio.Task | None = None
_stop = asyncio.Event()


async def poll_once() -> int:
    """Ingest all currently-staged captures. Returns how many were processed."""
    processed = 0
    try:
        keys = await asyncio.to_thread(staging.list_incoming)
    except Exception as exc:  # noqa: BLE001
        log.warning("Staging list failed: %s", exc)
        return 0

    for key in keys:
        execution_id = staging.execution_id_from_key(key)
        with SessionLocal() as db:
            row = db.query(EdgeAnomalyExecutionModel).filter_by(execution_id=execution_id).first()
            if row is None or row.status != "staged":
                continue
            headend_id = row.headend_id
            row.status = "analyzing"
            db.commit()

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pcap")
        tmp.close()
        try:
            await asyncio.to_thread(staging.fetch, key, tmp.name)
            capture = await analyze_pcap_file(
                tmp.name,
                f"{execution_id}.pcap",
                source="edge",
                headend_id=headend_id,
                edge_execution_id=execution_id,
            )
            with SessionLocal() as db:
                persist_capture(db, capture)
                row = db.query(EdgeAnomalyExecutionModel).filter_by(execution_id=execution_id).first()
                if row is not None:
                    row.status = "completed"
                    row.analysis_id = capture.id
                    row.progress_percent = 100.0
                    row.completed_at = datetime.now(timezone.utc)
                    db.commit()
            await asyncio.to_thread(staging.mark_processed, key)
            processed += 1
            log.info("Edge execution %s analyzed → capture %s", execution_id, capture.id)
        except Exception as exc:  # noqa: BLE001
            log.exception("Ingest failed for %s", key)
            with SessionLocal() as db:
                row = db.query(EdgeAnomalyExecutionModel).filter_by(execution_id=execution_id).first()
                if row is not None:
                    row.status = "failed"
                    row.error = str(exc)
                    db.commit()
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    return processed


async def _loop() -> None:
    log.info("Edge staging poller started (interval=%ss)", _POLL_INTERVAL_S)
    while not _stop.is_set():
        try:
            await poll_once()
        except Exception:  # noqa: BLE001
            log.exception("Edge poll cycle error")
        try:
            await asyncio.wait_for(_stop.wait(), timeout=_POLL_INTERVAL_S)
        except asyncio.TimeoutError:
            pass


async def start() -> None:
    global _task
    if _task is not None:
        return
    _stop.clear()
    _task = asyncio.create_task(_loop())


async def stop() -> None:
    _stop.set()
