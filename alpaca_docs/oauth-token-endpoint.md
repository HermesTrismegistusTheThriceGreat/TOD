# Alpaca Markets API - OAuth Token Endpoint

## Issue Tokens

### Endpoint
`POST https://authx.alpaca.markets/v1/oauth2/token`

### Request Parameters

#### grant_type
- **Type:** string
- **Format:** enum
- **Required:** Yes
- **Value:** `client_credentials`
- **Description:** Grant type

**Allowed values:**
- `client_credentials`

#### client_id
- **Type:** string
- **Required:** Yes
- **Length:** between 20 and 32 characters
- **Description:** Client ID

#### client_secret
- **Type:** string
- **Length:** ≤ 128 characters
- **Description:** Client secret (if using client_secret)

#### client_assertion_type
- **Type:** string
- **Format:** enum
- **Description:** Client assertion type (if using private_key_jwt)
- **Value:** `urn:ietf:params:oauth:client-assertion-type:jwt-bearer`

**Allowed values:**
- `urn:ietf:params:oauth:client-assertion-type:jwt-bearer`

#### client_assertion
- **Type:** string
- **Length:** ≤ 16384 characters
- **Description:** Client assertion JWT (if using private_key_jwt)

## Responses

### 200 OK

**Response object:**

#### access_token
- **Type:** string
- **Required:** Yes
- **Description:** Access token

#### expires_in
- **Type:** integer
- **Required:** Yes
- **Description:** Time in seconds until the token expires

#### token_type
- **Type:** string
- **Format:** enum
- **Required:** Yes
- **Value:** `Bearer`
- **Description:** Type of the token (e.g., Bearer)

### Default Error Response

**Response object:**

#### error
- **Type:** string
- **Format:** enum
- **Required:** Yes
- **Description:** Error code

**Allowed error codes:**
- `unknown_error`
- `invalid_request_uri`
- `invalid_request_object`
- `consent_required`
- `interaction_required`
- `login_required`
- `request_unauthorized`
- `request_forbidden`
- `invalid_request`
- `unauthorized_client`
- `access_denied`
- `unsupported_response_type`
- `unsupported_response_mode`
- `invalid_scope`
- `server_error`
- `temporarily_unavailable`
- `unsupported_grant_type`
- `invalid_grant`
- `invalid_client`
- `not_found`
- `invalid_state`
- `misconfiguration`
- `insufficient_entropy`
- `invalid_token`
- `token_signature_mismatch`
- `scope_not_granted`
- `token_claim`
- `token_inactive`
- `request_not_supported`
- `request_uri_not_supported`
- `jti_known`
- `quota_exceeded`

#### fields
- **Type:** array of objects
- **Description:** List of invalid request fields, if any

**Field object:**
- **name** (string, required): Name of the request field

## Example Request

### Shell (cURL)
```bash
curl --request POST \
     --url https://authx.alpaca.markets/v1/oauth2/token \
     --header 'accept: application/json' \
     --header 'content-type: application/x-www-form-urlencoded' \
     --data grant_type=client_credentials
```

---

**Source:** https://docs.alpaca.markets/reference/issuetokens
**Last Updated:** About 1 month ago
