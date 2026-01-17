# Alpaca API - Get Account (Trading API)

**Endpoint:** `GET https://paper-api.alpaca.markets/v2/account`

## Response Schema

### 200 - OK

Returns an Account object with the following fields:

#### Core Account Information

**id**
- **Type:** uuid
- **Required:** Yes
- **Description:** Account ID

**account_number**
- **Type:** string
- **Description:** Account number

**status**
- **Type:** string (enum)
- **Required:** Yes
- **Description:** An enum representing the various possible account status values. Most likely, the account status is ACTIVE unless there is any problem. The account status may get in ACCOUNT_UPDATED when personal information is being updated from the dashboard, in which case you may not be allowed trading for a short period of time until the change is approved.

**Allowed values:**
- `ONBOARDING` - The account is onboarding
- `SUBMISSION_FAILED` - The account application submission failed for some reason
- `SUBMITTED` - The account application has been submitted for review
- `ACCOUNT_UPDATED` - The account information is being updated
- `APPROVAL_PENDING` - The final account approval is pending
- `ACTIVE` - The account is active for trading
- `REJECTED` - The account application has been rejected

**currency**
- **Type:** string
- **Default:** USD
- **Description:** Account currency

**created_at**
- **Type:** date-time
- **Description:** Timestamp this account was created at

#### Balance & Portfolio Information

**cash**
- **Type:** string
- **Description:** Cash balance

**portfolio_value**
- **Type:** string
- **Deprecated:** Yes
- **Description:** Total value of cash + holding positions (This field is deprecated. It is equivalent to the equity field.)

**equity**
- **Type:** string
- **Description:** Cash + long_market_value + short_market_value

**last_equity**
- **Type:** string
- **Description:** Equity as of previous trading day at 16:00:00 ET

**long_market_value**
- **Type:** string
- **Description:** Real-time MtM value of all long positions held in the account

**short_market_value**
- **Type:** string
- **Description:** Real-time MtM value of all short positions held in the account

**accrued_fees**
- **Type:** string
- **Description:** The fees collected

**balance_asof**
- **Type:** string
- **Description:** The date of the snapshot for `last_*` fields

#### Buying Power & Margin

**multiplier**
- **Type:** string
- **Description:** Buying power multiplier that represents account margin classification. Valid values:
  - `1` - Standard limited margin account with 1x buying power
  - `2` - Reg T margin account with 2x intraday and overnight buying power (default for all non-PDT accounts with $2,000 or more equity)
  - `4` - PDT account with 4x intraday buying power and 2x reg T overnight buying power

**buying_power**
- **Type:** string
- **Description:** Current available dollar buying power
  - If multiplier = 4: daytrade buying power = (last_equity - (last) maintenance_margin) * 4
  - If multiplier = 2: buying_power = max(equity – initial_margin, 0) * 2
  - If multiplier = 1: buying_power = cash

**non_marginable_buying_power**
- **Type:** string
- **Description:** Current available non-margin dollar buying power

**daytrading_buying_power**
- **Type:** string
- **Description:** Your buying power for day trades (continuously updated value)

**regt_buying_power**
- **Type:** string
- **Description:** Your buying power under Regulation T (your excess equity - equity minus margin value - times your margin multiplier)

**options_buying_power**
- **Type:** string
- **Description:** Your buying power for options trading

**initial_margin**
- **Type:** string
- **Description:** Reg T initial margin requirement (continuously updated value)

**maintenance_margin**
- **Type:** string
- **Description:** Maintenance margin requirement (continuously updated value)

**last_maintenance_margin**
- **Type:** string
- **Description:** Your maintenance margin requirement on the previous trading day

**sma**
- **Type:** string
- **Description:** Value of special memorandum account (will be used at a later date to provide additional buying_power)

**intraday_adjustments**
- **Type:** string
- **Description:** The intraday adjustment by non_trade_activities such as fund deposit/withdraw

#### Pattern Day Trader Information

**pattern_day_trader**
- **Type:** boolean
- **Description:** Whether or not the account has been flagged as a pattern day trader

**daytrade_count**
- **Type:** integer
- **Description:** The current number of daytrades that have been made in the last 5 trading days (inclusive of today)

#### Options Trading

**options_approved_level**
- **Type:** integer (enum)
- **Description:** The options trading level that was approved for this account.

**Allowed values:**
- `0` - Disabled
- `1` - Covered Call/Cash-Secured Put
- `2` - Long Call/Put
- `3` - Spreads/Straddles

**options_trading_level**
- **Type:** integer (enum)
- **Description:** The effective options trading level of the account. This is the minimum between account options_approved_level and account configurations max_options_trading_level.

**Allowed values:**
- `0` - Disabled
- `1` - Covered Call/Cash-Secured Put
- `2` - Long Call/Put
- `3` - Spreads/Straddles

#### Transfer Information

**pending_transfer_in**
- **Type:** string
- **Description:** Cash pending transfer in

**pending_transfer_out**
- **Type:** string
- **Description:** Cash pending transfer out

#### Account Restrictions

**trade_suspended_by_user**
- **Type:** boolean
- **Description:** User setting. If true, the account is not allowed to place orders.

**trading_blocked**
- **Type:** boolean
- **Description:** If true, the account is not allowed to place orders.

**transfers_blocked**
- **Type:** boolean
- **Description:** If true, the account is not allowed to request money transfers.

**account_blocked**
- **Type:** boolean
- **Description:** If true, the account activity by user is prohibited.

**shorting_enabled**
- **Type:** boolean
- **Description:** Flag to denote whether or not the account is permitted to short

#### Fees

**pending_reg_taf_fees**
- **Type:** string
- **Description:** Pending regulatory fees for the account

## Example Request

### Shell (cURL)
```bash
curl --request GET \
     --url https://paper-api.alpaca.markets/v2/account \
     --header 'accept: application/json'
```

---

**Source:** https://docs.alpaca.markets/reference/getaccount-1
**Last Updated:** About 23 hours ago
