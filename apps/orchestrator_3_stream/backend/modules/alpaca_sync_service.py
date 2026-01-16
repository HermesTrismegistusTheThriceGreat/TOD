#!/usr/bin/env python3
"""
Alpaca Sync Service

Syncs Alpaca order history and positions to the database.

Key Features:
- Fetches and persists order history from Alpaca
- Fetches and persists open positions
- Assigns trade_id to link related orders (same underlying, expiry, time window)
- Detects strategy types from order patterns

IMPORTANT: Use app.state pattern, not global singleton.
Initialize via init_alpaca_sync_service(app) in lifespan.
"""

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import UUID, uuid4

import asyncpg

from .alpaca_models import OCCSymbol
from .alpaca_service import AlpacaService
from .config import DATABASE_URL
from .logger import get_logger

# Import models for type hints
import sys
from pathlib import Path

# Add orchestrator_db to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "orchestrator_db"))
from models import AlpacaOrder, AlpacaPosition

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = get_logger()

# Time window for grouping orders into trades (5 minutes)
TRADE_GROUPING_TIME_WINDOW = timedelta(minutes=5)


class AlpacaSyncService:
    """
    Service for syncing Alpaca data to database.

    Responsibilities:
    - Fetch and persist order history
    - Fetch and persist open positions
    - Assign trade_ids to link related orders
    - Detect strategy types from order patterns
    """

    def __init__(self, alpaca_service: AlpacaService, db_pool: Optional[asyncpg.Pool] = None):
        """
        Initialize the sync service.

        Args:
            alpaca_service: AlpacaService instance for API calls
            db_pool: Optional asyncpg connection pool (created if not provided)
        """
        self._alpaca_service = alpaca_service
        self._db_pool = db_pool

    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create database connection pool."""
        if self._db_pool is None:
            self._db_pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=2,
                max_size=10
            )
            logger.info("AlpacaSyncService: Database pool created")
        return self._db_pool

    async def close(self) -> None:
        """Close database connections."""
        if self._db_pool:
            await self._db_pool.close()
            self._db_pool = None
            logger.info("AlpacaSyncService: Database pool closed")

    # ═══════════════════════════════════════════════════════════
    # ORDER SYNCING
    # ═══════════════════════════════════════════════════════════

    async def sync_orders(
        self,
        since: Optional[datetime] = None,
        status: Optional[str] = None
    ) -> List[AlpacaOrder]:
        """
        Fetch and sync order history from Alpaca using Account Activities API.

        NOTE: Uses Account Activities API with activity_type=FILL to get historical fills.
        This is more reliable than get_orders() which only returns recent/active orders.

        Args:
            since: Only fetch activities after this datetime (default: last 30 days)
            status: Ignored (activities are always filled orders)

        Returns:
            List of synced AlpacaOrder records
        """
        if not self._alpaca_service.is_configured:
            logger.warning("AlpacaSyncService: Alpaca not configured - skipping order sync")
            return []

        try:
            # Fetch activities from Alpaca
            client = self._alpaca_service._get_trading_client()
            loop = asyncio.get_running_loop()

            # Default to last 30 days
            if since is None:
                since = datetime.now() - timedelta(days=30)

            # Build query params for Account Activities API
            # GET /account/activities?activity_types=FILL&after=<timestamp>
            params = {
                'activity_types': 'FILL',
                'after': since.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'direction': 'desc',  # Most recent first
                'page_size': 100,  # Max page size allowed by Alpaca API
            }

            # Fetch activities using direct REST call (sync call in executor)
            # TradingClient.get() returns the raw response
            activities = await loop.run_in_executor(
                None,
                lambda: client.get('/account/activities', data=params)
            )

            # Handle pagination if needed
            all_activities = []
            if isinstance(activities, list):
                all_activities = activities
            else:
                # Single activity returned
                all_activities = [activities] if activities else []

            logger.info(f"Fetched {len(all_activities)} fill activities from Alpaca")

            if not all_activities:
                return []

            # Convert activities to order dicts
            order_dicts = []
            for activity in all_activities:
                try:
                    # Account Activities return different structure than Orders
                    # Activity fields: id, activity_type, transaction_time, type (fill/partial_fill),
                    #                  price, qty, side, symbol, cum_qty, leaves_qty, order_id

                    symbol = activity.get('symbol', '')

                    # Parse OCC symbol for option details
                    occ = None
                    underlying = None
                    expiry_date = None
                    strike_price = None
                    option_type = None

                    try:
                        occ = OCCSymbol.parse(symbol)
                        underlying = occ.underlying
                        expiry_date = occ.expiry_date
                        strike_price = occ.strike_price
                        option_type = occ.option_type.lower() if occ.option_type else None
                    except ValueError:
                        # Not an option symbol, use as-is
                        underlying = symbol

                    # Map activity to order dict structure
                    # Use activity id as order id (or order_id if available)
                    order_id = activity.get('order_id') or activity.get('id')
                    transaction_time = activity.get('transaction_time')

                    # Parse transaction_time if it's a string
                    if isinstance(transaction_time, str):
                        transaction_time = datetime.fromisoformat(transaction_time.replace('Z', '+00:00'))

                    order_dict = {
                        'id': str(order_id),
                        'client_order_id': None,  # Not available in activities
                        'symbol': symbol,
                        'underlying': underlying,
                        'side': activity.get('side', '').lower(),
                        'qty': float(activity.get('qty', 0)),
                        'filled_qty': float(activity.get('qty', 0)),  # FILL activities are fully filled
                        'order_type': 'market',  # Not available, assume market
                        'time_in_force': 'day',  # Not available, assume day
                        'limit_price': None,  # Not available in fill activities
                        'stop_price': None,  # Not available in fill activities
                        'filled_avg_price': float(activity.get('price', 0)),
                        'status': 'filled',  # FILL activities are always filled
                        'expiry_date': expiry_date,
                        'strike_price': strike_price,
                        'option_type': option_type,
                        'submitted_at': transaction_time,  # Use transaction time as proxy
                        'filled_at': transaction_time,
                        'expired_at': None,
                        'canceled_at': None,
                        'raw_data': {
                            'activity_id': str(activity.get('id')) if activity.get('id') else None,
                            'activity_type': str(activity.get('activity_type')) if activity.get('activity_type') else None,
                            'type': str(activity.get('type')) if activity.get('type') else None,
                            'cum_qty': float(activity.get('cum_qty')) if activity.get('cum_qty') else None,
                            'leaves_qty': float(activity.get('leaves_qty')) if activity.get('leaves_qty') else None,
                        }
                    }
                    order_dicts.append(order_dict)
                except Exception as e:
                    logger.warning(f"Error processing activity {activity.get('id')}: {e}")
                    continue

            # Assign trade_ids
            trade_id_map = self._assign_trade_id(order_dicts)

            # Persist to database
            synced_orders = await self._persist_orders(order_dicts, trade_id_map)

            logger.success(f"Synced {len(synced_orders)} orders from activities to database")
            return synced_orders

        except Exception as e:
            logger.error(f"Failed to sync orders from activities: {e}")
            raise

    def _assign_trade_id(self, orders: List[dict]) -> Dict[str, dict]:
        """
        Assign trade_ids to group related orders.

        Logic:
        1. Group by underlying symbol + expiry date
        2. Within each group, cluster by time window (5 minutes)
        3. Detect strategy type for each cluster
        4. Assign same trade_id to all orders in cluster

        Args:
            orders: List of order dicts from Alpaca

        Returns:
            Mapping of alpaca_order_id -> {trade_id, strategy_type, leg_number}
        """
        if not orders:
            return {}

        # Group by underlying + expiry
        groups: Dict[tuple, list] = defaultdict(list)
        for order in orders:
            key = (order.get('underlying'), order.get('expiry_date'))
            groups[key].append(order)

        trade_id_map = {}

        for key, group_orders in groups.items():
            # Sort by submitted_at
            group_orders.sort(key=lambda x: x.get('submitted_at') or datetime.min)

            # Find clusters within time window
            clusters = []
            current_cluster = [group_orders[0]]

            for order in group_orders[1:]:
                prev_time = current_cluster[-1].get('submitted_at')
                curr_time = order.get('submitted_at')

                # Handle None timestamps
                if prev_time is None or curr_time is None:
                    current_cluster.append(order)
                    continue

                if curr_time - prev_time <= TRADE_GROUPING_TIME_WINDOW:
                    current_cluster.append(order)
                else:
                    clusters.append(current_cluster)
                    current_cluster = [order]

            clusters.append(current_cluster)

            # Assign trade_id to each cluster
            for cluster in clusters:
                trade_id = uuid4()
                strategy = self._detect_strategy(cluster)

                for i, order in enumerate(cluster):
                    trade_id_map[order['id']] = {
                        'trade_id': trade_id,
                        'strategy_type': strategy,
                        'leg_number': i + 1
                    }

        return trade_id_map

    def _detect_strategy(self, orders: List[dict]) -> str:
        """
        Detect strategy type from order leg patterns.

        Uses same logic as IronCondorPosition.detect_strategy().

        Args:
            orders: List of orders in a potential trade group

        Returns:
            Strategy type string
        """
        if len(orders) == 0:
            return 'options'

        if len(orders) == 1:
            return 'single_leg'

        # Count calls and puts, long and short
        calls = []
        puts = []

        for order in orders:
            option_type = order.get('option_type', '').lower()
            side = order.get('side', '').lower()
            strike = order.get('strike_price')

            if option_type == 'call':
                calls.append({'side': side, 'strike': strike})
            elif option_type == 'put':
                puts.append({'side': side, 'strike': strike})

        # Check for Iron Butterfly (4 legs: 2 calls + 2 puts, short strikes equal)
        if len(orders) == 4 and len(calls) == 2 and len(puts) == 2:
            short_call = next((c for c in calls if c['side'] == 'sell'), None)
            short_put = next((p for p in puts if p['side'] == 'sell'), None)

            if short_call and short_put:
                if short_call['strike'] == short_put['strike']:
                    return 'iron_butterfly'
                else:
                    # Different short strikes = Iron Condor
                    call_sides = set(c['side'] for c in calls)
                    put_sides = set(p['side'] for p in puts)
                    if call_sides == {'buy', 'sell'} and put_sides == {'buy', 'sell'}:
                        return 'iron_condor'

        # Check for 2-leg strategies
        if len(orders) == 2:
            opt_types = [o.get('option_type', '').lower() for o in orders]
            strikes = [o.get('strike_price') for o in orders]

            # Same option type = Vertical Spread
            if opt_types[0] == opt_types[1]:
                return 'vertical_spread'

            # Different types, same strike = Straddle
            if strikes[0] == strikes[1]:
                return 'straddle'

            # Different types, different strikes = Strangle
            return 'strangle'

        # Default for other patterns
        return 'options'

    async def _persist_orders(
        self,
        orders: List[dict],
        trade_id_map: Dict[str, dict]
    ) -> List[AlpacaOrder]:
        """
        Persist orders to database.

        Args:
            orders: List of order dicts
            trade_id_map: Mapping of order ID to trade info

        Returns:
            List of persisted AlpacaOrder records
        """
        pool = await self._get_pool()
        persisted = []

        async with pool.acquire() as conn:
            for order in orders:
                try:
                    alpaca_order_id = order['id']
                    trade_info = trade_id_map.get(alpaca_order_id, {})
                    trade_id = trade_info.get('trade_id', uuid4())
                    strategy_type = trade_info.get('strategy_type', 'options')
                    leg_number = trade_info.get('leg_number')

                    # Upsert order (update if exists, insert if not)
                    row = await conn.fetchrow("""
                        INSERT INTO alpaca_orders (
                            alpaca_order_id, client_order_id,
                            trade_id, strategy_type, leg_number,
                            symbol, underlying, side, qty, filled_qty,
                            order_type, time_in_force,
                            limit_price, stop_price, filled_avg_price,
                            status, expiry_date, strike_price, option_type,
                            submitted_at, filled_at, expired_at, canceled_at,
                            raw_data
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                            $11, $12, $13, $14, $15, $16, $17, $18, $19,
                            $20, $21, $22, $23, $24
                        )
                        ON CONFLICT (alpaca_order_id)
                        DO UPDATE SET
                            filled_qty = EXCLUDED.filled_qty,
                            filled_avg_price = EXCLUDED.filled_avg_price,
                            status = EXCLUDED.status,
                            filled_at = EXCLUDED.filled_at,
                            expired_at = EXCLUDED.expired_at,
                            canceled_at = EXCLUDED.canceled_at,
                            raw_data = EXCLUDED.raw_data,
                            updated_at = NOW()
                        RETURNING *
                    """,
                        alpaca_order_id,
                        order.get('client_order_id'),
                        trade_id,
                        strategy_type,
                        leg_number,
                        order.get('symbol'),
                        order.get('underlying'),
                        order.get('side'),
                        order.get('qty'),
                        order.get('filled_qty'),
                        order.get('order_type'),
                        order.get('time_in_force'),
                        order.get('limit_price'),
                        order.get('stop_price'),
                        order.get('filled_avg_price'),
                        order.get('status'),
                        order.get('expiry_date'),
                        order.get('strike_price'),
                        order.get('option_type'),
                        order.get('submitted_at'),
                        order.get('filled_at'),
                        order.get('expired_at'),
                        order.get('canceled_at'),
                        json.dumps(order.get('raw_data', {}))
                    )

                    if row:
                        persisted.append(AlpacaOrder(**dict(row)))

                except Exception as e:
                    logger.warning(f"Failed to persist order {order.get('id')}: {e}")
                    continue

        return persisted

    # ═══════════════════════════════════════════════════════════
    # POSITION SYNCING
    # ═══════════════════════════════════════════════════════════

    async def sync_positions(self) -> List[AlpacaPosition]:
        """
        Fetch and sync open positions from Alpaca.

        Returns:
            List of synced AlpacaPosition records
        """
        if not self._alpaca_service.is_configured:
            logger.warning("AlpacaSyncService: Alpaca not configured - skipping position sync")
            return []

        try:
            # Use existing position fetching from AlpacaService
            positions = await self._alpaca_service.get_all_positions()

            if not positions:
                logger.info("No positions to sync")
                return []

            # Convert to position records and persist
            synced_positions = await self._persist_positions(positions)

            logger.success(f"Synced {len(synced_positions)} positions to database")
            return synced_positions

        except Exception as e:
            logger.error(f"Failed to sync positions: {e}")
            raise

    async def _persist_positions(self, positions: List[Any]) -> List[AlpacaPosition]:
        """
        Persist positions to database.

        Args:
            positions: List of IronCondorPosition objects from AlpacaService

        Returns:
            List of persisted AlpacaPosition records
        """
        pool = await self._get_pool()
        persisted = []

        async with pool.acquire() as conn:
            # Mark all existing positions as potentially closed
            await conn.execute("""
                UPDATE alpaca_positions SET is_open = FALSE WHERE is_open = TRUE
            """)

            for position in positions:
                for leg in position.legs:
                    try:
                        # Determine side from direction
                        side = 'short' if leg.direction == 'Short' else 'long'

                        # Try to find matching trade_id from orders
                        trade_id = await conn.fetchval("""
                            SELECT trade_id FROM alpaca_orders
                            WHERE symbol = $1 AND underlying = $2
                            ORDER BY created_at DESC LIMIT 1
                        """, leg.symbol, leg.underlying)

                        # Upsert position
                        row = await conn.fetchrow("""
                            INSERT INTO alpaca_positions (
                                trade_id, symbol, underlying, qty, side,
                                avg_entry_price, current_price, market_value, cost_basis,
                                unrealized_pl, unrealized_plpc,
                                expiry_date, strike_price, option_type,
                                is_open, raw_data
                            ) VALUES (
                                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
                            )
                            ON CONFLICT (symbol, is_open)
                            DO UPDATE SET
                                trade_id = COALESCE(EXCLUDED.trade_id, alpaca_positions.trade_id),
                                qty = EXCLUDED.qty,
                                current_price = EXCLUDED.current_price,
                                market_value = EXCLUDED.market_value,
                                unrealized_pl = EXCLUDED.unrealized_pl,
                                unrealized_plpc = EXCLUDED.unrealized_plpc,
                                is_open = TRUE,
                                updated_at = NOW()
                            RETURNING *
                        """,
                            trade_id,
                            leg.symbol,
                            leg.underlying,
                            leg.quantity * (-1 if side == 'short' else 1),
                            side,
                            leg.entry_price,
                            leg.current_price,
                            leg.current_price * leg.quantity * 100,  # market value
                            leg.entry_price * leg.quantity * 100,    # cost basis
                            leg.pnl_dollars,
                            leg.pnl_percent,
                            leg.expiry_date,
                            leg.strike,
                            leg.option_type.lower() if leg.option_type else None,
                            True,
                            json.dumps({
                                'position_id': str(position.id),
                                'strategy': position.strategy,
                                'ticker': position.ticker
                            })
                        )

                        if row:
                            persisted.append(AlpacaPosition(**dict(row)))

                    except Exception as e:
                        logger.warning(f"Failed to persist position leg {leg.symbol}: {e}")
                        continue

        return persisted

    # ═══════════════════════════════════════════════════════════
    # QUERY METHODS
    # ═══════════════════════════════════════════════════════════

    async def get_orders_by_trade_id(self, trade_id: UUID) -> List[AlpacaOrder]:
        """
        Get all orders for a trade group.

        Args:
            trade_id: UUID of the trade group

        Returns:
            List of AlpacaOrder records
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM alpaca_orders
                WHERE trade_id = $1
                ORDER BY leg_number, submitted_at
            """, trade_id)

            return [AlpacaOrder(**dict(row)) for row in rows]

    async def get_orders(
        self,
        underlying: Optional[str] = None,
        status: Optional[str] = None,
        strategy_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AlpacaOrder]:
        """
        Query orders with filters.

        Args:
            underlying: Filter by underlying symbol
            status: Filter by order status
            strategy_type: Filter by strategy type
            limit: Maximum records to return
            offset: Offset for pagination

        Returns:
            List of AlpacaOrder records
        """
        pool = await self._get_pool()

        # Build query with filters
        conditions = []
        params = []
        param_idx = 1

        if underlying:
            conditions.append(f"underlying = ${param_idx}")
            params.append(underlying)
            param_idx += 1

        if status:
            conditions.append(f"status = ${param_idx}")
            params.append(status)
            param_idx += 1

        if strategy_type:
            conditions.append(f"strategy_type = ${param_idx}")
            params.append(strategy_type)
            param_idx += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        # Add limit and offset with correct parameter indices
        limit_idx = param_idx
        offset_idx = param_idx + 1
        params.extend([limit, offset])

        async with pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT * FROM alpaca_orders
                WHERE {where_clause}
                ORDER BY submitted_at DESC
                LIMIT ${limit_idx} OFFSET ${offset_idx}
            """, *params)

            return [AlpacaOrder(**dict(row)) for row in rows]

    async def get_open_positions(self) -> List[AlpacaPosition]:
        """
        Get all open positions from database.

        Returns:
            List of open AlpacaPosition records
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM alpaca_positions
                WHERE is_open = TRUE
                ORDER BY underlying, expiry_date
            """)

            return [AlpacaPosition(**dict(row)) for row in rows]

    # ═══════════════════════════════════════════════════════════
    # TRADE AGGREGATION METHODS
    # ═══════════════════════════════════════════════════════════

    async def get_trades(
        self,
        underlying: Optional[str] = None,
        status: Optional[str] = None,  # open, closed, all
        limit: int = 100,
        offset: int = 0
    ) -> List[dict]:
        """
        Get aggregated trades (orders grouped by trade_id).

        Logic:
        1. Query orders grouped by trade_id
        2. Aggregate P&L across all legs
        3. Determine overall trade status
        4. Calculate direction (net position)

        Args:
            underlying: Filter by underlying symbol
            status: Filter by trade status (open, closed, all)
            limit: Maximum number of trades to return
            offset: Offset for pagination

        Returns:
            List of trade dictionaries
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # Query with aggregation - using COALESCE for NULL safety
            query = """
                SELECT
                    trade_id,
                    underlying,
                    strategy_type,
                    MIN(submitted_at) as entry_date,
                    MAX(COALESCE(filled_at, canceled_at, expired_at)) as exit_date,
                    COALESCE(SUM(CASE WHEN side = 'sell' THEN COALESCE(filled_avg_price, 0) * COALESCE(filled_qty, 0) * 100
                             ELSE -COALESCE(filled_avg_price, 0) * COALESCE(filled_qty, 0) * 100 END), 0) as total_premium,
                    COALESCE(SUM(CASE WHEN side = 'buy' THEN COALESCE(filled_avg_price, 0) * COALESCE(filled_qty, 0) * 100
                             ELSE 0 END), 0) as total_cost,
                    COALESCE(MAX(filled_qty), 0) as quantity,
                    COUNT(*) as leg_count,
                    array_agg(DISTINCT status) as statuses
                FROM alpaca_orders
                WHERE ($1::TEXT IS NULL OR underlying = $1)
                GROUP BY trade_id, underlying, strategy_type
                ORDER BY entry_date DESC
                LIMIT $2 OFFSET $3
            """
            rows = await conn.fetch(query, underlying, limit, offset)

            trades = []
            for row in rows:
                # Determine status from order statuses
                statuses = set(row['statuses']) if row['statuses'] else set()
                if 'filled' in statuses and len(statuses) == 1:
                    trade_status = 'closed'
                elif 'expired' in statuses:
                    trade_status = 'expired'
                elif statuses & {'new', 'accepted', 'partially_filled'}:
                    trade_status = 'open'
                else:
                    trade_status = 'closed'

                # Filter by status if requested
                if status and status != 'all' and trade_status != status:
                    continue

                # Calculate P&L with proper weighted average approach
                # total_premium = credit received from selling options
                # total_cost = cost of buying options (for spreads/hedges)
                total_premium = float(row['total_premium']) if row['total_premium'] is not None else 0.0
                total_cost = float(row['total_cost']) if row['total_cost'] is not None else 0.0
                quantity = int(row['quantity']) if row['quantity'] is not None else 0

                # Net credit/debit = what we received - what we paid
                # Positive = net credit (we received money), Negative = net debit (we paid money)
                net_premium = total_premium  # Already accounts for buy/sell via CASE statement

                # For closed trades, calculate realized P&L
                # For open trades, this represents the entry credit/debit
                pnl_dollars = net_premium

                # Calculate P&L percent based on max risk or capital at risk
                # For credit spreads: max risk is width of spread - credit received
                # Simplified: use absolute premium as cost basis for percentage
                cost_basis = abs(total_cost) if total_cost != 0 else abs(total_premium)
                pnl_percent = 0.0
                if cost_basis > 0:
                    pnl_percent = (pnl_dollars / cost_basis) * 100
                elif net_premium != 0:
                    # If no cost basis, use sign of premium (100% for full credit, -100% for full loss)
                    pnl_percent = 100.0 if net_premium > 0 else -100.0

                # Entry price = weighted average entry price per contract
                entry_price = (net_premium / quantity) if quantity > 0 else net_premium

                trades.append({
                    'trade_id': str(row['trade_id']),
                    'ticker': row['underlying'] or 'UNKNOWN',
                    'strategy': row['strategy_type'] or 'options',
                    'direction': 'Short' if net_premium > 0 else 'Long',  # Net credit = short, net debit = long
                    'entry_date': row['entry_date'].isoformat() if row['entry_date'] else None,
                    'exit_date': row['exit_date'].isoformat() if row['exit_date'] else None,
                    'entry_price': entry_price,
                    'exit_price': None,  # Would need position matching for accurate exit
                    'quantity': quantity,
                    'pnl': pnl_dollars,
                    'pnl_percent': round(pnl_percent, 2),
                    'status': trade_status,
                    'leg_count': int(row['leg_count']) if row['leg_count'] is not None else 0,
                })

            return trades

    async def get_detailed_trades(
        self,
        underlying: Optional[str] = None,
        status: Optional[str] = None,  # open, closed, partial, all
        limit: int = 50,
        offset: int = 0
    ) -> List[dict]:
        """
        Get trades with full leg-level detail and open/close matching.

        For each trade:
        1. Fetch all orders grouped by trade_id
        2. Group orders by leg (symbol)
        3. Match opening order with closing order per leg
        4. Calculate per-leg P&L
        5. Aggregate into summary

        Returns:
            List of DetailedTrade dictionaries
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # Step 1: Get all trade_ids with basic info
            trade_query = """
                SELECT DISTINCT
                    trade_id,
                    underlying,
                    strategy_type,
                    MIN(expiry_date) as expiry_date,
                    MIN(submitted_at) as entry_date
                FROM alpaca_orders
                WHERE ($1::TEXT IS NULL OR underlying = $1)
                GROUP BY trade_id, underlying, strategy_type
                ORDER BY entry_date DESC
                LIMIT $2 OFFSET $3
            """
            trade_rows = await conn.fetch(trade_query, underlying, limit, offset)

            if not trade_rows:
                return []

            detailed_trades = []

            for trade_row in trade_rows:
                trade_id = trade_row['trade_id']

                # Step 2: Fetch all orders for this trade
                orders_query = """
                    SELECT
                        alpaca_order_id, symbol, underlying, side,
                        qty, filled_qty, filled_avg_price, status,
                        option_type, strike_price, expiry_date,
                        leg_number, submitted_at, filled_at
                    FROM alpaca_orders
                    WHERE trade_id = $1
                    ORDER BY leg_number, submitted_at
                """
                orders = await conn.fetch(orders_query, trade_id)

                # Step 3: Group orders by symbol (leg)
                legs_by_symbol: Dict[str, List[dict]] = defaultdict(list)
                for order in orders:
                    legs_by_symbol[order['symbol']].append(dict(order))

                # Step 4: Build leg details with open/close matching
                leg_details = []
                opening_credit = 0.0  # Net premium from opening legs (SELL - BUY)
                closing_debit = 0.0   # Net premium for closing legs (BUY - SELL)
                closed_legs = 0

                for leg_num, (symbol, leg_orders) in enumerate(legs_by_symbol.items(), 1):
                    # Sort by time to identify open vs close
                    leg_orders.sort(key=lambda x: x['submitted_at'] or datetime.min)

                    # First order is the opening order
                    open_order = leg_orders[0]
                    close_order = leg_orders[1] if len(leg_orders) > 1 else None

                    # Determine open action
                    open_action = 'SELL' if open_order['side'] == 'sell' else 'BUY'
                    open_fill = float(open_order['filled_avg_price'] or 0)

                    # Determine close action (opposite of open)
                    close_action = None
                    close_fill = None
                    close_date = None
                    is_closed = False

                    if close_order:
                        close_action = 'BUY' if close_order['side'] == 'buy' else 'SELL'
                        close_fill = float(close_order['filled_avg_price'] or 0)
                        close_date = close_order['filled_at'].isoformat() if close_order['filled_at'] else None
                        is_closed = True
                        closed_legs += 1

                    # Calculate P&L per leg
                    quantity = int(open_order['filled_qty'] or open_order['qty'] or 1)

                    # Track opening credit/debit
                    if open_action == 'SELL':
                        # Sold to open: adds to opening credit
                        opening_credit += open_fill * quantity * 100
                    else:  # BUY to open
                        # Bought to open: reduces net opening credit
                        opening_credit -= open_fill * quantity * 100

                    # Track closing debit/credit
                    if is_closed:
                        if close_action == 'BUY':
                            # Bought to close: adds to closing debit
                            closing_debit += close_fill * quantity * 100
                        else:  # SELL to close
                            # Sold to close: reduces net closing debit
                            closing_debit -= close_fill * quantity * 100

                    # Calculate per-leg P&L
                    if open_action == 'SELL':
                        if is_closed:
                            pnl_per_contract = open_fill - close_fill
                        else:
                            pnl_per_contract = open_fill  # Unrealized
                    else:
                        if is_closed:
                            pnl_per_contract = close_fill - open_fill
                        else:
                            pnl_per_contract = -open_fill  # Unrealized (cost)

                    pnl_total = pnl_per_contract * quantity * 100

                    # Build description (e.g., "423 Call")
                    strike = open_order['strike_price']
                    opt_type = (open_order['option_type'] or 'option').capitalize()
                    description = f"{int(strike)} {opt_type}" if strike else symbol

                    leg_details.append({
                        'leg_number': leg_num,
                        'description': description,
                        'symbol': symbol,
                        'strike': float(strike) if strike else 0,
                        'option_type': (open_order['option_type'] or 'call').lower(),
                        'open_action': open_action,
                        'open_fill': open_fill,
                        'open_date': open_order['submitted_at'].isoformat() if open_order['submitted_at'] else None,
                        'close_action': close_action,
                        'close_fill': close_fill,
                        'close_date': close_date,
                        'quantity': quantity,
                        'pnl_per_contract': round(pnl_per_contract, 4),
                        'pnl_total': round(pnl_total, 2),
                        'is_closed': is_closed
                    })

                # Step 5: Build summary
                net_pnl_total = opening_credit - closing_debit
                # All legs in a strategy should have equal quantities, use first leg's quantity
                quantity = leg_details[0]['quantity'] if leg_details else 1
                net_pnl_per_contract = net_pnl_total / (quantity * 100) if quantity else 0

                # Determine trade status
                open_legs = len(leg_details) - closed_legs
                if closed_legs == 0:
                    trade_status = 'open'
                elif open_legs == 0:
                    trade_status = 'closed'
                else:
                    trade_status = 'partial'

                # Filter by status if requested
                if status and status != 'all' and trade_status != status:
                    continue

                # Determine direction (net credit = Short, net debit = Long)
                direction = 'Short' if opening_credit > 0 else 'Long'

                # Find exit date (latest close date)
                exit_dates = [leg['close_date'] for leg in leg_details if leg['close_date']]
                exit_date = max(exit_dates) if exit_dates else None

                detailed_trades.append({
                    'trade_id': str(trade_id),
                    'ticker': trade_row['underlying'] or 'UNKNOWN',
                    'strategy': trade_row['strategy_type'] or 'options',
                    'direction': direction,
                    'status': trade_status,
                    'entry_date': trade_row['entry_date'].isoformat() if trade_row['entry_date'] else None,
                    'exit_date': exit_date,
                    'expiry_date': trade_row['expiry_date'].isoformat() if trade_row['expiry_date'] else None,
                    'legs': leg_details,
                    'summary': {
                        'opening_credit': round(opening_credit, 2),
                        'closing_debit': round(closing_debit, 2),
                        'net_pnl_per_contract': round(net_pnl_per_contract, 4),
                        'net_pnl_total': round(net_pnl_total, 2),
                        'leg_count': len(leg_details),
                        'closed_legs': closed_legs,
                        'open_legs': open_legs
                    }
                })

            return detailed_trades

    async def get_trade_stats(self, status: Optional[str] = None) -> dict:
        """
        Get aggregated trade statistics.

        Args:
            status: Filter by trade status (open, closed, all)

        Returns:
            Dictionary with trade statistics
        """
        trades = await self.get_trades(status=status, limit=1000)

        total_pnl = sum(t['pnl'] for t in trades)
        winning = [t for t in trades if t['pnl'] > 0]
        losing = [t for t in trades if t['pnl'] < 0]
        open_trades = [t for t in trades if t['status'] == 'open']
        closed_trades = [t for t in trades if t['status'] in ('closed', 'expired')]

        return {
            'total_pnl': total_pnl,
            'win_rate': (len(winning) / len(trades) * 100) if trades else 0,
            'total_trades': len(trades),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'open_trades': len(open_trades),
            'closed_trades': len(closed_trades),
        }


