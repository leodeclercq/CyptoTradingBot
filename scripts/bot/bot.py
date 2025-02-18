import sqlite3
import pandas as pd
from binance.client import Client
from database import init_db, save_candle
from indicators import calculate_indicators
from strategy import check_signal
from telegram_bot import send_telegram_message  # 🔥 Import du module Telegram
import hmac
from datetime import datetime, timedelta
import time
import hashlib
import requests
from urllib.parse import urlencode
import requests
from decimal import Decimal, ROUND_FLOOR
import math

DB_FILE = ""

API_KEY = ""
API_SECRET = ""

client = Client(API_KEY, API_SECRET)
SYMBOL = "BTCFDUSD"
INTERVAL = Client.KLINE_INTERVAL_1SECOND

# URL Binance
BASE_URL = "https://api.binance.com"
#BASE_URL = "https://testnet.binance.vision"

order_id = 0

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
    return hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()

# Créer une session avec les headers
session = requests.Session()
session.headers.update({"Content-Type": "application/json", "X-MBX-APIKEY": API_KEY})

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
        if balance["asset"] == "FDUSD":
            return float(balance["free"])
    return 0.0

USDT_balance = get_USDT_balance()
print(f"Solde FDUSD disponible : {USDT_balance}")


def get_price(symbol):
    """Récupère le prix actuel du marché pour un symbole donné."""
    response = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}")
    return float(response.json()["price"])
price = get_price("BTCFDUSD")

print(f"Le prix actuel du BTC en FDUSD est de {price}")

last_buy_price = get_price("BTCFDUSD")# ou comme vous le souhaitez ou vous pouver directement passer depuis binance par vous même un ordre limit de vente si vous n'avez que des BTC
def BUYs():
    global last_buy_price
    amount = (get_USDT_balance() - (get_USDT_balance() * 0.00075) - 0.000009)
    precision = 5
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

    
def check_order_status(df):
    global order_id
    """
    Récupère la liste des ordres ouverts pour un symbole donné.
    """
    params = {
        "symbol": "BTCFDUSD"
    }
    response = send_signed_request("GET", "/api/v3/openOrders", params)

    if response and isinstance(response, list):
        if len(response) == 0:
            print(f"🔴 Aucun ordre ouvert pour {"BTCFDUSD"}.")
            check_signal(df, execute_trade)
        else:
            print(f"🟢 Ordres ouverts pour {"BTCFDUSD"}:")
            for order in response:
                print(f"Order ID: {order['orderId']}, Price: {order['price']}, Quantity: {order['origQty']}, Status: {order['status']}")
                if  order['status'] and order['status'] == "NEW":
                    print(f"📊 Statut de l'ordre {order_id}: {order['status']}")
                    print(f"✅ Ordre ouvert à {order['price']}, attente.... {get_price("BTCFDUSD")}")
                elif  order['status'] and order['status'] == "FILLED":
                    print(f"✅ Ordre exécuté à {order['price']}, déclenchement de la vente.")
    else:
        print("⚠️ analyse d'achat...")
        check_signal(df, execute_trade)
# Afficher uniquement les balances non nulles
        
def Get_balance_utile():
    if "balances" in response:
        balances = response["balances"]
        for asset in balances:
            if float(asset["free"]) > 0 or float(asset["locked"]) > 0:
                print(f"{asset['asset']}: {asset['free']} (free), {asset['locked']} (locked)")
    else:
        print("Erreur : Impossible de récupérer les balances.")


def get_historical_data():
    
    """Vérifie si les données historiques existent déjà, sinon les récupère depuis Binance."""
    print("🔄 Vérification des données historiques...")

    # Connexion à la base de données
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Vérifier si la table 'market_data' existe et contient des données
        cursor.execute("SELECT COUNT(*) FROM market_data")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("📚 Données historiques trouvées dans la base de données. Chargement...")
            # Charger les données existantes
            df = pd.read_sql_query("SELECT * FROM market_data", conn)
            df['time'] = pd.to_datetime(df['time']).astype(str)
        else:
            print("⚠️ Aucune donnée historique trouvée. Récupération des données depuis Binance...")
            # Récupérer les données historiques depuis Binance si elles n'existent pas
            # Calcul du timestamp de la dernière heure
            end_time = int(time.time() * 1000)  # Timestamp actuel en ms
            start_time = end_time - (60 * 60 * 1000)  # 1 heure en arrière
            klines = client.get_historical_klines(SYMBOL, INTERVAL, start_time)
            df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                            'quote_asset_volume', 'num_trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'])
            
            df = df[['time', 'open', 'high', 'low', 'close']].astype(float)
            df['time'] = pd.to_datetime(df['time'], unit='ms').astype(str)

            # Calculer les indicateurs et sauvegarder dans la base de données
            df = calculate_indicators(df)

            # Sauvegarder les nouvelles bougies dans la table 'market_data'
            for _, row in df.iterrows():
                save_candle(tuple(row))  # Sauvegarde dans la base

            print("✅ Historique récupéré et sauvegardé dans la base de données.")
    
    return df



