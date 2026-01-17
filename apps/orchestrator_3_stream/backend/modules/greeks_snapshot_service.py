#!/usr/bin/env python3
"""
Greeks Snapshot Service

Fetches and persists option Greeks snapshots from Alpaca API.

Key Features:
- Uses OptionHistoricalDataClient for snapshot data
- Handles pagination for large option chains
- Persists to option_greeks_snapshots table
- Supports manual and scheduled triggers

IMPORTANT: Use app.state pattern, not global singleton.
Initialize via init_greeks_snapshot_service(app) in lifespan.
"""

import asyncio
import json
from datetime import datetime, date, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import UUID

import asyncpg
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionChainRequest

from .alpaca_models import OCCSymbol
from .config import ALPACA_API_KEY, ALPACA_SECRET_KEY, DATABASE_URL
from .logger import get_logger
from .orch_database_models import OptionGreeksSnapshot

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = get_logger()


class GreeksSnapshotService:
    """
    Service for fetching and persisting option Greeks snapshots.

    Responsibilities:
    - Fetch option chain snapshots from Alpaca
    - Parse Greeks and pricing data
    - Persist to PostgreSQL with upsert logic
    - Support multiple underlyings (initially GLD)
    """

    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        """
        Initialize the service.

        Args:
            db_pool: Optional asyncpg connection pool (created if not provided)
        """
        self._db_pool = db_pool
        self._option_client: Optional[OptionHistoricalDataClient] = None
        self._is_configured = bool(ALPACA_API_KEY and ALPACA_SECRET_KEY)

    @property
    def is_configured(self) -> bool:
        """Check if Alpaca credentials are configured."""
        return self._is_configured

    def _get_option_client(self) -> OptionHistoricalDataClient:
        """Get or create OptionHistoricalDataClient."""
        if self._option_client is None:
            self._option_client = OptionHistoricalDataClient(
                api_key=ALPACA_API_KEY,
                secret_key=ALPACA_SECRET_KEY
            )
        return self._option_client

    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create database connection pool."""
        if self._db_pool is None:
            self._db_pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=2,
                max_size=10
            )
            logger.info("GreeksSnapshotService: Database pool created")
        return self._db_pool

    async def close(self) -> None:
        """Close database connections."""
        if self._db_pool:
            await self._db_pool.close()
            self._db_pool = None
            logger.info("GreeksSnapshotService: Database pool closed")

    # ═══════════════════════════════════════════════════════════
    # SNAPSHOT FETCHING
    # ═══════════════════════════════════════════════════════════

    async def fetch_and_persist_snapshots(
        self,
        underlying: str = "GLD",
        snapshot_type: str = "manual"
    ) -> int:
        """
        Fetch option chain snapshots and persist to database.

        Args:
            underlying: Underlying symbol (default: GLD)
            snapshot_type: Type of snapshot (london_session, us_session, asian_session, manual)

        Returns:
            Number of snapshots persisted
        """
        if not self._is_configured:
            logger.warning("GreeksSnapshotService: Alpaca not configured - skipping snapshot")
            return 0

        try:
            snapshot_at = datetime.now(timezone.utc)
            logger.info(f"Fetching {underlying} options snapshots ({snapshot_type})...")

            # Fetch snapshots with pagination
            all_snapshots = await self._fetch_all_snapshots(underlying)

            if not all_snapshots:
                logger.warning(f"No snapshots returned for {underlying}")
                return 0

            logger.info(f"Fetched {len(all_snapshots)} option contracts for {underlying}")

            # Persist to database
            persisted_count = await self._persist_snapshots(
                snapshots=all_snapshots,
                underlying=underlying,
                snapshot_at=snapshot_at,
                snapshot_type=snapshot_type
            )

            logger.success(f"Persisted {persisted_count} Greeks snapshots for {underlying}")
            return persisted_count

        except Exception as e:
            logger.error(f"Failed to fetch/persist snapshots for {underlying}: {e}")
            raise

    async def _fetch_all_snapshots(self, underlying: str) -> Dict[str, Any]:
        """
        Fetch all option snapshots for an underlying using the Option Chain API.

        Uses OptionChainRequest with underlying_symbol to fetch all options
        for the underlying symbol. This returns Greeks data for all contracts.

        Args:
            underlying: Underlying symbol (e.g., "GLD")

        Returns:
            Dictionary of symbol -> OptionsSnapshot data
        """
        client = self._get_option_client()
        loop = asyncio.get_running_loop()

        # Build request using OptionChainRequest which accepts underlying_symbol
        # This is the correct approach for fetching all options for an underlying
        request = OptionChainRequest(
            underlying_symbol=underlying,
            feed="opra"  # Use OPRA feed (Elite subscription)
        )

        # Fetch option chain snapshots (sync call in executor)
        # get_option_chain returns Dict[str, OptionsSnapshot] with Greeks for all contracts
        response = await loop.run_in_executor(
            None,
            lambda: client.get_option_chain(request)
        )

        # Response is Dict[str, OptionsSnapshot] - return directly
        return response if response else {}

    async def _persist_snapshots(
        self,
        snapshots: Dict[str, Any],
        underlying: str,
        snapshot_at: datetime,
        snapshot_type: str
    ) -> int:
        """
        Persist snapshots to database.

        Args:
            snapshots: Dictionary of symbol -> snapshot data
            underlying: Underlying symbol
            snapshot_at: Timestamp of snapshot
            snapshot_type: Type of snapshot

        Returns:
            Number of records persisted
        """
        pool = await self._get_pool()
        persisted = 0

        async with pool.acquire() as conn:
            # Use a transaction for batch insert
            async with conn.transaction():
                for symbol, snapshot in snapshots.items():
                    try:
                        # Validate OCC symbol format before parsing
                        # OCC symbols are typically 21 characters (e.g., GLD250117C00200000)
                        if not symbol or len(symbol) < 15:
                            logger.warning(f"Invalid OCC symbol format (too short): {symbol}")
                            continue

                        # Parse OCC symbol with explicit error handling
                        try:
                            occ = OCCSymbol.parse(symbol)
                        except (ValueError, AttributeError) as parse_error:
                            logger.warning(f"Failed to parse OCC symbol '{symbol}': {parse_error}")
                            continue

                        # Extract Greeks (handle both dict and object access)
                        greeks = snapshot.greeks if hasattr(snapshot, 'greeks') else snapshot.get('greeks', {})
                        quote = snapshot.latest_quote if hasattr(snapshot, 'latest_quote') else snapshot.get('latestQuote', {})
                        trade = snapshot.latest_trade if hasattr(snapshot, 'latest_trade') else snapshot.get('latestTrade', {})

                        # Extract implied_volatility from snapshot level (not in greeks object)
                        # OptionsSnapshot has: symbol, latest_trade, latest_quote, implied_volatility, greeks
                        if hasattr(snapshot, 'implied_volatility'):
                            iv = snapshot.implied_volatility
                        else:
                            iv = snapshot.get('implied_volatility') if isinstance(snapshot, dict) else None

                        # Handle attribute vs dict access for greeks
                        # OptionsGreeks model has: delta, gamma, theta, vega, rho (no implied_volatility)
                        if hasattr(greeks, 'delta'):
                            delta = greeks.delta
                            gamma = greeks.gamma
                            theta = greeks.theta
                            vega = greeks.vega
                            rho = greeks.rho
                        else:
                            delta = greeks.get('delta') if greeks else None
                            gamma = greeks.get('gamma') if greeks else None
                            theta = greeks.get('theta') if greeks else None
                            vega = greeks.get('vega') if greeks else None
                            rho = greeks.get('rho') if greeks else None

                        # Extract pricing
                        if hasattr(quote, 'bid_price'):
                            bid = quote.bid_price
                            ask = quote.ask_price
                        else:
                            bid = quote.get('bp') if quote else None  # API uses 'bp' for bid_price
                            ask = quote.get('ap') if quote else None  # API uses 'ap' for ask_price

                        mid = (float(bid) + float(ask)) / 2 if bid and ask else None

                        if hasattr(trade, 'price'):
                            last_price = trade.price
                        else:
                            last_price = trade.get('p') if trade else None  # API uses 'p' for price

                        # Build raw_data
                        raw_data = {
                            'greeks': greeks if isinstance(greeks, dict) else (
                                {'delta': delta, 'gamma': gamma, 'theta': theta, 'vega': vega, 'rho': rho, 'iv': iv}
                            ),
                            'quote': quote if isinstance(quote, dict) else {'bid': bid, 'ask': ask},
                            'trade': trade if isinstance(trade, dict) else {'price': last_price}
                        }

                        # Upsert to database
                        await conn.execute("""
                            INSERT INTO option_greeks_snapshots (
                                snapshot_at, snapshot_type,
                                symbol, underlying, expiry_date, strike_price, option_type,
                                delta, gamma, theta, vega, rho, implied_volatility,
                                underlying_price, bid_price, ask_price, mid_price, last_trade_price,
                                volume, open_interest, raw_data
                            ) VALUES (
                                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                                $14, $15, $16, $17, $18, $19, $20, $21
                            )
                            ON CONFLICT (symbol, snapshot_at)
                            DO UPDATE SET
                                delta = EXCLUDED.delta,
                                gamma = EXCLUDED.gamma,
                                theta = EXCLUDED.theta,
                                vega = EXCLUDED.vega,
                                rho = EXCLUDED.rho,
                                implied_volatility = EXCLUDED.implied_volatility,
                                bid_price = EXCLUDED.bid_price,
                                ask_price = EXCLUDED.ask_price,
                                mid_price = EXCLUDED.mid_price,
                                last_trade_price = EXCLUDED.last_trade_price,
                                raw_data = EXCLUDED.raw_data
                        """,
                            snapshot_at,
                            snapshot_type,
                            symbol,
                            underlying,
                            occ.expiry_date,
                            occ.strike_price,
                            occ.option_type.lower(),
                            delta,
                            gamma,
                            theta,
                            vega,
                            rho,
                            iv,
                            None,  # underlying_price - would need separate fetch
                            bid,
                            ask,
                            mid,
                            last_price,
                            0,  # volume - not in snapshot response
                            0,  # open_interest - not in snapshot response
                            json.dumps(raw_data)
                        )

                        persisted += 1

                    except Exception as e:
                        logger.warning(f"Failed to persist snapshot for {symbol}: {e}")
                        continue

        return persisted

    # ═══════════════════════════════════════════════════════════
    # QUERY METHODS
    # ═══════════════════════════════════════════════════════════

    async def get_latest_snapshots(
        self,
        underlying: str = "GLD",
        limit: int = 100
    ) -> List[OptionGreeksSnapshot]:
        """
        Get latest Greeks snapshots for an underlying.

        Args:
            underlying: Underlying symbol
            limit: Maximum records to return

        Returns:
            List of OptionGreeksSnapshot records
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM option_greeks_snapshots
                WHERE underlying = $1
                ORDER BY snapshot_at DESC, symbol
                LIMIT $2
            """, underlying, limit)

            return [OptionGreeksSnapshot(**dict(row)) for row in rows]

    async def get_greeks_history(
        self,
        symbol: str,
        days: int = 30,
        limit: int = 1000
    ) -> List[OptionGreeksSnapshot]:
        """
        Get Greeks history for a specific option symbol.

        Args:
            symbol: OCC option symbol
            days: Number of days of history
            limit: Maximum records to return

        Returns:
            List of OptionGreeksSnapshot records ordered by snapshot_at ASC
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM option_greeks_snapshots
                WHERE symbol = $1
                  AND snapshot_at >= NOW() - make_interval(days => $2)
                ORDER BY snapshot_at ASC
                LIMIT $3
            """, symbol, days, limit)

            return [OptionGreeksSnapshot(**dict(row)) for row in rows]


# ═══════════════════════════════════════════════════════════
# APP.STATE INITIALIZATION
# ═══════════════════════════════════════════════════════════

async def init_greeks_snapshot_service(app: "FastAPI") -> GreeksSnapshotService:
    """
    Initialize GreeksSnapshotService and store in app.state.

    IMPORTANT: Call this in FastAPI lifespan startup.

    Args:
        app: FastAPI application instance

    Returns:
        Initialized GreeksSnapshotService
    """
    service = GreeksSnapshotService()
    app.state.greeks_snapshot_service = service

    if service.is_configured:
        logger.success("GreeksSnapshotService initialized and ready")
    else:
        logger.warning("GreeksSnapshotService: Alpaca not configured - snapshots disabled")

    return service


def get_greeks_snapshot_service(app: "FastAPI") -> GreeksSnapshotService:
    """
    Get GreeksSnapshotService from app.state.

    Args:
        app: FastAPI application instance

    Returns:
        GreeksSnapshotService instance

    Raises:
        RuntimeError: If service not initialized
    """
    if not hasattr(app.state, 'greeks_snapshot_service'):
        raise RuntimeError("GreeksSnapshotService not initialized. Call init_greeks_snapshot_service() in lifespan.")
    return app.state.greeks_snapshot_service