# ═══════════════════════════════════════════════════════════
# APP.STATE INITIALIZATION
# ═══════════════════════════════════════════════════════════

async def init_alpaca_sync_service(
    app: "FastAPI",
    alpaca_service: AlpacaService
) -> AlpacaSyncService:
    """
    Initialize AlpacaSyncService and store in app.state.

    IMPORTANT: Call this in FastAPI lifespan startup after AlpacaService.

    Args:
        app: FastAPI application instance
        alpaca_service: Initialized AlpacaService

    Returns:
        Initialized AlpacaSyncService
    """
    service = AlpacaSyncService(alpaca_service)
    app.state.alpaca_sync_service = service

    if alpaca_service.is_configured:
        logger.success("AlpacaSyncService initialized and ready")
    else:
        logger.warning("AlpacaSyncService: Alpaca not configured - sync disabled")

    return service


def get_alpaca_sync_service(app: "FastAPI") -> AlpacaSyncService:
    """
    Get AlpacaSyncService from app.state.

    Args:
        app: FastAPI application instance

    Returns:
        AlpacaSyncService instance

    Raises:
        RuntimeError: If service not initialized
    """
    if not hasattr(app.state, 'alpaca_sync_service'):
        raise RuntimeError("AlpacaSyncService not initialized. Call init_alpaca_sync_service() in lifespan.")
    return app.state.alpaca_sync_service
