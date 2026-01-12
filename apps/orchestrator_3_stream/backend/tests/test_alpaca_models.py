#!/usr/bin/env python3
"""
Unit tests for Alpaca Pydantic models.

Run with: cd apps/orchestrator_3_stream/backend && uv run pytest tests/test_alpaca_models.py -v
"""

import pytest
from datetime import date, datetime
from uuid import UUID

# Import models
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.alpaca_models import (
    OCCSymbol,
    OptionLeg,
    IronCondorPosition,
    OptionPriceUpdate,
    GetPositionsResponse,
)


class TestOCCSymbolParser:
    """Tests for OCCSymbol.parse()"""

    def test_parse_spy_call(self):
        """Parse SPY call option"""
        result = OCCSymbol.parse("SPY260117C00688000")

        assert result.underlying == "SPY"
        assert result.expiry_date == date(2026, 1, 17)
        assert result.option_type == "Call"
        assert result.strike_price == 688.0

    def test_parse_spy_put(self):
        """Parse SPY put option"""
        result = OCCSymbol.parse("SPY260117P00683000")

        assert result.underlying == "SPY"
        assert result.expiry_date == date(2026, 1, 17)
        assert result.option_type == "Put"
        assert result.strike_price == 683.0

    def test_parse_fractional_strike(self):
        """Parse option with fractional strike"""
        result = OCCSymbol.parse("AAPL250321C00142500")

        assert result.underlying == "AAPL"
        assert result.strike_price == 142.5

    def test_parse_single_char_underlying(self):
        """Parse option with single character underlying"""
        result = OCCSymbol.parse("F251219C00015000")

        assert result.underlying == "F"
        assert result.strike_price == 15.0

    def test_parse_six_char_underlying(self):
        """Parse option with 6 character underlying"""
        result = OCCSymbol.parse("GOOGLL251219C01500000")

        assert result.underlying == "GOOGLL"
        assert result.strike_price == 1500.0

    def test_invalid_format_raises(self):
        """Invalid format raises ValueError"""
        with pytest.raises(ValueError):
            OCCSymbol.parse("INVALID")

    def test_lowercase_normalized(self):
        """Lowercase input is normalized to uppercase"""
        result = OCCSymbol.parse("spy260117c00688000")

        assert result.underlying == "SPY"
        assert result.option_type == "Call"
        assert result.raw_symbol == "SPY260117C00688000"

    def test_empty_string_raises(self):
        """Empty string raises ValueError"""
        with pytest.raises(ValueError):
            OCCSymbol.parse("")


class TestOptionLegPnL:
    """Tests for OptionLeg P/L calculations"""

    def test_short_call_profit(self):
        """Short call with price decrease = profit"""
        leg = OptionLeg(
            symbol="SPY260117C00688000",
            direction="Short",
            strike=688.0,
            option_type="Call",
            quantity=10,
            entry_price=4.00,
            current_price=3.00,
            expiry_date=date(2026, 1, 17),
            underlying="SPY"
        )

        # Short: entry > current = profit
        # P/L = (entry - current) * qty * 100
        # = (4.00 - 3.00) * 10 * 100 = $1000
        assert leg.pnl_dollars == 1000.0

    def test_short_call_loss(self):
        """Short call with price increase = loss"""
        leg = OptionLeg(
            symbol="SPY260117C00688000",
            direction="Short",
            strike=688.0,
            option_type="Call",
            quantity=10,
            entry_price=3.00,
            current_price=4.00,
            expiry_date=date(2026, 1, 17),
            underlying="SPY"
        )

        # Short: entry < current = loss
        # P/L = (3.00 - 4.00) * 10 * 100 = -$1000
        assert leg.pnl_dollars == -1000.0

    def test_long_put_profit(self):
        """Long put with price increase = profit"""
        leg = OptionLeg(
            symbol="SPY260117P00683000",
            direction="Long",
            strike=683.0,
            option_type="Put",
            quantity=10,
            entry_price=1.00,
            current_price=2.00,
            expiry_date=date(2026, 1, 17),
            underlying="SPY"
        )

        # Long: current > entry = profit
        # P/L = (current - entry) * qty * 100
        # = (2.00 - 1.00) * 10 * 100 = $1000
        assert leg.pnl_dollars == 1000.0

    def test_long_put_loss(self):
        """Long put with price decrease = loss"""
        leg = OptionLeg(
            symbol="SPY260117P00683000",
            direction="Long",
            strike=683.0,
            option_type="Put",
            quantity=10,
            entry_price=2.00,
            current_price=1.00,
            expiry_date=date(2026, 1, 17),
            underlying="SPY"
        )

        # Long: current < entry = loss
        # P/L = (1.00 - 2.00) * 10 * 100 = -$1000
        assert leg.pnl_dollars == -1000.0

    def test_zero_entry_price_pnl_percent(self):
        """Zero entry price returns 0% P/L"""
        leg = OptionLeg(
            symbol="SPY260117P00683000",
            direction="Long",
            strike=683.0,
            option_type="Put",
            quantity=10,
            entry_price=0.0,
            current_price=1.00,
            expiry_date=date(2026, 1, 17),
            underlying="SPY"
        )

        assert leg.pnl_percent == 0.0


