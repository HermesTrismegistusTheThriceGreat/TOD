"""
Alpaca Database Models

Pydantic models for Alpaca orders and positions.
Maps to the alpaca_orders and alpaca_positions tables.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class AlpacaOrder(BaseModel):
    """
    Alpaca order history record with trade grouping.

    Maps to: alpaca_orders table
    """
    id: UUID
    alpaca_order_id: str
    client_order_id: Optional[str] = None

    # Trade grouping
    trade_id: UUID
    strategy_type: Optional[Literal['options']] = 'options'
    leg_number: Optional[int] = None

    # Order details
    symbol: str
    underlying: str
    side: Literal['buy', 'sell']
    qty: float
    filled_qty: float = 0.0
    order_type: Optional[Literal['market', 'limit', 'stop', 'stop_limit']] = None
    time_in_force: Optional[Literal['day', 'gtc', 'opg', 'cls', 'ioc', 'fok']] = None

    # Pricing
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    filled_avg_price: Optional[float] = None

    # Status
    status: str

    # Option details
    expiry_date: Optional[date] = None
    strike_price: Optional[float] = None
    option_type: Optional[Literal['call', 'put']] = None

    # Timestamps
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None

    # Metadata
    raw_data: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime
    updated_at: datetime

    @field_validator('id', 'trade_id', mode='before')
    @classmethod
    def convert_uuid(cls, v):
        """Convert asyncpg UUID to Python UUID"""
        if v is None:
            return None
        if isinstance(v, UUID):
            return v
        return UUID(str(v))

    @field_validator('qty', 'filled_qty', 'limit_price', 'stop_price', 'filled_avg_price', 'strike_price', mode='before')
    @classmethod
    def convert_decimal(cls, v):
        """Convert Decimal to float"""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return float(v)
        return v

    @field_validator('raw_data', mode='before')
    @classmethod
    def parse_raw_data(cls, v):
        """Parse JSON string to dict"""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }


class AlpacaPosition(BaseModel):
    """
    Current open position from Alpaca.

    Maps to: alpaca_positions table
    """
    id: UUID
    trade_id: Optional[UUID] = None

    symbol: str
    underlying: str
    qty: float
    side: Optional[Literal['long', 'short']] = None

    # Pricing
    avg_entry_price: Optional[float] = None
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    cost_basis: Optional[float] = None

    # P/L
    unrealized_pl: Optional[float] = None
    unrealized_plpc: Optional[float] = None
    unrealized_intraday_pl: Optional[float] = None
    unrealized_intraday_plpc: Optional[float] = None

    # Option details
    expiry_date: Optional[date] = None
    strike_price: Optional[float] = None
    option_type: Optional[Literal['call', 'put']] = None

    is_open: bool = True
    raw_data: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime
    updated_at: datetime

    @field_validator('id', 'trade_id', mode='before')
    @classmethod
    def convert_uuid(cls, v):
        """Convert asyncpg UUID to Python UUID"""
        if v is None:
            return None
        if isinstance(v, UUID):
            return v
        return UUID(str(v))

    @field_validator('qty', 'avg_entry_price', 'current_price', 'market_value', 'cost_basis',
                     'unrealized_pl', 'unrealized_plpc', 'unrealized_intraday_pl',
                     'unrealized_intraday_plpc', 'strike_price', mode='before')
    @classmethod
    def convert_decimal(cls, v):
        """Convert Decimal to float"""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return float(v)
        return v

    @field_validator('raw_data', mode='before')
    @classmethod
    def parse_raw_data(cls, v):
        """Parse JSON string to dict"""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }
