# Api Binance Manager

'''py
import hmac
import time
import hashlib
import requests
from urllib.parse import urlencode

# Clés API
KEY = ""
SECRET = ""

# URL Binance
BASE_URL = "https://api.binance.com"

# Récupérer le temps du serveur Binance
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
    
    print(f"{http_method} {url}")  # Debugging
    
    response = session.request(http_method, url)
    
    if response.status_code == 200:
        return response.json()
    else:
        print("Error:", response.json())  # Debug
        return response.json()

# Fonction pour envoyer une requête publique (sans signature)
def send_public_request(url_path, payload={}):
    query_string = urlencode(payload)
    url = f"{BASE_URL}{url_path}"
    if query_string:
        url += f"?{query_string}"
    
    print("GET", url)  # Debugging
    response = session.get(url)
    return response.json()

# Vérifier la synchronisation avec Binance
get_binance_server_time()

# Récupérer les informations du compte
response = send_signed_request("GET", "/api/v3/account")
print(response)


# Afficher uniquement les balances non nulles
if "balances" in response:
    balances = response["balances"]
    for asset in balances:
        if float(asset["free"]) > 0 or float(asset["locked"]) > 0:
            print(f"{asset['asset']}: {asset['free']} (free), {asset['locked']} (locked)")
else:
    print("Erreur : Impossible de récupérer les balances.")
'''
## Ordre du marché Api Binance Manager
'''py
# Passer un ordre d'achat (market)
buy_params = {
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "MARKET",
    "quantity": 0.0001,
}
buy_response = send_signed_request("POST", "/api/v3/order", buy_params)
print("Buy order response:", buy_response)

# Passer un ordre de vente (market)
sell_params = {
    "symbol": "BTCUSDT",
    "side": "SELL",
    "type": "MARKET",
    "quantity": 0.0001,
}
sell_response = send_signed_request("POST", "/api/v3/order", sell_params)
   print("Sell order response:", sell_response)
'''