class TestIronCondorPosition:
    """Tests for IronCondorPosition validation"""

    def create_valid_iron_condor(self) -> IronCondorPosition:
        """Helper to create a valid iron condor"""
        return IronCondorPosition(
            ticker="SPY",
            expiry_date=date(2026, 1, 17),
            legs=[
                OptionLeg(symbol="SPY260117P00680000", direction="Long", strike=680.0, option_type="Put", quantity=10, entry_price=1.00, expiry_date=date(2026, 1, 17), underlying="SPY"),
                OptionLeg(symbol="SPY260117P00685000", direction="Short", strike=685.0, option_type="Put", quantity=10, entry_price=2.00, expiry_date=date(2026, 1, 17), underlying="SPY"),
                OptionLeg(symbol="SPY260117C00695000", direction="Short", strike=695.0, option_type="Call", quantity=10, entry_price=2.00, expiry_date=date(2026, 1, 17), underlying="SPY"),
                OptionLeg(symbol="SPY260117C00700000", direction="Long", strike=700.0, option_type="Call", quantity=10, entry_price=1.00, expiry_date=date(2026, 1, 17), underlying="SPY"),
            ]
        )

    def test_valid_iron_condor(self):
        """Valid iron condor passes validation"""
        ic = self.create_valid_iron_condor()
        assert ic.is_valid_iron_condor() is True

    def test_invalid_fewer_than_4_legs(self):
        """Iron condor with fewer than 4 legs fails validation"""
        ic = IronCondorPosition(
            ticker="SPY",
            expiry_date=date(2026, 1, 17),
            legs=[
                OptionLeg(symbol="SPY260117P00680000", direction="Long", strike=680.0, option_type="Put", quantity=10, entry_price=1.00, expiry_date=date(2026, 1, 17), underlying="SPY"),
                OptionLeg(symbol="SPY260117P00685000", direction="Short", strike=685.0, option_type="Put", quantity=10, entry_price=2.00, expiry_date=date(2026, 1, 17), underlying="SPY"),
            ]
        )
        assert ic.is_valid_iron_condor() is False

    def test_total_pnl_calculation(self):
        """Total P/L sums all leg P/Ls"""
        ic = self.create_valid_iron_condor()

        # Set current prices to trigger P/L
        ic.legs[0].current_price = 0.50  # Long put: loss of $500
        ic.legs[1].current_price = 1.50  # Short put: profit of $500
        ic.legs[2].current_price = 1.50  # Short call: profit of $500
        ic.legs[3].current_price = 0.50  # Long call: loss of $500

        # Total should be $0 (balanced)
        assert ic.total_pnl == 0.0

    def test_get_leg_by_type(self):
        """get_leg_by_type returns correct leg"""
        ic = self.create_valid_iron_condor()

        short_put = ic.get_leg_by_type('Put', 'Short')
        assert short_put is not None
        assert short_put.strike == 685.0

        long_call = ic.get_leg_by_type('Call', 'Long')
        assert long_call is not None
        assert long_call.strike == 700.0

    def test_days_to_expiry(self):
        """days_to_expiry calculates correctly"""
        from datetime import timedelta

        # Create IC expiring in 10 days
        future_date = date.today() + timedelta(days=10)
        ic = IronCondorPosition(
            ticker="SPY",
            expiry_date=future_date,
            legs=[]
        )

        assert ic.days_to_expiry == 10

    def test_default_strategy_is_options(self):
        """Default strategy should be 'Options'"""
        ic = IronCondorPosition(
            ticker="SPY",
            expiry_date=date(2026, 1, 17),
            legs=[]
        )
        assert ic.strategy == "Options"


