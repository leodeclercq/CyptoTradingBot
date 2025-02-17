# Notes spécifique Binance Exchange

Cette page regroupe les problèmes courants et les informations qui sont spécifiques à Binance Exchange.

## Exchange configuration

IA TRADE BOT est basée sur [Python Binance library](https://python-binance.readthedocs.io/en/latest/binance.html)  100 cryptocurrency
exchange markets and trading API. The complete up-to-date list can be found in the
[CCXT repo homepage](https://github.com/ccxt/ccxt/tree/master/python).
However, the bot was tested by the development team with only a few exchanges.
A current list of these can be found in the "Home" section of this documentation.

Feel free to test other exchanges and submit your feedback or PR to improve the bot or confirm exchanges that work flawlessly..

Some exchanges require special configuration, which can be found below.

### Sample exchange configuration

A exchange configuration for "binance" would look as follows:

```json
def get_binance_server_time():
    response = requests.get(BASE_URL + "/api/v3/time")
    server_time = response.json()["serverTime"]
    local_time = int(time.time() * 1000)
    print(f"Local time: {local_time}, Binance server time: {server_time}")
    print(f"Time difference: {server_time - local_time} ms")
    return server_time

# Générer une signature HMAC-SHA256
def hashing(query_string):
    return hmac.new(SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()

# Créer une session avec les headers
session = requests.Session()
session.headers.update({"Content-Type": "application/json", "X-MBX-APIKEY": KEY})

# Fonction pour envoyer une requête signée
def send_signed_request(http_method, url_path, payload={}):
    payload["timestamp"] = get_binance_server_time()  # Synchronisation avec Binance
    payload["recvWindow"] = 5000  # Augmenter la fenêtre de réception
    query_string = urlencode(sorted(payload.items()))  # Trier les paramètres
    signature = hashing(query_string)  # Générer la signature
    url = f"{BASE_URL}{url_path}?{query_string}&signature={signature}"
    
    #print(f"{http_method} {url}")  # Debugging
    
    response = session.request(http_method, url)
    
    if response.status_code == 200:
        return response.json()
    else:
        #print("Error:", response.json())  # Debug
        return response.json()

# Fonction pour envoyer une requête publique (sans signature)
def send_public_request(url_path, payload={}):
    query_string = urlencode(payload)
    url = f"{BASE_URL}{url_path}"
    if query_string:
        url += f"?{query_string}"
    
    #print("GET", url)  # Debugging
    response = session.get(url)
    return response.json()

# Vérifier la synchronisation avec Binance
get_binance_server_time()

# Récupérer les informations du compte
response = send_signed_request("GET", "/api/v3/account")

print(response)

def get_btc_balance():
    account_info = send_signed_request("GET", "/api/v3/account")
     #print("Réponse de Binance:", account_info)  # 🔥 Debug
    
    if "balances" not in account_info:
        print("⚠️ Erreur: 'balances' n'existe pas dans la réponse !")
        return 0.0  # Retourne 0 pour éviter le crash

    for balance in account_info["balances"]:
        if balance["asset"] == "BTC":
            return float(balance["free"])
    return 0.0


btc_balance = get_btc_balance()
print(f"Solde BTC disponible : {btc_balance}")

def get_USDT_balance():
    account_info = send_signed_request("GET", "/api/v3/account")
    for balance in account_info["balances"]:
        if balance["asset"] == "USDT":
            return float(balance["free"])
    return 0.0

USDT_balance = get_USDT_balance()
print(f"Solde USDT disponible : {USDT_balance}")


def get_price(symbol):
    """Récupère le prix actuel du marché pour un symbole donné."""
    response = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}")
    return float(response.json()["price"])
price = get_price("BTCUSDT")

print(f"Le prix actuel du BTC en USDT est de {price}")



def BUYs():
    USDT_balance = get_USDT_balance()
    a = round(USDT_balance * 0.9, 4)
    b = round(a / price, 4)
    print(b)
    # Passer un ordre d'achat (market)
    buy_params = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "MARKET",
        "quantity": b,
    }
    buy_response = send_signed_request("POST", "/api/v3/order", buy_params)
    print("Buy order response:", buy_response)

def SELLs():
    btc_balance = get_btc_balance()
    # Passer un ordre de vente (market)
    sell_params = {
        "symbol": "BTCUSDT",
        "side": "SELL",
        "type": "MARKET",
        "quantity": btc_balance,
    }
    sell_response = send_signed_request("POST", "/api/v3/order", sell_params)
    print("Sell order response:", sell_response)
    
# Afficher uniquement les balances non nulles
def Get_balance_utile():
    if "balances" in response:
        balances = response["balances"]
        for asset in balances:
            if float(asset["free"]) > 0 or float(asset["locked"]) > 0:
                print(f"{asset['asset']}: {asset['free']} (free), {asset['locked']} (locked)")
    else:
        print("Erreur : Impossible de récupérer les balances.")
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

ATTENTION pour ne pas se faire ban de Binance pour maker limit.
`"rateLimit": 3100` 3.1s entre chaque call.

!!! Note
    je n'ai pas encore codé pour être Maker et faire des ordre Limite.
 `"rateLimit"`  step by step.

## Binance

!!! Avertissement "Restrictions de localisation du serveur et géo-ip"
    Veuillez noter que Binance restreint l'accès à l'API en fonction du pays du serveur. Les pays actuellement bloqués, bien que non exhaustifs, sont le Canada, la Malaisie, les Pays-Bas et les États-Unis. Veuillez consulter les [binance terms > b. Eligibility](https://www.binance.com/en/terms) pour obtenir la liste à jour.

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
