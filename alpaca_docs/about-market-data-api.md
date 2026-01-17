# About Market Data API

## Overview

The Alpaca Market Data API provides "seamless access to market data through both HTTP and WebSocket protocols" with emphasis on historical and real-time data integration. The platform offers SDKs in Python, Go, NodeJS, and C# to simplify implementation, and developers can experiment using Postman through either a public workspace or GitHub repository.

## Subscription Plans

### For Regular Users

**Basic Plan** (Free)
- US Stocks & ETFs coverage
- Real-time IEX data only
- 30 WebSocket symbol subscriptions
- Historical data since 2016 (limited to latest 15 minutes)
- 200 API calls per minute

**Algo Trader Plus** ($99/month)
- US Stocks & ETFs coverage
- All US Stock Exchange access
- Unlimited WebSocket subscriptions
- Full historical data without restrictions
- 10,000 API calls per minute

### Options Trading

Both plans cover US Options Securities. Basic includes indicative pricing (200 quote subscriptions), while Algo Trader Plus provides OPRA Feed access (1,000 quote subscriptions).

Data originates from CTA (Consolidated Tape Association) via NYSE and UTP (Unlisted Trading Privileges) via Nasdaq, ensuring 100% market volume coverage.

### Broker Partners

Custom plans available with varying request rates (1,000-10,000 RPM), connection limits, and pricing ($500-$2,000/month). Options add $1,000 monthly for Standard/StandardPlus3000 tiers.

## Authentication

**Trading API**: Credentials passed via headers `APCA-API-KEY-ID` and `APCA-API-SECRET-KEY`

**Broker API**: HTTP Basic authentication using base-64 encoded `key:secret` format in Authorization header

WebSocket authentication follows separate documentation guidelines.
