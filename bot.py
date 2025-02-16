
import time
import sqlite3
import pandas as pd
from binance.client import Client
from database import init_db, save_candle
from indicators import calculate_indicators
from strategy import check_signal
from telegram_bot import send_telegram_message  # 🔥 Import du module Telegram
import hmac
import time
import hashlib
import requests
from urllib.parse import urlencode
import requests
from binance.client import Client

API_KEY = ""
API_SECRET = ""
# Clés API
KEY = ""
SECRET = ""
client = Client(API_KEY, API_SECRET)
SYMBOL = "BTCUSDT"
INTERVAL = Client.KLINE_INTERVAL_1MINUTE
# URL Binance
#BASE_URL = "https://api.binance.com"
BASE_URL = "https://testnet.binance.vision"


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

import sqlite3
import pandas as pd

DB_FILE = "C:\\TRADE_BOT\\trading_data.db"

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
            klines = client.get_historical_klines(SYMBOL, INTERVAL, "1 Feb, 2025")
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

# Fonction pour récupérer les données de la base de données SQLite
def backtest():
    df = get_historical_data()  # Récupère toutes les bougies historiques

    balance_usdt = 1000
    balance_btc = 0
    history = []

    # Parcourir toutes les bougies de l'historique
    for i in range(1, len(df)):  # On commence à 1 pour avoir i-1
        last_row = df.iloc[i - 1]
        current_row = df.iloc[i]

        # Détermination du signal
        signal = None  
        
        # Récupérer le prix actuel (par exemple, le prix de clôture)
        current_price = current_row['close']
    
    
        # Signal d'achat basé sur RSI(6), RSI(12), RSI(24) et croisement de TEMA(7), TEMA(25), TEMA(99)
        if (last_row['TEMA20'] < last_row['TEMA50'] ):
            signal = "BUY"
            #print(f"Achat exécuté à {current_price}")
            
    
        # Signal de vente basé sur RSI(6), RSI(12), RSI(24) et croisement de TEMA(7), TEMA(25), TEMA(99)
        if (last_row['TEMA20'] > last_row['TEMA50']  ):
            # Vérifier que le prix actuel est supérieur au dernier prix d'achat
            signal = "SELL"
            #print(f"Vente exécutée à {current_price}")

        if signal is None:
            continue
        timestamp = current_row['time']

        # Achat si le signal est "BUY"
        if signal == "BUY" and balance_usdt > 100 :
            amount_to_buy = balance_usdt / current_price
            balance_btc = amount_to_buy
            balance_usdt = 0
            history.append(f"{timestamp} - BUY at {current_price} BTC")
            #print(df.iloc[i - 1 : i + 1])  # Afficher les 2 dernières lignes 

        # Vente si le signal est "SELL"
        if signal == "SELL" and balance_btc > 0.0001 :
            amount_to_sell = balance_btc * current_price
            balance_usdt = amount_to_sell
            balance_btc = 0
            history.append(f"{timestamp} - SELL at {current_price} BTC")
            #print(df.iloc[i - 1 : i + 1])  # Afficher les 2 dernières lignes 

        #print(f"{timestamp} | USDT: {balance_usdt:.2f}, BTC: {balance_btc:.6f}, Buy Price: {buy_price if buy_price is not None else 'N/A'}, Sell Price: {sell_price if sell_price is not None else 'N/A'}, Signal: {signal}")

    print("\nBacktest terminé")
    print(f"Solde final USDT: {balance_usdt:.2f}, Solde final BTC: {balance_btc:.6f}")
    #print("Historique des transactions:")
    #for transaction in history:
        #print(transaction)

def execute_trade(action, data):
    balance_usdt = get_USDT_balance()
    balance_btc = get_btc_balance()
    # Appel de la fonction selon l'action
    if action == "BUY" and balance_usdt >= 10:
        BUYs()
        """Exécute une action d'achat ou de vente et envoie à Telegram."""
        message = f"🔥 *SIGNAL DÉTECTÉ* : {action} 📢\n" \
            f"📅 *Temps* : {data['time']}\n" \
              f"💰 *Prix* : {data['close']:.2f}\n" \
              f"📈 *RSI14* : {data['RSI14']:.2f}\n" \
              f"📈 *RSI50* : {data['RSI50']:.2f}\n" \
              f"📊 *TEMA20* : {data['TEMA20']:.2f}\n" \
              f"📊 *TEMA50* : {data['TEMA50']:.2f}\n" \
              f"💲 *FAUX Solde USDT* : {get_USDT_balance()}\n"  \
              f"🪙 *FAUX Solde BTC* : {get_btc_balance()}"
    
        print(message)  # Affichage en console
        send_telegram_message(message)  # 🔥 Envoi sur Telegram
    # Appel de la fonction selon l'action
    elif action == "SELL"and balance_btc >= 0.0001:
        SELLs()
        """Exécute une action d'achat ou de vente et envoie à Telegram."""
        message = f"🔥 *SIGNAL DÉTECTÉ* : {action} 📢\n" \
              f"📅 *Temps* : {data['time']}\n" \
              f"💰 *Prix* : {data['close']:.2f}\n" \
              f"📈 *RSI14* : {data['RSI14']:.2f}\n" \
              f"📈 *RSI50* : {data['RSI50']:.2f}\n" \
              f"📊 *TEMA20* : {data['TEMA20']:.2f}\n" \
              f"📊 *TEMA50* : {data['TEMA50']:.2f}\n" \
              f"💲 *FAUX Solde USDT* : {get_USDT_balance()}\n"  \
              f"🪙 *FAUX Solde BTC* : {get_btc_balance()}"
    
        print(message)  # Affichage en console
        send_telegram_message(message)  # 🔥 Envoi sur Telegram

    # Appel de la fonction selon l'action

def run_bot():
    """Boucle principale du bot, détecte les signaux UNIQUEMENT en live."""
    init_db()
    # Charger l'historique sans signal

    backtest()
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
            if 'RSI14' and 'close' and 'RSI50' in last_data:
                telegram_message = f"📊 *Mise à jour LIVE TEST* 📅 {last_data['time']}\n" \
                       f"💰 *Prix* : {last_data['close']:.2f}\n" \
                       f"📈 *RSI14* : {last_data['RSI14']:.2f}\n" \
                       f"📈 *RSI50* : {last_data['RSI50']:.2f}\n" \
                       f"📊 *TEMA20* : {last_data['TEMA20']:.2f}\n" \
                       f"📊 *TEMA50* : {last_data['TEMA50']:.2f}\n" \
                       f"💲 *FAUX Solde USDT* : {get_USDT_balance()}\n"  \
                       f"🪙 *FAUX Solde BTC* : {get_btc_balance()}"
                print(telegram_message)  # Affichage en console
                send_telegram_message(telegram_message)
            else:
                print("⚠️ Colonnes RSI manquantes ou incorrectes.")


            if live_mode:  # Ne détecter les signaux qu'en live
                check_signal(df, execute_trade)
            else:
                live_mode = True  # Activer la détection de signaux pour la prochaine itération

            time.sleep(60)  # Attendre 1 minute avant la prochaine itération

        except Exception as e:
            print(f"⚠️ Erreur : {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_bot()
