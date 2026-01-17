# Alpaca API - Get All Orders (GET)

**Endpoint:** `GET https://paper-api.alpaca.markets/v2/orders`

## Query Parameters

### status
- **Type:** string (enum)
- **Default:** open
- **Description:** Order status to be queried. Options: open, closed, or all. Defaults to open.

**Allowed values:**
- `open`
- `closed`
- `all`

### limit
- **Type:** integer
- **Default:** 50
- **Max:** 500
- **Description:** The maximum number of orders in response.

### after
- **Type:** string
- **Description:** The response will include only ones submitted after this timestamp (exclusive).

### until
- **Type:** string
- **Description:** The response will include only ones submitted until this timestamp (exclusive).

### direction
- **Type:** string (enum)
- **Default:** desc
- **Description:** The chronological order of response based on the submission time. Options: asc or desc.

**Allowed values:**
- `asc`
- `desc`

### nested
- **Type:** boolean
- **Description:** If true, the result will roll up multi-leg orders under the legs field of primary order.

### symbols
- **Type:** string
- **Description:** A comma-separated list of symbols to filter by (ex. "AAPL,TSLA,MSFT"). A currency pair is required for crypto orders (ex. "BTCUSD,BCHUSD,LTCUSD,ETCUSD").

### side
- **Type:** string
- **Description:** Filters down to orders that have a matching side field set.

### asset_class
- **Type:** array of strings
- **Description:** A comma separated list of asset classes, the response will include only orders in the specified asset classes. By specifying `us_option` as the class, you can query option orders by underlying symbol using the symbols parameter.

### before_order_id
- **Type:** string
- **Description:** Return orders submitted before the order with this ID (exclusive). Mutually exclusive with `after_order_id`. Do not combine with `after`/`until`.

### after_order_id
- **Type:** string
- **Description:** Return orders submitted after the order with this ID (exclusive). Mutually exclusive with `before_order_id`. Do not combine with `after`/`until`.

## Response Schema

### 200 - Successful Response
Returns an array of Order objects.

#### Order Object Fields:

**id**
- **Type:** string
- **Description:** Order ID

**client_order_id**
- **Type:** string
- **Max Length:** 128 characters
- **Description:** Client unique order ID

**created_at**
- **Type:** date-time

**updated_at**
- **Type:** date-time | null

**submitted_at**
- **Type:** date-time | null

**filled_at**
- **Type:** date-time | null

**expired_at**
- **Type:** date-time | null

**canceled_at**
- **Type:** date-time | null

**failed_at**
- **Type:** date-time | null

**replaced_at**
- **Type:** date-time | null

**replaced_by**
- **Type:** uuid | null
- **Description:** The order ID that this order was replaced by

**replaces**
- **Type:** uuid | null
- **Description:** The order ID that this order replaces

**asset_id**
- **Type:** uuid
- **Description:** Asset ID (For options this represents the option contract ID)

**symbol**
- **Type:** string
- **Min Length:** 1
- **Description:** Asset symbol, required for all order classes except for `mleg`

**asset_class**
- **Type:** string (enum)
- **Description:** This represents the category to which the asset belongs to. It serves to identify the nature of the financial instrument.

**Allowed values:**
- `us_equity` - U.S. equities
- `us_option` - U.S. options
- `crypto` - Cryptocurrencies

**notional**
- **Type:** string | null
- **Required:** Yes
- **Description:** Ordered notional amount. If entered, qty will be null. Can take up to 9 decimal points.

**qty**
- **Type:** string | null
- **Description:** Ordered quantity. If entered, notional will be null. Can take up to 9 decimal points. Required if order class is `mleg`.

**filled_qty**
- **Type:** string
- **Min Length:** 1
- **Description:** Filled quantity

**filled_avg_price**
- **Type:** string | null
- **Description:** Filled average price

**order_class**
- **Type:** string (enum)
- **Description:** The order classes supported by Alpaca vary based on the order's security type.

**Allowed values:**
- `simple`
- `bracket`
- `oco`
- `oto`
- `mleg`

**order_type**
- **Type:** string
- **Deprecated:** Yes
- **Description:** Deprecated in favour of the field "type"

**type**
- **Type:** string (enum)
- **Required:** Yes
- **Description:** The order types supported by Alpaca vary based on the order's security type.
  - **Equity trading:** market, limit, stop, stop_limit, trailing_stop
  - **Options trading:** market, limit
  - **Multileg Options trading:** market, limit
  - **Crypto trading:** market, limit, stop_limit

**Allowed values:**
- `market`
- `limit`
- `stop`
- `stop_limit`
- `trailing_stop`

**side**
- **Type:** string (enum)
- **Description:** Represents which side this order was on. Required for all order classes except for mleg.

**Allowed values:**
- `buy`
- `sell`

**time_in_force**
- **Type:** string (enum)
- **Required:** Yes
- **Description:** The Time-In-Force values supported by Alpaca vary based on the order's security type.
  - **Equity trading:** day, gtc, opg, cls, ioc, fok
  - **Options trading:** day
  - **Crypto trading:** gtc, ioc

**Allowed values:**
- `day`
- `gtc`
- `opg`
- `cls`
- `ioc`
- `fok`

#### Time-In-Force Descriptions:

**day:**
A day order is eligible for execution only on the day it is live. By default, the order is only valid during Regular Trading Hours (9:30am - 4:00pm ET). If unfilled after the closing auction, it is automatically canceled. If submitted after the close, it is queued and submitted the following trading day. However, if marked as eligible for extended hours, the order can also execute during supported extended hours.

