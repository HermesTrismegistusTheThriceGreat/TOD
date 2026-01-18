# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0", "requests", "numpy", "python-dotenv"]
# ///
"""
Alpaca Data Fetcher for Options Strategy Selector

Fetches options data from Alpaca Elite API (OPRA feed) and converts it to GreekProfile objects.
"""

import logging
import os
import re
from datetime import date, datetime, timedelta
from typing import Optional

import numpy as np
import requests
from dotenv import load_dotenv

# Import models from same directory
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from models import GreekProfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlpacaFetcherError(Exception):
    """Base exception for Alpaca fetcher errors."""

    pass


class AlpacaFetcher:
    """
    Alpaca data fetcher for options greeks and historical volatility.

    Requires Alpaca Elite subscription for OPRA feed access.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: str = "https://data.alpaca.markets",
    ):
        """
        Initialize Alpaca fetcher.

        Args:
            api_key: Alpaca API key (or set ALPACA_API_KEY env var)
            api_secret: Alpaca secret key (or set ALPACA_SECRET_KEY env var)
            base_url: Alpaca data API base URL
        """
        # Search for .env file in current dir and parent directories up to project root
        env_path = Path(__file__).parent
        for _ in range(10):  # Search up to 10 levels
            env_file = env_path / ".env"
            if env_file.exists():
                load_dotenv(env_file)
                break
            if (env_path / ".git").exists():  # Stop at git root
                load_dotenv(env_file)  # Try loading even if not found
                break
            env_path = env_path.parent

        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.api_secret = api_secret or os.getenv("ALPACA_SECRET_KEY")
        self.base_url = base_url

        if not self.api_key or not self.api_secret:
            raise AlpacaFetcherError(
                "Alpaca API credentials not found. Set ALPACA_API_KEY and ALPACA_SECRET_KEY "
                "environment variables or pass them to the constructor."
            )

        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
        }

    def _make_request(self, endpoint: str, params: dict) -> dict:
        """Make authenticated request to Alpaca API."""
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise AlpacaFetcherError("Authentication failed. Check your API credentials.")
            elif response.status_code == 403:
                raise AlpacaFetcherError(
                    "Access forbidden. Ensure you have Alpaca Elite subscription for options data."
                )
            elif response.status_code == 404:
                raise AlpacaFetcherError(f"Resource not found: {endpoint}")
            else:
                raise AlpacaFetcherError(f"HTTP error {response.status_code}: {str(e)}")
        except requests.exceptions.Timeout:
            raise AlpacaFetcherError("Request timed out. Try again later.")
        except requests.exceptions.RequestException as e:
            raise AlpacaFetcherError(f"Request failed: {str(e)}")

    def fetch_historical_vol(
        self, symbol: str, window: int = 20, timeframe: str = "1Day"
    ) -> float:
        """
        Calculate historical volatility from stock bars.

        Args:
            symbol: Stock ticker symbol (e.g., "SLV")
            window: Number of days for volatility calculation (default: 20)
            timeframe: Bar timeframe (default: "1Day")

        Returns:
            Annualized historical volatility as decimal (e.g., 0.22 = 22%)

        Example:
            >>> fetcher = AlpacaFetcher()
            >>> hv = fetcher.fetch_historical_vol("SLV", window=20)
            >>> print(f"Historical Vol: {hv:.2%}")
            Historical Vol: 22.45%
        """
        logger.info(f"Fetching {window}-day historical volatility for {symbol}")

        # Get enough data for rolling window (add buffer)
        # Use yesterday as end date to ensure data exists (today's data may not be available yet)
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=window + 10)

        endpoint = f"/v2/stocks/{symbol}/bars"
        params = {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "timeframe": timeframe,
            "limit": window + 10,
            "adjustment": "split",
        }

        try:
            data = self._make_request(endpoint, params)
            bars = data.get("bars", [])

            if len(bars) < window:
                raise AlpacaFetcherError(
                    f"Insufficient data for {symbol}. Got {len(bars)} bars, need {window}."
                )

            # Calculate log returns
            closes = np.array([bar["c"] for bar in bars[-window:]])
            log_returns = np.diff(np.log(closes))

            # Annualized standard deviation (252 trading days)
            daily_vol = np.std(log_returns, ddof=1)
            annual_vol = daily_vol * np.sqrt(252)

            logger.info(f"Historical volatility for {symbol}: {annual_vol:.4f} ({annual_vol:.2%})")
            return float(annual_vol)

        except KeyError as e:
            raise AlpacaFetcherError(f"Unexpected API response format: {str(e)}")

    def fetch_spot_price(self, symbol: str) -> float:
        """
        Fetch the current spot price for a symbol.

        Args:
            symbol: Stock/ETF ticker symbol (e.g., "GLD", "SLV")

        Returns:
            Current spot price as float

        Example:
            >>> fetcher = AlpacaFetcher()
            >>> price = fetcher.fetch_spot_price("GLD")
            >>> print(f"GLD: ${price:.2f}")
            GLD: $421.29
        """
        logger.info(f"Fetching spot price for {symbol}")

        endpoint = f"/v2/stocks/{symbol}/quotes/latest"
        params = {}

        try:
            data = self._make_request(endpoint, params)
            quote = data.get("quote", {})

            # Use midpoint of bid/ask for spot price
            bid = quote.get("bp", 0)
            ask = quote.get("ap", 0)

            if bid and ask:
                spot = (bid + ask) / 2
            elif ask:
                spot = ask
            elif bid:
                spot = bid
            else:
                # Fallback to latest trade
                trade_endpoint = f"/v2/stocks/{symbol}/trades/latest"
                trade_data = self._make_request(trade_endpoint, {})
                spot = trade_data.get("trade", {}).get("p", 0)

            if not spot:
                raise AlpacaFetcherError(f"Could not determine spot price for {symbol}")

            logger.info(f"Spot price for {symbol}: ${spot:.2f}")
            return float(spot)

        except KeyError as e:
            raise AlpacaFetcherError(f"Unexpected API response format: {str(e)}")

    def _generate_expiry_dates(
        self, start_date: date, end_date: date
    ) -> list[date]:
        """
        Generate likely options expiry dates within a date range.

        Options typically expire on Fridays (weeklies) and the 3rd Friday (monthlies).
        Some ETFs also have Monday/Wednesday weeklies.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of potential expiry dates to query
        """
        expiry_dates = []
        current = start_date

        while current <= end_date:
            # Include all Fridays (most common expiry day)
            if current.weekday() == 4:  # Friday
                expiry_dates.append(current)
            # Include Mondays and Wednesdays for ETFs with more frequent expirations
            elif current.weekday() in [0, 2]:  # Monday, Wednesday
                expiry_dates.append(current)
            current += timedelta(days=1)

        return expiry_dates

    def _fetch_with_pagination(self, endpoint: str, params: dict) -> dict:
        """
        Fetch all pages of options snapshots using pagination.

        Alpaca limits results to ~100 per request. This method handles
        the next_page_token to fetch all results.

        Args:
            endpoint: API endpoint
            params: Request parameters

        Returns:
            Dict mapping OCC symbols to snapshot data (all pages combined)
        """
        all_snapshots = {}
        page_count = 0

        while True:
            page_count += 1
            data = self._make_request(endpoint, params)
            snapshots = data.get("snapshots", {})

            if snapshots:
                all_snapshots.update(snapshots)

            # Check for next page
            next_page_token = data.get("next_page_token")
            if not next_page_token:
                break

            # Add token for next request
            params["page_token"] = next_page_token
            logger.debug(f"  Fetching page {page_count + 1}...")

        return all_snapshots

    def fetch_options_chain(
        self,
        symbol: str,
        expiry_after: Optional[date] = None,
        expiry_before: Optional[date] = None,
    ) -> dict:
        """
        Fetch options chain with snapshots including greeks.

        Makes multiple API calls to fetch all expiries within the date range,
        handling pagination to get all contracts (calls and puts).

        Args:
            symbol: Underlying ticker symbol (e.g., "SLV")
            expiry_after: Only include options expiring after this date
            expiry_before: Only include options expiring before this date

        Returns:
            Dict mapping OCC symbols to snapshot data

        Example:
            >>> fetcher = AlpacaFetcher()
            >>> chain = fetcher.fetch_options_chain("SLV")
            >>> print(f"Got {len(chain)} option contracts")
            Got 156 option contracts
        """
        logger.info(f"Fetching options chain for {symbol}")

        endpoint = f"/v1beta1/options/snapshots/{symbol}"
        all_snapshots = {}

        # If date range specified, fetch each potential expiry date separately
        if expiry_after and expiry_before:
            expiry_dates = self._generate_expiry_dates(expiry_after, expiry_before)
            logger.info(f"Fetching {len(expiry_dates)} potential expiry dates for {symbol}")

            for exp_date in expiry_dates:
                params = {"expiration_date": exp_date.isoformat()}
                try:
                    snapshots = self._fetch_with_pagination(endpoint, params.copy())

                    if snapshots:
                        logger.info(f"  {exp_date.isoformat()}: {len(snapshots)} contracts")
                        all_snapshots.update(snapshots)

                except AlpacaFetcherError as e:
                    # Log but continue - some dates may not have options
                    logger.debug(f"  {exp_date.isoformat()}: No data ({e})")
                    continue
        else:
            # No date range - use default behavior with pagination
            params = {}
            if expiry_after:
                params["expiration_date_gte"] = expiry_after.isoformat()
            if expiry_before:
                params["expiration_date_lte"] = expiry_before.isoformat()

            try:
                all_snapshots = self._fetch_with_pagination(endpoint, params)
            except KeyError as e:
                raise AlpacaFetcherError(f"Unexpected API response format: {str(e)}")

        if not all_snapshots:
            logger.warning(f"No options data found for {symbol}")

        logger.info(f"Fetched {len(all_snapshots)} total option contracts for {symbol}")
        return all_snapshots

    def parse_option_symbol(self, occ_symbol: str) -> dict:
        """
        Parse OCC format option symbol.

        OCC format: SYMBOL[YY][MM][DD][C/P][STRIKE*1000]
        Example: SLV250221C00025000 = SLV Feb 21 2025 $25 Call

        Args:
            occ_symbol: OCC formatted option symbol

        Returns:
            Dict with keys: symbol, expiry, option_type, strike

        Example:
            >>> fetcher = AlpacaFetcher()
            >>> parsed = fetcher.parse_option_symbol("SLV250221C00025000")
            >>> print(parsed)
            {'symbol': 'SLV', 'expiry': date(2025, 2, 21), 'option_type': 'call', 'strike': 25.0}
        """
        # Pattern: [SYMBOL][YYMMDD][C/P][STRIKE*1000 as 8 digits]
        # Example: SLV250221C00025000
        pattern = r"^([A-Z]+)(\d{6})([CP])(\d{8})$"
        match = re.match(pattern, occ_symbol)

        if not match:
            raise AlpacaFetcherError(f"Invalid OCC symbol format: {occ_symbol}")

        symbol_part, date_part, type_part, strike_part = match.groups()

        # Parse date (YYMMDD)
        year = int("20" + date_part[0:2])
        month = int(date_part[2:4])
        day = int(date_part[4:6])
        expiry = date(year, month, day)

        # Parse type
        option_type = "call" if type_part == "C" else "put"

        # Parse strike (divide by 1000)
        strike = int(strike_part) / 1000.0

        return {
            "symbol": symbol_part,
            "expiry": expiry,
            "option_type": option_type,
            "strike": strike,
        }

    def build_greek_profiles(
        self, symbol: str, chain_data: dict, hist_vol: float
    ) -> list[GreekProfile]:
        """
        Build GreekProfile objects from options chain data.

        Args:
            symbol: Underlying ticker symbol
            chain_data: Options chain data from fetch_options_chain()
            hist_vol: Historical volatility from fetch_historical_vol()

        Returns:
            List of GreekProfile objects

        Example:
            >>> fetcher = AlpacaFetcher()
            >>> hv = fetcher.fetch_historical_vol("SLV")
            >>> chain = fetcher.fetch_options_chain("SLV")
            >>> profiles = fetcher.build_greek_profiles("SLV", chain, hv)
            >>> print(f"Built {len(profiles)} GreekProfile objects")
            Built 156 GreekProfile objects
        """
        logger.info(f"Building GreekProfile objects for {symbol}")

        profiles = []

        for occ_symbol, snapshot in chain_data.items():
            try:
                # Parse OCC symbol
                parsed = self.parse_option_symbol(occ_symbol)

                # Extract snapshot data
                # Alpaca snapshot structure: {latestQuote: {...}, latestTrade: {...}, greeks: {...}}
                greeks = snapshot.get("greeks", {})
                quote = snapshot.get("latestQuote", {})
                trade = snapshot.get("latestTrade", {})

                # Check if greeks are available
                if not greeks or greeks.get("delta") is None:
                    logger.debug(f"Skipping {occ_symbol}: no greeks data")
                    continue

                # Calculate DTE
                today = date.today()
                dte = (parsed["expiry"] - today).days

                # Extract pricing data
                bid = quote.get("bp") if quote else None
                ask = quote.get("ap") if quote else None
                last_price = trade.get("p") if trade else None
                volume = trade.get("s") if trade else None

                # Extract greeks
                delta = greeks.get("delta", 0.0)
                gamma = greeks.get("gamma", 0.0)
                theta = greeks.get("theta", 0.0)
                vega = greeks.get("vega", 0.0)
                # Note: Alpaca returns IV at snapshot level, not in greeks object
                implied_vol = snapshot.get("impliedVolatility", 0.0)

                # Build GreekProfile
                profile = GreekProfile(
                    symbol=parsed["symbol"],
                    strike=parsed["strike"],
                    expiry=parsed["expiry"],
                    option_type=parsed["option_type"],
                    dte=dte,
                    delta=delta,
                    gamma=gamma,
                    theta=theta,
                    vega=vega,
                    implied_vol=implied_vol,
                    hist_vol_20d=hist_vol,
                    bid=bid,
                    ask=ask,
                    last_price=last_price,
                    volume=volume,
                )

                profiles.append(profile)

            except (KeyError, ValueError, AlpacaFetcherError) as e:
                logger.debug(f"Skipping {occ_symbol}: {str(e)}")
                continue

        logger.info(f"Built {len(profiles)} valid GreekProfile objects")
        return profiles

    def fetch_all(
        self,
        symbol: str,
        expiry_after: Optional[date] = None,
        expiry_before: Optional[date] = None,
        hv_window: int = 20,
    ) -> list[GreekProfile]:
        """
        Convenience method to fetch everything and build GreekProfiles.

        Args:
            symbol: Underlying ticker symbol
            expiry_after: Only include options expiring after this date
            expiry_before: Only include options expiring before this date
            hv_window: Window for historical volatility calculation

        Returns:
            List of GreekProfile objects

        Example:
            >>> fetcher = AlpacaFetcher()
            >>> profiles = fetcher.fetch_all("SLV")
            >>> print(f"Fetched {len(profiles)} option profiles")
            Fetched 156 option profiles
        """
        logger.info(f"Fetching all data for {symbol}")

        # Fetch historical volatility
        hist_vol = self.fetch_historical_vol(symbol, window=hv_window)

        # Fetch options chain
        chain = self.fetch_options_chain(symbol, expiry_after, expiry_before)

        # Build profiles
        profiles = self.build_greek_profiles(symbol, chain, hist_vol)

        return profiles


# Convenience function
def fetch_greek_profiles(
    symbol: str,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    expiry_after: Optional[date] = None,
    expiry_before: Optional[date] = None,
) -> list[GreekProfile]:
    """
    Convenience function to fetch GreekProfile objects.

    Example:
        >>> profiles = fetch_greek_profiles("SLV")
        >>> for p in profiles[:5]:
        ...     print(f"{p.strike} {p.option_type} - Delta: {p.delta:.2f}, IV: {p.implied_vol:.2%}")
    """
    fetcher = AlpacaFetcher(api_key=api_key, api_secret=api_secret)
    return fetcher.fetch_all(symbol, expiry_after, expiry_before)


if __name__ == "__main__":
    # Example usage
    import argparse

    parser = argparse.ArgumentParser(description="Fetch options data from Alpaca")
    parser.add_argument("--symbol", default="SLV", help="Ticker symbol")
    parser.add_argument("--output", help="Output JSON file path")
    args = parser.parse_args()

    try:
        profiles = fetch_greek_profiles(args.symbol)

        print(f"\nFetched {len(profiles)} option contracts for {args.symbol}\n")

        # Show sample
        if profiles:
            print("Sample profiles:")
            for profile in profiles[:5]:
                print(
                    f"  {profile.strike} {profile.option_type} "
                    f"(DTE: {profile.dte}) - "
                    f"Delta: {profile.delta:.3f}, "
                    f"IV: {profile.implied_vol:.2%}, "
                    f"Vol Edge: {profile.vol_edge:.2%}"
                )

        # Save if requested
        if args.output:
            import json

            with open(args.output, "w") as f:
                json.dump([p.model_dump(mode="json") for p in profiles], f, indent=2)
            print(f"\nSaved to {args.output}")

    except AlpacaFetcherError as e:
        print(f"Error: {e}")
        sys.exit(1)
