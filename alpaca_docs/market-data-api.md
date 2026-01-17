# Overview

The Market Data API offers seamless access to market data through both HTTP and WebSocket protocols. With a focus on historical and real-time data, developers can efficiently integrate these APIs into their applications.

To simplify the integration process, we provide user-friendly SDKs in [Python](https://github.com/alpacahq/alpaca-py), [Go](https://github.com/alpacahq/alpaca-trade-api-go), [NodeJS](https://github.com/alpacahq/alpaca-trade-api-js), and [C#](https://github.com/alpacahq/alpaca-trade-api-csharp). These SDKs offer comprehensive functionalities, making it easier for developers to work with the Market Data APIs & Web Sockets.

To experiment with the APIs, developers can try them with [Postman](https://www.postman.com/): either through the [public workspace on Postman](https://www.postman.com/alpacamarkets) or directly from our [GitHub repository](https://github.com/alpacahq/alpaca-postman).

By leveraging Alpaca Market Data API and its associated SDKs, developers can seamlessly incorporate historical and real-time market data into their applications, enabling them to build powerful and data-driven financial products.

# Subscription Plans

For regular users we offer two subscription plans: **Basic** and **Algo Trader Plus**.

The **Basic** plan serves as the default option for both Paper and Live trading accounts, ensuring all users can access essential data with zero cost. However, this plan only includes limited real-time data: for equities only the IEX exchange, for options only the indicative feed. For advanced traders we recommend subscribing to **Algo Trader Plus** which includes complete market coverage for stocks and options as well.

## Equities

|  | Basic | Algo Trader Plus |
| --- | --- | --- |
| Pricing | Free | $99 / month |
| Securities coverage | US Stocks & ETFs | US Stocks & ETFs |
| Real-time market coverage | IEX | All US Stock Exchanges |
| Websocket subscriptions | 30 symbols | Unlimited |
| Historical data timeframe | Since 2016 | Since 2016 |
| Historical data limitation\* | latest 15 minutes | no restriction |
| Historical API calls | 200 / min | 10,000 / min |

Our data sources are directly fed by the CTA (Consolidated Tape Association), which is administered by NYSE (New York Stock Exchange), and the UTP (Unlisted Trading Privileges) stream, which is administered by Nasdaq. The synergy of these two sources ensures comprehensive market coverage, encompassing 100% of market volume.

## Options

|  | Basic | Algo Trader Plus |
| --- | --- | --- |
| Securities coverage | US Options Securities | US Options Securities |
| Real-time market coverage | Indicative Pricing Feed | OPRA Feed |
| Websocket subscriptions | 200 quotes | 1000 quotes |
| Historical data limitation\* | latest 15 minutes | no restriction |
| Historical API calls | 200 / min | 10,000 / min |

Our options data sources are directly fed by OPRA (Options Price Reporting Authority).

## Broker partners

For equities, the below subscription plans are available.

| Subscription Name | RPM (Request Per Minute) | Stream Connection Limit | Stream Symbol Limit | Price (per month) | Options Indicative Feed |
| --- | --- | --- | --- | --- | --- |
| Standard | 1,000 | 5 | unlimited | included | additional $1,000 per month |
| StandardPlus3000 | 3,000 | 5 | unlimited | $500 | additional $1,000 per month |
| StandardPlus5000 | 5,000 | 5 | unlimited | $1,000 | included |
| StandardPlus10000 | 10,000 | 10 | unlimited | $2,000 | included |

\*Note: Standard subscription plans will only be active when integration starts. Prior to that, the account will be on the Basic plan listed above. Additionally, similar to the free plan all the standard plans are real time IEX or 15 mins delayed SIP.

For partners on the Standard and StandardPlus3000 plans, an additional subscription fee of $1,000 / month enables access to the same equities plan for options. For StandardPlus5000 and StandardPlus10000 plans, options are included.

We offer custom pricing and tailored solutions for Broker API partners seeking to leverage our comprehensive market data. Our goal is to meet the specific needs and requirements of our valued partners, ensuring they have access to the data and tools necessary to enhance their services and provide exceptional value to their customers. If none of the subscription plans listed above are believed to be suitable, kindly reach out to our [sales team](https://alpaca.markets/contact).

# Authentication

With the exception of historical crypto data, all market data endpoints require authentication. Authentication differs between the Trading & Broker API. API keys can be acquired in the web UI (under the API keys on the right sidebar).

## Trading API

You should authenticate by passing the key / secret pair in the HTTP request headers named `APCA-API-KEY-ID` and `APCA-API-SECRET-KEY`, respectively.

## Broker API

You should authenticate using HTTP Basic authentication. Use your correspondent API\_KEY and API\_SECRET as the username and password. The format is `key:secret`. Encode the string with base-64 encoding, and you can pass it as an authentication header in the `Authorization` header.

**Note:** For the WebSocket stream authentication, kindly refer to the WebSocket Stream [documentation](https://docs.alpaca.markets/docs/streaming-market-data#authentication).
