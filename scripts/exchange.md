# Notes spécifique Binance Exchange

Cette page regroupe les problèmes courants et les informations qui sont spécifiques à Binance Exchange.
info API [Notes spécifique API](api.md) .
## Exchange configuration

IA TRADE BOT est basée sur [Python Binance library](https://python-binance.readthedocs.io/en/latest/binance.html)  100 cryptocurrency
exchange markets and trading API.


### Sample exchange configuration

exchange configuration  "binance" (geoTime: Evere) :

```py
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

## Binance

!!! Avertissement "Restrictions de localisation du serveur et géo-ip"
    Veuillez noter que Binance restreint l'accès à l'API en fonction du pays du serveur. Les pays actuellement bloqués, bien que non exhaustifs, sont le Canada, la Malaisie, les Pays-Bas et les États-Unis. Veuillez consulter les [binance terms](https://www.binance.com/en/terms) pour obtenir la liste à jour.



### Binance Blacklist recommendation

Pour Binance, il est recommandé d'ajouter  `"BNB/<STAKE>"` à votre liste noire afin d'éviter des problèmes, sauf si vous êtes prêt à maintenir une quantité suffisante de `BNB` sur le compte ou si vous êtes prêt à désactiver l'utilisation de `BNB` pour les frais.
Les comptes Binance peuvent utiliser le `BNB` pour payer les frais, et si un trade utilise du`BNB`, d'autres trades pourraient consommer cette position et rendre l'achat initial de BNB impossible à vendre, car la quantité attendue ne serait plus disponible.

Si le montant de `BNB` disponible est insuffisant pour couvrir les frais de transaction, les frais ne seront pas couverts par le `BNB` t aucune réduction de frais n'aura lieu. Freqtrade n'achètera jamais de BNB pour couvrir les frais. Le BNB doit être acheté et surveillé manuellement à cette fin.

### Binance sites

utilisez le .com.

* [binance.com](https://www.binance.com/) - International users. Use exchange id: `binance`.

### Binance RSA keys

IA TRADE BOT not yet supports binance RSA API keys.

We recommend to use them as environment variable.


### Binance Futures

Binance a des (malheureusement complexes) [règles spécifiques de trading quantitatif sur les futures](https://www.binance.com/en/support/faq/4f462ebe6ff445d4a170be7d9e897272) qui doivent être respectées, et qui interdisent, entre autres, un montant de position trop faible pour trop de commandes.
Le non-respect de ces règles entraînera une restriction de trading.

dm moi pour plus d'infos.




!!! Warning
    Veuillez vous assurer de bien comprendre les impacts de ces paramètres avant de les modifier, ou de mettre une api réel en non Test Binance.