class TestDetectStrategy:
    """Tests for IronCondorPosition.detect_strategy()"""

    def create_option_leg(self, symbol: str, direction: str, strike: float,
                          option_type: str) -> OptionLeg:
        """Helper to create an option leg"""
        return OptionLeg(
            symbol=symbol,
            direction=direction,
            strike=strike,
            option_type=option_type,
            quantity=10,
            entry_price=1.00,
            expiry_date=date(2026, 1, 17),
            underlying="SPY"
        )

    def test_detect_strategy_iron_condor(self):
        """Detects iron condor strategy with valid 4-leg structure"""
        ic = IronCondorPosition(
            ticker="SPY",
            expiry_date=date(2026, 1, 17),
            legs=[
                self.create_option_leg("SPY260117P00680000", "Long", 680.0, "Put"),
                self.create_option_leg("SPY260117P00685000", "Short", 685.0, "Put"),
                self.create_option_leg("SPY260117C00695000", "Short", 695.0, "Call"),
                self.create_option_leg("SPY260117C00700000", "Long", 700.0, "Call"),
            ]
        )
        assert ic.detect_strategy() == "Iron Condor"

    def test_detect_strategy_vertical_spread_calls(self):
        """Detects vertical spread with 2 calls"""
        pos = IronCondorPosition(
            ticker="SPY",
            expiry_date=date(2026, 1, 17),
            legs=[
                self.create_option_leg("SPY260117C00695000", "Short", 695.0, "Call"),
                self.create_option_leg("SPY260117C00700000", "Long", 700.0, "Call"),
            ]
        )
        assert pos.detect_strategy() == "Vertical Spread"

    def test_detect_strategy_vertical_spread_puts(self):
        """Detects vertical spread with 2 puts"""
        pos = IronCondorPosition(
            ticker="SPY",
            expiry_date=date(2026, 1, 17),
            legs=[
                self.create_option_leg("SPY260117P00680000", "Long", 680.0, "Put"),
                self.create_option_leg("SPY260117P00685000", "Short", 685.0, "Put"),
            ]
        )
        assert pos.detect_strategy() == "Vertical Spread"

    def test_detect_strategy_straddle(self):
        """Detects straddle with same strike, different types"""
        pos = IronCondorPosition(
            ticker="SPY",
            expiry_date=date(2026, 1, 17),
            legs=[
                self.create_option_leg("SPY260117C00690000", "Short", 690.0, "Call"),
                self.create_option_leg("SPY260117P00690000", "Short", 690.0, "Put"),
            ]
        )
        assert pos.detect_strategy() == "Straddle"

    def test_detect_strategy_strangle(self):
        """Detects strangle with different strikes, different types"""
        pos = IronCondorPosition(
            ticker="SPY",
            expiry_date=date(2026, 1, 17),
            legs=[
                self.create_option_leg("SPY260117C00700000", "Short", 700.0, "Call"),
                self.create_option_leg("SPY260117P00680000", "Short", 680.0, "Put"),
            ]
        )
        assert pos.detect_strategy() == "Strangle"

    def test_detect_strategy_single_leg(self):
        """Single leg returns 'Options'"""
        pos = IronCondorPosition(
            ticker="SPY",
            expiry_date=date(2026, 1, 17),
            legs=[
                self.create_option_leg("SPY260117C00695000", "Long", 695.0, "Call"),
            ]
        )
        assert pos.detect_strategy() == "Options"

    def test_detect_strategy_three_legs(self):
        """Three legs returns 'Options'"""
        pos = IronCondorPosition(
            ticker="SPY",
            expiry_date=date(2026, 1, 17),
            legs=[
                self.create_option_leg("SPY260117P00680000", "Long", 680.0, "Put"),
                self.create_option_leg("SPY260117P00685000", "Short", 685.0, "Put"),
                self.create_option_leg("SPY260117C00695000", "Short", 695.0, "Call"),
            ]
        )
        assert pos.detect_strategy() == "Options"

    def test_detect_strategy_empty_legs(self):
        """Empty legs returns 'Options'"""
        pos = IronCondorPosition(
            ticker="SPY",
            expiry_date=date(2026, 1, 17),
            legs=[]
        )
        assert pos.detect_strategy() == "Options"

    def test_detect_strategy_invalid_4_leg_structure(self):
        """Invalid 4-leg structure (not valid IC) returns 'Options'"""
        # 4 legs but all calls (not valid iron condor)
        pos = IronCondorPosition(
            ticker="SPY",
            expiry_date=date(2026, 1, 17),
            legs=[
                self.create_option_leg("SPY260117C00680000", "Long", 680.0, "Call"),
                self.create_option_leg("SPY260117C00685000", "Short", 685.0, "Call"),
                self.create_option_leg("SPY260117C00695000", "Short", 695.0, "Call"),
                self.create_option_leg("SPY260117C00700000", "Long", 700.0, "Call"),
            ]
        )
        assert pos.detect_strategy() == "Options"


class TestModelSerialization:
    """Tests for JSON serialization"""

    def test_option_leg_to_json(self):
        """OptionLeg serializes to JSON correctly"""
        leg = OptionLeg(
            symbol="SPY260117C00688000",
            direction="Short",
            strike=688.0,
            option_type="Call",
            quantity=10,
            entry_price=4.00,
            current_price=3.00,
            expiry_date=date(2026, 1, 17),
            underlying="SPY"
        )

        json_data = leg.model_dump()

        assert json_data['symbol'] == 'SPY260117C00688000'
        assert json_data['strike'] == 688.0
        assert json_data['pnl_dollars'] == 1000.0
        assert 'expiry_date' in json_data

    def test_price_update_to_json(self):
        """OptionPriceUpdate serializes correctly"""
        update = OptionPriceUpdate(
            symbol="SPY260117C00688000",
            bid_price=3.20,
            ask_price=3.30,
            mid_price=3.25,
        )

        json_data = update.model_dump()

        assert json_data['symbol'] == 'SPY260117C00688000'
        assert json_data['mid_price'] == 3.25
        assert 'timestamp' in json_data

    def test_response_model_serialization(self):
        """API response models serialize correctly"""
        response = GetPositionsResponse(
            status='success',
            positions=[],
            total_count=0
        )

        json_data = response.model_dump()

        assert json_data['status'] == 'success'
        assert json_data['positions'] == []
