# Api Binance Manager
libs
```py
import hmac
import time
import hashlib
import requests
from urllib.parse import urlencode
```
API
```py
# Clés API
KEY = ""
SECRET = ""
```
compte réel ou test
```py
# URL Binance
BASE_URL = "https://api.binance.com" #Binance
BASE_URL = "https://testnet.binance.vision" #Test
```
pour synchro le time entre Biannce et votre machine
```py
# Récupérer le temps du serveur Binance
def get_binance_server_time():
    response = requests.get(BASE_URL + "/api/v3/time")
    server_time = response.json()["serverTime"]
    local_time = int(time.time() * 1000)
    print(f"Local time: {local_time}, Binance server time: {server_time}")
    print(f"Time difference: {server_time - local_time} ms")
    return server_time
```
requête cryptée
```py
# Générer une signature HMAC-SHA256
def hashing(query_string):
    return hmac.new(SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
```
sécurisé la clé api lors de la requête
```py
# Créer une session avec les headers
session = requests.Session()
session.headers.update({"Content-Type": "application/json", "X-MBX-APIKEY": KEY})
```
envoie de la requête
```py
# Fonction pour envoyer une requête signée
def send_signed_request(http_method, url_path, payload={}):
    payload["timestamp"] = get_binance_server_time()  # Synchronisation avec Binance
    payload["recvWindow"] = 5000  # Augmenter la fenêtre de réception
    query_string = urlencode(sorted(payload.items()))  # Trier les paramètres
    signature = hashing(query_string)  # Générer la signature
    url = f"{BASE_URL}{url_path}?{query_string}&signature={signature}"
    
    print(f"{http_method} {url}")  # Debugging
    
    response = session.request(http_method, url)
    
    if response.status_code == 200:
        return response.json()
    else:
        print("Error:", response.json())  # Debug
        return response.json()
```
test signature
```py
# Fonction pour envoyer une requête publique (sans signature)
def send_public_request(url_path, payload={}):
    query_string = urlencode(payload)
    url = f"{BASE_URL}{url_path}"
    if query_string:
        url += f"?{query_string}"
    
    print("GET", url)  # Debugging
    response = session.get(url)
    return response.json()
```
check 
```py
# Vérifier la synchronisation avec Binance
get_binance_server_time()
```
donne info compte
```py
# Récupérer les informations du compte
response = send_signed_request("GET", "/api/v3/account")
print(response)
```
récupérer la balance du compte
```py

# Afficher uniquement les balances non nulles
if "balances" in response:
    balances = response["balances"]
    for asset in balances:
        if float(asset["free"]) > 0 or float(asset["locked"]) > 0:
            print(f"{asset['asset']}: {asset['free']} (free), {asset['locked']} (locked)")
else:
    print("Erreur : Impossible de récupérer les balances.")
```
## Ordre du marché Api Binance Manager
achat
```py
def BUYs():
    global last_buy_price
    amount = (get_USDT_balance() - (get_USDT_balance() * 0.00075) - 0.00009)
    precision = 4
    amt_str = "{:0.0{}f}".format(amount, precision)
    # Passer un ordre d'achat (market)
    buy_params = {
        "symbol": "BTCFDUSD",
        "side": "BUY",
        "type": "MARKET",
        "quantity": amt_str,
    }
    buy_response = send_signed_request("POST", "/api/v3/order", buy_params)
    last_buy_price = get_price('BTCFDUSD')
    print("Buy order response:", buy_response)
    
```
vente
```py
# Passer un ordre de vente (market)
sell_params = {
    "symbol": "BTCUSDT",
    "side": "SELL",
    "type": "MARKET",
    "quantity": 0.0001,
}
sell_response = send_signed_request("POST", "/api/v3/order", sell_params)
   print("Sell order response:", sell_response)
```
vente limit
```py
def SELLs():
    c = last_buy_price
    amount = (get_btc_balance()-0.000009)
    precision = 5
    precisions = 2
    qtt  = c * 1.00175
    # Formater la quantité à vendre avec la précision correcte
    amt_str = "{:0.0{}f}".format(amount, precision)
    print(amt_str)
    amt_strs = "{:0.0{}f}".format(qtt, precisions)
    # Vérification de la balance avant de passer un ordre
    if amount <= 0:
        print("❌ Solde insuffisant pour effectuer la vente.")
        return

    # Passer un ordre de vente (limit)
    sell_params = {
        "symbol": "BTCFDUSD",  # Utilisation de la paire BTCFDUSD
        "side": "SELL",
        "type": "LIMIT",
        "quantity": amt_str,
        "price": amt_strs,  # Exemple : vente à 0.175% au-dessus du prix actuel
        "timeInForce": "GTC"  # Ordre valide jusqu'à annulation
    }

    # Envoi de la demande de création de l'ordre de vente
    sell_response = send_signed_request("POST", "/api/v3/order", sell_params)
    print("Sell order response:", sell_response)
```
