#!/usr/bin/env python3
"""
Greeks Snapshot Scheduler

Schedules automatic Greeks snapshots 3x daily using APScheduler.

Schedule (Eastern Time):
- 8:00 AM - London Session (London is in full swing, captures overnight moves)
- 2:00 PM - US Session (Peak COMEX activity, good liquidity)
- 9:30 PM - Asian Session (Tokyo/Shanghai handoff from US)

Runs every day (gold trades nearly 24 hours).
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import pytz

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .greeks_snapshot_service import get_greeks_snapshot_service
from .logger import get_logger

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = get_logger()

# US Eastern timezone
ET = pytz.timezone('America/New_York')

# Scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


def is_trading_day() -> bool:
    """
    Check if today is a trading day.

    Returns True for Mon-Fri, excluding major US market holidays.
    Note: For production, integrate with a market calendar API.
    """
    now = datetime.now(ET)

    # Skip weekends
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False

    # Major US market holidays (simplified - add more as needed)
    # For production, use pandas_market_calendars or similar
    holidays = [
        (1, 1),   # New Year's Day
        (7, 4),   # Independence Day
        (12, 25), # Christmas Day
    ]

    if (now.month, now.day) in holidays:
        return False

    return True


async def run_london_session_snapshot(app: "FastAPI") -> None:
    """Run London session snapshot (8:00 AM ET). London is the world's largest gold trading hub."""
    logger.info("Greeks scheduler: Running London session snapshot...")
    try:
        service = get_greeks_snapshot_service(app)
        count = await service.fetch_and_persist_snapshots(
            underlying="GLD",
            snapshot_type="london_session"
        )
        logger.success(f"Greeks scheduler: London session snapshot complete ({count} records)")
    except Exception as e:
        logger.error(f"Greeks scheduler: London session snapshot failed: {e}")


async def run_us_session_snapshot(app: "FastAPI") -> None:
    """Run US session snapshot (2:00 PM ET). Peak COMEX activity with good liquidity."""
    logger.info("Greeks scheduler: Running US session snapshot...")
    try:
        service = get_greeks_snapshot_service(app)
        count = await service.fetch_and_persist_snapshots(
            underlying="GLD",
            snapshot_type="us_session"
        )
        logger.success(f"Greeks scheduler: US session snapshot complete ({count} records)")
    except Exception as e:
        logger.error(f"Greeks scheduler: US session snapshot failed: {e}")


async def run_asian_session_snapshot(app: "FastAPI") -> None:
    """Run Asian session snapshot (9:30 PM ET). Catches Tokyo/Shanghai handoff from US."""
    logger.info("Greeks scheduler: Running Asian session snapshot...")
    try:
        service = get_greeks_snapshot_service(app)
        count = await service.fetch_and_persist_snapshots(
            underlying="GLD",
            snapshot_type="asian_session"
        )
        logger.success(f"Greeks scheduler: Asian session snapshot complete ({count} records)")
    except Exception as e:
        logger.error(f"Greeks scheduler: Asian session snapshot failed: {e}")


def init_greeks_scheduler(app: "FastAPI") -> AsyncIOScheduler:
    """
    Initialize and start the Greeks snapshot scheduler.

    Args:
        app: FastAPI application instance

    Returns:
        Configured AsyncIOScheduler
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("Greeks scheduler already initialized")
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone=ET)

    # London Session: 8:00 AM ET (London in full swing, captures overnight moves)
    _scheduler.add_job(
        run_london_session_snapshot,
        CronTrigger(hour=8, minute=0, timezone=ET),
        args=[app],
        id='greeks_london_session',
        name='Greeks London Session Snapshot',
        replace_existing=True
    )

    # US Session: 2:00 PM ET (Peak COMEX activity, good liquidity)
    _scheduler.add_job(
        run_us_session_snapshot,
        CronTrigger(hour=14, minute=0, timezone=ET),
        args=[app],
        id='greeks_us_session',
        name='Greeks US Session Snapshot',
        replace_existing=True
    )

    # Asian Session: 9:30 PM ET (Tokyo/Shanghai handoff from US)
    _scheduler.add_job(
        run_asian_session_snapshot,
        CronTrigger(hour=21, minute=30, timezone=ET),
        args=[app],
        id='greeks_asian_session',
        name='Greeks Asian Session Snapshot',
        replace_existing=True
    )

    _scheduler.start()
    logger.success("Greeks scheduler started (3 daily jobs scheduled)")

    return _scheduler


def shutdown_greeks_scheduler() -> None:
    """Shutdown the scheduler gracefully."""
    global _scheduler

    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Greeks scheduler shutdown")