def execute_trade(action, data):
    balance_usdt = get_USDT_balance()
    balance_btc = get_btc_balance()
    # Appel de la fonction selon l'action
    if action == "BUY" and balance_usdt >= 7.000001:
        BUYs()
        """Exécute une action d'achat ou de vente et envoie à Telegram."""
        
        message = f"🔥 *SIGNAL DÉTECTÉ* : {action} 📢\n" \
            f"📅 *Temps* : {data['time']}\n" \
              f"💰 *Prix* : {data['close']:.2f}\n" \
              f"💰 *Last Buy Price* : {last_buy_price:.2f}\n" \
              f"📈 *pente* : {data['slope']:.2f}\n" \
              f"📊 *TEMA20* : {data['TEMA20']:.2f}\n" \
              f"📊 *TEMA50* : {data['TEMA50']:.2f}\n" \
              f"💲 *FAUX Solde FDUSD* : {balance_usdt}\n"  \
              f"🪙 *FAUX Solde BTC* : {balance_btc}"
    
        print(message)  # Affichage en console
        send_telegram_message(message)  # 🔥 Envoi sur Telegram
        SELLs()
    else:
        SELLs()
def run_bot():
    print(get_USDT_balance)
    print(get_btc_balance)
    """Boucle principale du bot, détecte les signaux UNIQUEMENT en live."""
    init_db()
    # Charger l'historique sans signal

    get_historical_data()
    print("🟢 Mode LIVE activé : Détection des signaux uniquement en temps réel !")

    send_telegram_message("🚀 *Bot Trading * :  en temps réel sur Binance ₿!")

    live_mode = False  # Activer la détection des signaux seulement après le premier live tick

    while True:
        try:
            candles = client.get_klines(symbol=SYMBOL, interval=INTERVAL, limit=99)
            df = pd.DataFrame(candles, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                                'quote_asset_volume', 'num_trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'])

            df = df[['time', 'open', 'high', 'low', 'close']].astype(float)
            df['time'] = pd.to_datetime(df['time'], unit='ms').astype(str)

            df = calculate_indicators(df)
            print(df.head())        

            save_candle(tuple(df.iloc[-1]))


            # 🔥 Affichage du dernier DataFrame en live
            print("\n🟢 Dernières données LIVE :")
            print(df.tail(5))

            # 🔥 Envoi du dernier DataFrame à Telegram (optionnel)
            last_data = df.iloc[-1]
            print(df.columns)  # Ajoute cette ligne juste avant l'envoi de la mise à jour à Telegram
            if 'close' and 'slope' and 'TEMA20' and 'TEMA50' in last_data:
                telegram_message = f"📊 *Mise à jour LIVE* 📅 {last_data['time']}\n" \
                       f"💰 *Prix* : {last_data['close']:.2f}\n" \
                       f"📈 *slope* : {last_data['slope']:.2f}\n" \
                       f"📊 *TEMA20* : {last_data['TEMA20']:.2f}\n" \
                       f"📊 *TEMA50* : {last_data['TEMA50']:.2f}\n" \
                       f"💲 *Solde FDUSD* : {get_USDT_balance()}\n"  \
                       f"🪙 *Solde BTC* : {get_btc_balance()}"
                print(telegram_message)  # Affichage en console
                #send_telegram_message(telegram_message)
            else:
                print("⚠️ Colonnes RSI manquantes ou incorrectes.")


            if live_mode:  # Ne détecter les signaux qu'en live
                check_order_status(df)
                
            else:
                live_mode = True  # Activer la détection de signaux pour la prochaine itération

            time.sleep(1)  # Attendre 1 minute avant la prochaine itération

        except Exception as e:
            print(f"⚠️ Erreur : {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