**gtc:**
The order is good until canceled. Non-marketable GTC limit orders are subject to price adjustments to offset corporate actions affecting the issue. We do not currently support Do Not Reduce(DNR) orders to opt out of such price adjustments.

**opg:**
Use this TIF with a market/limit order type to submit "market on open" (MOO) and "limit on open" (LOO) orders. This order is eligible to execute only in the market opening auction. Any unfilled orders after the open will be cancelled. OPG orders submitted after 9:28am but before 7:00pm ET will be rejected. OPG orders submitted after 7:00pm will be queued and routed to the following day's opening auction. On open/on close orders are routed to the primary exchange. Such orders do not necessarily execute exactly at 9:30am / 4:00pm ET but execute per the exchange's auction rules.

**cls:**
Use this TIF with a market/limit order type to submit "market on close" (MOC) and "limit on close" (LOC) orders. This order is eligible to execute only in the market closing auction. Any unfilled orders after the close will be cancelled. CLS orders submitted after 3:50pm but before 7:00pm ET will be rejected. CLS orders submitted after 7:00pm will be queued and routed to the following day's closing auction. Only available with API v2.

**ioc:**
An Immediate Or Cancel (IOC) order requires all or part of the order to be executed immediately. Any unfilled portion of the order is canceled. Only available with API v2. Most market makers who receive IOC orders will attempt to fill the order on a principal basis only, and cancel any unfilled balance. On occasion, this can result in the entire order being cancelled if the market maker does not have any existing inventory of the security in question.

**fok:**
A Fill or Kill (FOK) order is only executed if the entire order quantity can be filled, otherwise the order is canceled. Only available with API v2.

**limit_price**
- **Type:** string | null
- **Description:** Limit price

**stop_price**
- **Type:** string | null
- **Description:** Stop price

**status**
- **Type:** string (enum)
- **Description:** An order executed through Alpaca can experience several status changes during its lifecycle.

**Allowed values:**
- `new`
- `partially_filled`
- `filled`
- `done_for_day`
- `canceled`
- `expired`
- `replaced`
- `pending_cancel`
- `pending_replace`
- `accepted`
- `pending_new`
- `accepted_for_bidding`
- `stopped`
- `rejected`
- `suspended`
- `calculated`

#### Order Status Descriptions:

**Most Common Statuses:**

**new:**
The order has been received by Alpaca, and routed to exchanges for execution. This is the usual initial state of an order.

**partially_filled:**
The order has been partially filled.

**filled:**
The order has been filled, and no further updates will occur for the order.

**done_for_day:**
The order is done executing for the day, and will not receive further updates until the next trading day.

**canceled:**
The order has been canceled, and no further updates will occur for the order. This can be either due to a cancel request by the user, or the order has been canceled by the exchanges due to its time-in-force.

**expired:**
The order has expired, and no further updates will occur for the order.

**replaced:**
The order was replaced by another order, or was updated due to a market event such as corporate action.

**pending_cancel:**
The order is waiting to be canceled.

**pending_replace:**
The order is waiting to be replaced by another order. The order will reject cancel request while in this state.

**Less Common Statuses:**

**accepted:**
The order has been received by Alpaca, but hasn't yet been routed to the execution venue. This could be seen often outside of trading session hours.

**pending_new:**
The order has been received by Alpaca, and routed to the exchanges, but has not yet been accepted for execution. This state only occurs on rare occasions.

**accepted_for_bidding:**
The order has been received by exchanges, and is evaluated for pricing. This state only occurs on rare occasions.

**stopped:**
The order has been stopped, and a trade is guaranteed for the order, usually at a stated price or better, but has not yet occurred. This state only occurs on rare occasions.

**rejected:**
The order has been rejected, and no further updates will occur for the order. This state occurs on rare occasions and may occur based on various conditions decided by the exchanges.

**suspended:**
The order has been suspended, and is not eligible for trading. This state only occurs on rare occasions.

**calculated:**
The order has been completed for the day (either filled or done for day), but remaining settlement calculations are still pending. This state only occurs on rare occasions.

**Note:** An order may be canceled through the API up until the point it reaches a state of either filled, canceled, or expired.

**extended_hours**
- **Type:** boolean
- **Description:** If true, eligible for execution outside regular trading hours.

**legs**
- **Type:** array of objects | null
- **Description:** When querying non-simple order_class orders in a nested style, an array of Order entities associated with this order. Otherwise, null. Required if order class is `mleg`.

**trail_percent**
- **Type:** string | null
- **Description:** The percent value away from the high water mark for trailing stop orders.

**trail_price**
- **Type:** string | null
- **Description:** The dollar value away from the high water mark for trailing stop orders.

**hwm**
- **Type:** string | null
- **Description:** The highest (lowest) market price seen since the trailing stop order was submitted.

**position_intent**
- **Type:** string (enum)
- **Description:** Represents the desired position strategy.

**Allowed values:**
- `buy_to_open`
- `buy_to_close`
- `sell_to_open`
- `sell_to_close`

## Example Request

### Shell (cURL)
```bash
curl --request GET \
     --url https://paper-api.alpaca.markets/v2/orders \
     --header 'accept: application/json'
```

---

**Source:** https://docs.alpaca.markets/reference/getallorders
**Last Updated:** About 23 hours ago
