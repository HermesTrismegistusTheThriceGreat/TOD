#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "python-dotenv"]
# ///
"""Debug script to check if puts are in raw Alpaca API response."""

import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load env from backend
backend_env = Path("/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/.env")
if backend_env.exists():
    load_dotenv(backend_env)

api_key = os.getenv("ALPACA_API_KEY")
api_secret = os.getenv("ALPACA_SECRET_KEY")
base_url = "https://data.alpaca.markets"
headers = {"APCA-API-KEY-ID": api_key, "APCA-API-SECRET-KEY": api_secret}

# Get raw chain data for one expiry
today = date.today()
expiry = today + timedelta(days=5)

print(f"Fetching GLD options for expiry: {expiry.isoformat()}")

endpoint = f"{base_url}/v1beta1/options/snapshots/GLD"
params = {"expiration_date": expiry.isoformat()}
response = requests.get(endpoint, headers=headers, params=params, timeout=30)
data = response.json()

snapshots = data.get("snapshots", {})
print(f"Total snapshots returned: {len(snapshots)}")

# Parse OCC symbols to find calls and puts
# OCC format: SYMBOL[YYMMDD][C/P][STRIKE*1000]
# Example: GLD260123C00420000

calls = []
puts = []
for symbol in snapshots.keys():
    # Match pattern
    match = re.match(r"^([A-Z]+)(\d{6})([CP])(\d{8})$", symbol)
    if match:
        option_type = match.group(3)
        if option_type == "C":
            calls.append(symbol)
        elif option_type == "P":
            puts.append(symbol)
    else:
        print(f"Unmatched symbol format: {symbol}")

print(f"\nCalls in raw data: {len(calls)}")
print(f"Puts in raw data: {len(puts)}")

if calls:
    print(f"\nSample call symbols: {calls[:3]}")
if puts:
    print(f"Sample put symbols: {puts[:3]}")
else:
    print("\nNo puts found! Checking if API limiting to 100 results...")

    # Try fetching without date filter to get more
    print("\nFetching without date filter...")
    response2 = requests.get(endpoint, headers=headers, timeout=30)
    data2 = response2.json()
    snapshots2 = data2.get("snapshots", {})
    print(f"Total without date filter: {len(snapshots2)}")

    calls2 = []
    puts2 = []
    for symbol in snapshots2.keys():
        match = re.match(r"^([A-Z]+)(\d{6})([CP])(\d{8})$", symbol)
        if match:
            option_type = match.group(3)
            if option_type == "C":
                calls2.append(symbol)
            elif option_type == "P":
                puts2.append(symbol)

    print(f"Calls: {len(calls2)}, Puts: {len(puts2)}")
    if puts2:
        print(f"Sample put symbols: {puts2[:3]}")
