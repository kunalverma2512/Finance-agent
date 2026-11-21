"""Simple in-process scheduler. Jobs are idempotent (alert dedupe keys) and guarded by a Postgres advisory
lock, so running several app instances is safe; for heavy load move this to a dedicated worker process."""
import asyncio
import logging

from starlette.concurrency import run_in_threadpool

from app.db.session import get_sessionmaker
from app.services.monitoring import run_all_users

log = logging.getLogger(__name__)


async def monitoring_loop(interval_minutes: int) -> None:
    while True:
        await asyncio.sleep(interval_minutes * 60)
        try:
            await run_in_threadpool(run_all_users, get_sessionmaker())
        except Exception:
            log.exception("monitoring_sweep_failed")
