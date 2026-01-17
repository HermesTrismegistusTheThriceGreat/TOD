# Alpaca API - Get All Open Positions

**Endpoint:** `GET https://paper-api.alpaca.markets/v2/positions`

## Response Schema

### 200 - Successful Response

Returns an array of Position objects.

#### Position Object Fields:

**asset_id**
- **Type:** uuid
- **Required:** Yes
- **Description:** Asset ID (For options this represents the option contract ID)

**symbol**
- **Type:** string
- **Required:** Yes
- **Description:** Symbol name of the asset

**exchange**
- **Type:** string (enum)
- **Required:** Yes
- **Description:** Represents the current exchanges Alpaca supports. Can be empty if not applicable (e.g., for options contracts).

**Allowed values:**
- `AMEX`
- `ARCA`
- `BATS`
- `NYSE`
- `NASDAQ`
- `NYSEARCA`
- `OTC`
- `null`

**Supported exchanges:**
- AMEX
- ARCA
- BATS
- NYSE
- NASDAQ
- NYSEARCA
- OTC

**asset_class**
- **Type:** string (enum)
- **Required:** Yes
- **Description:** This represents the category to which the asset belongs to. It serves to identify the nature of the financial instrument.

**Allowed values:**
- `us_equity` - U.S. equities
- `us_option` - U.S. options
- `crypto` - Cryptocurrencies

**avg_entry_price**
- **Type:** string
- **Required:** Yes
- **Min Length:** 1
- **Description:** Average entry price of the position

**qty**
- **Type:** string
- **Required:** Yes
- **Min Length:** 1
- **Description:** The number of shares

**qty_available**
- **Type:** string
- **Min Length:** 1
- **Description:** Total number of shares available minus open orders / locked for options covered call

**side**
- **Type:** string
- **Required:** Yes
- **Min Length:** 1
- **Description:** Position side (typically "long")

**market_value**
- **Type:** string
- **Required:** Yes
- **Min Length:** 1
- **Description:** Total dollar amount of the position

**cost_basis**
- **Type:** string
- **Required:** Yes
- **Min Length:** 1
- **Description:** Total cost basis in dollars

**unrealized_pl**
- **Type:** string
- **Required:** Yes
- **Min Length:** 1
- **Description:** Unrealized profit/loss in dollars

**unrealized_plpc**
- **Type:** string
- **Required:** Yes
- **Min Length:** 1
- **Description:** Unrealized profit/loss percent (by a factor of 1)

**unrealized_intraday_pl**
- **Type:** string
- **Required:** Yes
- **Min Length:** 1
- **Description:** Unrealized profit/loss in dollars for the day

**unrealized_intraday_plpc**
- **Type:** string
- **Required:** Yes
- **Min Length:** 1
- **Description:** Unrealized profit/loss percent for the day (by a factor of 1)

**current_price**
- **Type:** string
- **Required:** Yes
- **Min Length:** 1
- **Description:** Current asset price per share

**lastday_price**
- **Type:** string
- **Required:** Yes
- **Min Length:** 1
- **Description:** Last day's asset price per share based on the closing value of the last trading day

**change_today**
- **Type:** string
- **Required:** Yes
- **Min Length:** 1
- **Description:** Percent change from last day price (by a factor of 1)

**asset_marginable**
- **Type:** boolean
- **Required:** Yes
- **Description:** Whether the asset is marginable

## Example Request

### Shell (cURL)
```bash
curl --request GET \
     --url https://paper-api.alpaca.markets/v2/positions \
     --header 'accept: application/json'
```

## Notes

- This endpoint returns all currently open positions for the account
- Position values are updated in real-time
- Unrealized P&L is calculated based on current market prices
- For options positions, the asset_id represents the option contract ID

---

**Source:** https://docs.alpaca.markets/reference/getallopenpositions
**Last Updated:** About 23 hours ago
