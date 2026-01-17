# Option Chain Snapshots API Reference

## Endpoint

```
GET https://data.alpaca.markets/v1beta1/options/snapshots/{underlying_symbol}
```

## Parameters

### underlying_symbol

**Type:** string
**Required:** Yes

The financial instrument on which an option contract is based or derived.

### feed

**Type:** string (enum)
**Default:** `opra`

The source feed of the data. `opra` is the official OPRA feed, `indicative` is a free indicative feed where trades are delayed and quotes are modified. Default: `opra` if the user has a subscription, otherwise `indicative`.

**Allowed values:**
- `opra`
- `indicative`

### limit

**Type:** integer
**Range:** 1 to 1000
**Default:** 100

Number of maximum snapshots to return in a response.
The limit applies to the total number of data points, not the number per symbol!
Use `next_page_token` to fetch the next set of responses.

### updated_since

**Type:** date-time

Filter to snapshots that were updated since this timestamp, meaning that the timestamp of the trade or the quote is greater than or equal to this value.
Format: RFC-3339 or YYYY-MM-DD. If missing, all values are returned.

### page_token

**Type:** string

The pagination token from which to continue. The value to pass here is returned in specific requests when more data is available, usually because of a response result limit.

### type

**Type:** string (enum)

Filter contracts by the type (call or put).

**Allowed values:**
- `call`
- `put`

### strike_price_gte

**Type:** double

Filter contracts with strike price greater than or equal to the specified value.

### strike_price_lte

**Type:** double

Filter contracts with strike price less than or equal to the specified value.

### expiration_date

**Type:** date

Filter contracts by the exact expiration date (format: YYYY-MM-DD).

### expiration_date_gte

**Type:** date

Filter contracts with expiration date greater than or equal to the specified date.

### expiration_date_lte

**Type:** date

Filter contracts with expiration date less than or equal to the specified date.

### root_symbol

**Type:** string

Filter contracts by the root symbol.

## Response Codes

### 200 OK

**Response Body:**

```json
{
  "snapshots": {
    // Additional properties
  },
  "next_page_token": "string | null"
}
```

**Fields:**
- `snapshots` (object, required): View Additional Properties
- `next_page_token` (string | null, required): Pagination token for the next page

**Response Headers:**
- `X-RateLimit-Limit` (integer): Request limit per minute
- `X-RateLimit-Remaining` (integer): Request limit per minute remaining
- `X-RateLimit-Reset` (integer): The UNIX epoch when the remaining quota changes

### 400 Bad Request

One of the request parameters is invalid. See the returned message for details.

**Response Headers:**
- `X-RateLimit-Limit` (integer): Request limit per minute
- `X-RateLimit-Remaining` (integer): Request limit per minute remaining
- `X-RateLimit-Reset` (integer): The UNIX epoch when the remaining quota changes

### 401 Unauthorized

Authentication headers are missing or invalid. Make sure you authenticate your request with a valid API key.

### 403 Forbidden

The requested resource is forbidden.

### 429 Too Many Requests

Too many requests. You hit the rate limit. Use the X-RateLimit-... response headers to make sure you're under the rate limit.

**Response Headers:**
- `X-RateLimit-Limit` (integer): Request limit per minute
- `X-RateLimit-Remaining` (integer): Request limit per minute remaining
- `X-RateLimit-Reset` (integer): The UNIX epoch when the remaining quota changes

### 500 Internal Server Error

Internal server error. We recommend retrying these later. If the issue persists, please contact us on [Slack](https://alpaca.markets/slack) or on the [Community Forum](https://forum.alpaca.markets/).

## Example Request

### Shell

```bash
curl --request GET \
     --url 'https://data.alpaca.markets/v1beta1/options/snapshots/underlying_symbol?feed=opra&limit=100' \
     --header 'accept: application/json'
```

## Supported Languages

- Shell
- Node
- Ruby
- PHP
- Python

---

**Source:** https://docs.alpaca.markets/reference/optionchain
**Last Updated:** About 23 hours ago
