#!/usr/bin/env python3
"""
Account Service

Fetches real-time account data from Alpaca API using decrypted credentials.
"""

from typing import Dict, Any
from alpaca.trading.client import TradingClient
from modules.logger import OrchestratorLogger

logger = OrchestratorLogger("account_service")

async def fetch_alpaca_account_data(
    api_key: str,
    secret_key: str,
    account_type: str,  # "paper" or "live" - determines API endpoint
) -> Dict[str, Any]:
    """
    Fetch real-time account data from Alpaca API.

    Args:
        api_key: Alpaca API key (plaintext, already decrypted)
        secret_key: Alpaca secret key (plaintext, already decrypted)
        account_type: "paper" or "live" to select correct endpoint

    Returns:
        Dict with keys: account_type, cash, equity, buying_power, currency, trading_blocked

    Raises:
        Exception: If API call fails
    """
    try:
        # TradingClient uses paper=True for paper-api.alpaca.markets
        client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=account_type == "paper"
        )

        # get_account() is synchronous in alpaca-py
        account = client.get_account()

        logger.info(f"Fetched account data for {account_type} account")

        return {
            "account_type": account_type,
            "cash": str(account.cash),
            "equity": str(account.equity),
            "buying_power": str(account.buying_power),
            "currency": getattr(account, 'currency', None) or "USD",
            "trading_blocked": getattr(account, 'trading_blocked', False) or False,
            "account_blocked": getattr(account, 'account_blocked', False) or False,
            "pattern_day_trader": getattr(account, 'pattern_day_trader', False) or False,
            "daytrade_count": getattr(account, 'daytrade_count', 0) or 0,
        }
    except Exception as e:
        logger.error(f"Failed to fetch account data: {e}")
        raise

__all__ = ["fetch_alpaca_account_data"]
