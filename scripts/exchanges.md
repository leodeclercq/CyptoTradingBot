# Notes spécifique Binance Exchange

Cette page regroupe les problèmes courants et les informations qui sont spécifiques à Binance Exchange.

## Exchange configuration

IA TRADE BOT est basée sur [CCXT library](https://github.com/ccxt/ccxt)  100 cryptocurrency
exchange markets and trading APIs. The complete up-to-date list can be found in the
[CCXT repo homepage](https://github.com/ccxt/ccxt/tree/master/python).
However, the bot was tested by the development team with only a few exchanges.
A current list of these can be found in the "Home" section of this documentation.

Feel free to test other exchanges and submit your feedback or PR to improve the bot or confirm exchanges that work flawlessly..

Some exchanges require special configuration, which can be found below.

### Sample exchange configuration

A exchange configuration for "binance" would look as follows:

```json
"exchange": {
    "name": "binance",
    "key": "your_exchange_key",
    "secret": "your_exchange_secret",
    "ccxt_config": {},
    "ccxt_async_config": {},
    // ... 
```

### Setting rate limits

Usually, rate limits set by CCXT are reliable and work well.
In case of problems related to rate-limits (usually DDOS Exceptions in your logs), it's easy to change rateLimit settings to other values.

```json
"exchange": {
    "name": "kraken",
    "key": "your_exchange_key",
    "secret": "your_exchange_secret",
    "ccxt_config": {"enableRateLimit": true},
    "ccxt_async_config": {
        "enableRateLimit": true,
        "rateLimit": 3100
    },
```

This configuration enables kraken, as well as rate-limiting to avoid bans from the exchange.
`"rateLimit": 3100` defines a wait-event of 3.1s between each call. This can also be completely disabled by setting `"enableRateLimit"` to false.

!!! Note
    Optimal settings for rate-limiting depend on the exchange and the size of the whitelist, so an ideal parameter will vary on many other settings.
    We try to provide sensible defaults per exchange where possible, if you encounter bans please make sure that `"enableRateLimit"` is enabled and increase the `"rateLimit"` parameter step by step.

## Binance

!!! Warning "Server location and geo-ip restrictions"
    Please be aware that Binance restricts API access regarding the server country. The current and non-exhaustive countries blocked are Canada, Malaysia, Netherlands and United States. Please go to [binance terms > b. Eligibility](https://www.binance.com/en/terms) to find up to date list.

Binance supports [time_in_force](configuration.md#understand-order_time_in_force).

!!! Tip "Stoploss on Exchange"
    Binance supports `stoploss_on_exchange` and uses `stop-loss-limit` orders. It provides great advantages, so we recommend to benefit from it by enabling stoploss on exchange.
    On futures, Binance supports both `stop-limit` as well as `stop-market` orders. You can use either `"limit"` or `"market"` in the `order_types.stoploss` configuration setting to decide which type to use.

### Binance Blacklist recommendation

For Binance, it is suggested to add `"BNB/<STAKE>"` to your blacklist to avoid issues, unless you are willing to maintain enough extra `BNB` on the account or unless you're willing to disable using `BNB` for fees.
Binance accounts may use `BNB` for fees, and if a trade happens to be on `BNB`, further trades may consume this position and make the initial BNB trade unsellable as the expected amount is not there anymore.

If not enough `BNB` is available to cover transaction fees, then fees will not be covered by `BNB` and no fee reduction will occur. Freqtrade will never buy BNB to cover for fees. BNB needs to be bought and monitored manually to this end.

### Binance sites

Binance has been split into 2, and users must use the correct ccxt exchange ID for their exchange, otherwise API keys are not recognized.

* [binance.com](https://www.binance.com/) - International users. Use exchange id: `binance`.
* [binance.us](https://www.binance.us/) - US based users. Use exchange id: `binanceus`.

### Binance RSA keys

Freqtrade supports binance RSA API keys.

We recommend to use them as environment variable.

``` bash
export FREQTRADE__EXCHANGE__SECRET="$(cat ./rsa_binance.private)"
```

They can however also be configured via configuration file. Since json doesn't support multi-line strings, you'll have to replace all newlines with `\n` to have a valid json file.

``` json
// ...
 "key": "<someapikey>",
 "secret": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBABACAFQA<...>s8KX8=\n-----END PRIVATE KEY-----"
// ...
```

### Binance Futures

Binance has specific (unfortunately complex) [Futures Trading Quantitative Rules](https://www.binance.com/en/support/faq/4f462ebe6ff445d4a170be7d9e897272) which need to be followed, and which prohibit a too low stake-amount (among others) for too many orders.
Violating these rules will result in a trading restriction.

When trading on Binance Futures market, orderbook must be used because there is no price ticker data for futures.

``` jsonc
  "entry_pricing": {
      "use_order_book": true,
      "order_book_top": 1,
      "check_depth_of_market": {
          "enabled": false,
          "bids_to_ask_delta": 1
      }
  },
  "exit_pricing": {
      "use_order_book": true,
      "order_book_top": 1
  },
```

#### Binance isolated futures settings

Users will also have to have the futures-setting "Position Mode" set to "One-way Mode", and "Asset Mode" set to "Single-Asset Mode".
These settings will be checked on startup, and freqtrade will show an error if this setting is wrong.

![Binance futures settings](assets/binance_futures_settings.png)

Freqtrade will not attempt to change these settings.

#### Binance BNFCR futures

BNFCR mode are a special type of futures mode on Binance to work around regulatory issues in Europe.  
To use BNFCR futures, you will have to have the following combination of settings:

``` jsonc
{
    // ...
    "trading_mode": "futures",
    "margin_mode": "cross",
    "proxy_coin": "BNFCR",
    "stake_currency": "USDT" // or "USDC"
    // ...
}
```

The `stake_currency` setting defines the markets the bot will be operating in. This choice is really arbitrary.

On the exchange, you'll have to use "Multi-asset Mode" - and "Position Mode set to "One-way Mode".  
Freqtrade will check these settings on startup, but won't attempt to change them.


!!! Warning
    Please make sure to fully understand the impacts of these settings before modifying them.
