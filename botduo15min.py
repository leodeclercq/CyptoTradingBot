import sqlite3
import pandas as pd
import hmac
import time
import hashlib
import requests
from urllib.parse import urlencode
from binance.client import Client
import threading
from collections import deque
from datetime import datetime
import numpy as np
import talib
API_KEY = ""
API_SECRET = ""

#BASE_URL = "https://api.binance.com"
#BASE_URL = "https://testnet.binance.vision"
client = Client(API_KEY, API_SECRET)
INTERVAL = Client.KLINE_INTERVAL_15MINUTE
seuil_acceleration = 50  # Minimum d'augmentation nécessaire
seuil_deceleration = -100  # Si la pente chute trop avant croisement, on annule
previous_signal = None
signal_detected = False
signal = None
position_signal = None
position_signals = None
close_window_s = deque(maxlen=150)
time_window_s = deque(maxlen=150)
tema20_window_s = deque(maxlen=10)
tema50_window_s = deque(maxlen=10)
slope20_window_s = deque(maxlen=10)
slope50_window_s = deque(maxlen=10)
last_buy_price_window = deque(maxlen=20)
fdusd = 0.0# même que votre balance divisé par 2
btc = 0.000060# même que votre balance divisé par 2
initial_display_done = False
initial_buy = False
initial_sell = False
initiate = False
def send_signal(signal):
    with open('signal.txt', 'w') as file:
        file.write(signal)
def get_binance_server_time():
    response = requests.get(BASE_URL + "/api/v3/time")
    server_time = response.json()["serverTime"]
    local_time = int(time.time() * 1000)
    #print(f"Local time: {local_time}, Binance server time: {server_time}")
    #print(f"Time difference: {server_time - local_time} ms")
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
def get_BTC_balance():
    account_info = send_signed_request("GET", "/api/v3/account")
    #print("Réponse de Binance:", account_info)  # 🔥 Debug
    if "balances" not in account_info:
        #print("⚠️ Erreur: 'balances' n'existe pas dans la réponse !")
        return 0.0  # Retourne 0 pour éviter le crash
    for balance in account_info["balances"]:
        if balance["asset"] == "BTC":
            return float(balance["free"])
    return 0.0
def get_FDUSD_balance():
    account_info = send_signed_request("GET", "/api/v3/account")
    for balance in account_info["balances"]:
        if balance["asset"] == "FDUSD":
            return float(balance["free"])
    return 0.0
def get_price(symbol):
    """Récupère le prix actuel du marché pour un symbole donné."""
    response = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}")
    return float(response.json()["price"])
btc_balance = get_BTC_balance()
print(f"Solde BTC disponible : {btc_balance}")
fdusd_balance = get_FDUSD_balance()
print(f"Solde FDUSD disponible : {fdusd_balance}")
price = get_price("BTCFDUSD")
print(f"Le prix actuel du BTC en FDUSD est de {price}")
#last_buy_price = get_price("BTCFDUSD")
#last_buy_price_window.append(last_buy_price)
#last_buym = last_buy_price
#print(last_buy_price)
def compute_TEMA(data, period):
    if len(data) < period:
        print(f"Pas assez de données pour calculer TEMA (besoin de {period} points)")
        return None
    np_data = np.array(data, dtype=float)
    tema = talib.TEMA(np_data, timeperiod=period)
    return tema[-1]
# Calcul de la pente sur les 'window' derniers points par régression linéaire.
def compute_slope(data, window=2):
    if len(data) < window:
        return None
    y = np.array(data[-window:], dtype=float)
    x = np.arange(window)
    slope, _ = np.polyfit(x, y, 1)
    return slope

def get_historical_data():
    global close_window_s, tema20_window_s, tema50_window_s, slope20_window_s, slope50_window_s
    
    # Récupérer les dernières bougies historiques
    klines = client.get_klines(symbol='BTCFDUSD', interval=INTERVAL, limit=150)
    
    # Initialiser les données avec les bougies récupérées
    initial_data = [float(kline[4]) for kline in klines]  # Utilisation des prix de clôture
    
    # Remplir les fenêtres avec les données historiques
    close_window_s.extend(initial_data)
    
    for price in initial_data:
        tema20s = compute_TEMA(list(close_window_s), period=20)
        tema20_window_s.append(tema20s)
        
        tema50s = compute_TEMA(list(close_window_s), period=50)
        tema50_window_s.append(tema50s)
        
        if len(tema20_window_s) > 2 and len(tema50_window_s) > 2:
            slope20s = compute_slope(list(tema20_window_s))
            slope20_window_s.append(slope20s)
            
            slope50s = compute_slope(list(tema50_window_s))
            slope50_window_s.append(slope50s)
#38330
btcacquis = 0.00006# dépend pour nombre et % de mise
def ORDER(side):
    # Passer un ordre d'achat (market)
    precision = 5
    amt_str = "{:0.0{}f}".format(btcacquis, precision)
    buy_params = {
        "symbol": "BTCFDUSD",
        "side": side,
        "type": "MARKET",
        "quantity": amt_str,
    }
    buy_response = send_signed_request("POST", "/api/v3/order", buy_params)
    print("Buy order response:", buy_response)
# Fonction pour récupérer et traiter les nouvelles bougies
vente = btcacquis*0.99925
achat = btcacquis*1.00075
fdusddepenses = 1000
seuil15 = 1.00333
seuil1 = 1.0015
def handle_new_candle_s():
    global fdusd_balance, btc_balance, last_buy_price, initial_display_done, initial_buy, initial_sell, btc, fdusd, previous_signal, signal,position_signal,signal_detected,position_signals, btcacquis, initiate
    # Récupérer la dernière bougiem
    klines = client.get_klines(symbol='BTCFDUSD', interval=INTERVAL, limit=1)
    # Obtenir la clôture de la dernière bougie
    close_price = float(klines[0][4])  # 4 = Close price
    close_window_s.append(close_price)
    print(f"🕒 Bougie clôturée, prix: {close_price:.2f}")
    # Calculer les indicateurs TEMA
    tema20s = compute_TEMA(list(close_window_s), period=20)
    tema20_window_s.append(tema20s)
    tema50s = compute_TEMA(list(close_window_s), period=50)
    tema50_window_s.append(tema50s)
    if len(tema20_window_s) > 2 and len(tema50_window_s) > 2:
        slope20s = compute_slope(list(tema20_window_s))
        slope20_window_s.append(slope20s)
        slope50s = compute_slope(list(tema50_window_s))
        slope50_window_s.append(slope50s)
        # Affichage de l'état initial uniquement la première fois
        if not initial_display_done:
            print(f"🔄 État Initial - 📉 Dernière Bougie: {close_price:.2f} | "
                  f"📈 Pente TEMA20: {slope20s if slope20s is not None else 'N/A'} | "
                  f"📉 Pente TEMA50: {slope50s if slope50s is not None else 'N/A'} | "
                  f"TEMA20: {tema20s:.2f} | TEMA50: {tema50s:.2f}")
            initial_display_done = True
        # Attente de la fin de la bougie actuelle
        current_time = time.time()
        next_candle_time = (current_time // 900 + 1) * 900 # Prochain multiple de 900s (15min)
        sleep_time = next_candle_time - current_time
        print(f"Attente de {sleep_time:.2f} secondes jusqu'à la prochaine clôture de bougie...")
        time.sleep(sleep_time)
        price = get_price('BTCFDUSD')
        btc_balance = get_BTC_balance()
        fdusd_balance = get_FDUSD_balance()
        print(f"SIMU 🪙: {btc:.6f}, 💲 : {fdusd:.6f}")
        if len(slope20_window_s) > 2 and len(slope50_window_s) > 2:
            if signal == "LONG":
                # Vente (si en position et conditions remplies)
                if  tema20s > tema50s  and tema20_window_s[-2] > tema50_window_s[-2] and tema20_window_s[-3] > tema50_window_s[-3] : 
                    if slope20s is not None  and slope20s < 0  and slope20_window_s[-2] > 0  and slope20_window_s[-3] > 0 :
                        if len(last_buy_price_window) >=1:
                            for i in range(len(last_buy_price_window) - 1, -1, -1):
                                if last_buy_price_window[i] * seuil15 < price and btc_balance >= btcacquis and btc >= btcacquis:
                                    fdusd += vente*price  # Conversion de BTC en FDUSD
                                    btc -= btcacquis
                                    ORDER('SELL')
                                    last_buy_price = price
                                    print(f"🔥VENTE à 💰{last_buy_price:.6f}, 🪙: {btc_balance:.6f}, 💲 : {fdusd_balance:.6f}, prix d'achat {last_buy_price_window[i]:.2f}, SINGAL LONG ")
                                    print(f"SIMU 🪙: {btc:.6f}, 💲 : {fdusd:.6f}, 💰{close_price:.6f}")
                                    last_buy_price_window.remove(last_buy_price_window[i])
                                    if last_buy_price not in last_buy_price_window:
                                        last_buy_price_window.append(last_buy_price)
                                        
                                    print(list(last_buy_price_window)[-38:])
                # Achat (si hors position et conditions remplies)
                if tema20s < tema50s and tema20_window_s[-2] < tema50_window_s[-2] and tema20_window_s[-3] < tema50_window_s[-3]:
                    if slope20s is not None and slope50s is not None and slope20s > 0 and slope50s < 0 and slope20_window_s[-2] < 0 and slope50_window_s[-2] < 0 and slope20_window_s[-3] < 0 and slope50_window_s[-3] < 0:
                        if len(last_buy_price_window) >=1:
                            for i in range(len(last_buy_price_window) - 1, -1, -1):
                                if last_buy_price_window[i]> price* seuil15 and fdusd_balance >= achat*price and fdusd >= achat*price:
                                    ORDER('BUY')
                                    btc += btcacquis# Achat du maximum possible
                                    fdusd -=  achat*price
                                    last_buy_price = price  # Enregistrer le prix d'achat
                                    print(f"🔥ACHAT à 💰{last_buy_price:.6f}, 🪙: {btc_balance:.6f}, 💲 : {fdusd_balance:.6f}, SINGAL LONG ")
                                    print(f"SIMU 🪙: {btc:.6f}, 💲 : {fdusd:.6f}, 💰{close_price:.6f}")
                                    if last_buy_price not in last_buy_price_window:
                                        last_buy_price_window.append(last_buy_price)
                                        
                                    print(list(last_buy_price_window)[-38:])
            if signal == "SHORT":
                # Vente (si en position et conditions remplies)
                if  tema20s > tema50s  and tema20_window_s[-2] > tema50_window_s[-2] and tema20_window_s[-3] > tema50_window_s[-3] : 
                    if slope20s is not None  and slope20s < 0  and slope20_window_s[-2] > 0  and slope20_window_s[-3] > 0 :
                        if len(last_buy_price_window) >=1:
                            for i in range(len(last_buy_price_window) - 1, -1, -1):
                                if last_buy_price_window[i] * seuil15 < price and btc_balance >= btcacquis and btc >= btcacquis:
                                    ORDER('SELL')
                                    fdusd += vente*price
                                    btc -= btcacquis
                                    last_buy_price = price
                                    print(f"🔥VENTE à 💰{last_buy_price:.6f}, 🪙: {btc_balance:.6f}, 💲 : {fdusd_balance:.6f},  SIGNAL SHORT")
                                    print(f"SIMU 🪙: {btc:.6f}, 💲 : {fdusd:.6f}, 💰{close_price:.6f}")
                                    if last_buy_price not in last_buy_price_window:
                                        last_buy_price_window.append(last_buy_price)
                                    print(last_buy_price_window[-38:])
                # Achat (si hors position et conditions remplies)
                if tema20s < tema50s and tema20_window_s[-2] < tema50_window_s[-2] and tema20_window_s[-3] < tema50_window_s[-3]:
                    if slope20s is not None and slope50s is not None and slope20s > 0 and slope50s < 0 and slope20_window_s[-2] < 0 and slope50_window_s[-2] < 0 and slope20_window_s[-3] < 0 and slope50_window_s[-3] < 0:
                        if len(last_buy_price_window) >=1:
                            for i in range(len(last_buy_price_window) - 1, -1, -1): 
                                if last_buy_price_window[i]  > price* seuil15 and fdusd_balance >= achat*price and fdusd >= achat*price:
                                    ORDER('BUY')
                                    btc += btcacquis # Achat du maximum possible
                                    fdusd -=  achat*price
                                    last_buy_price = price  # Enregistrer le prix d'achat
                                    print(f"🔥ACHAT à 💰{last_buy_price:.6f}, 🪙: {btc_balance:.6f}, 💲 : {fdusd_balance:.6f}, prix de vente {last_buy_price_window[i]:.2f},SIGNAL SHORT")
                                    print(f"SIMU 🪙: {btc:.6f}, 💲 : {fdusd:.6f}, 💰{close_price:.6f}")
                                    last_buy_price_window.remove(last_buy_price_window[i])
                                    if last_buy_price not in last_buy_price_window:
                                        last_buy_price_window.append(last_buy_price)
                                    print(list(last_buy_price_window)[-38:])

            # Affichage des informations
            candle_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            if tema20s < tema50s:
                print(f" {candle_time} |💚 U (pente TEMA20: {slope20s} ), (pente TEMA50: {slope50s} ) (TEMA20: {f'\033[94m{tema20s:.2f}\033[0m'} < TEMA50: {f'\033[93m{tema50s:.2f}\033[0m'}) 🪙: {btc_balance:.6f}, 💲 : {fdusd_balance:.6f}, 💰: {price:.6f}")
                if (slope20_window_s[-1] - slope20_window_s[-2] < seuil_deceleration) and (slope20_window_s[-1] < slope50_window_s[-1]):
                    if not signal_detected:
                        previous_signal = 'SHORT'
                        print(f"Position Signal: {previous_signal}")
                        signal_detected = True
                    if signal_detected and previous_signal != 'SHORT':
                        signal='SHORT'
                        send_signal(signal)
                        print(f"Position Signal: {signal}")
                        if not initiate:
                            if btc_balance >= btcacquis and btc >= btcacquis:
                                ORDER('SELL')
                                fdusd += vente*price  # Conversion de BTC en FDUSD
                                btc -= btcacquis
                                last_buy_price = price
                                print(f"🔥VENTE à 💰{last_buy_price:.6f}, 🪙: {btc_balance:.6f}, 💲 : {fdusd_balance:.6f},  ENTREE SIGNAL SHORT")
                                print(f"SIMU 🪙: {btc:.6f}, 💲 : {fdusd:.6f}, 💰{close_price:.6f}")
                                if last_buy_price not in last_buy_price_window:
                                    last_buy_price_window.append(last_buy_price)
                                print(list(last_buy_price_window)[-38:])
                                initiate = True
                        if len(last_buy_price_window) >=1:
                            for i in range(len(last_buy_price_window) - 1, -1, -1):
                                    if last_buy_price_window[i] * seuil15 < price and btc_balance >= btcacquis and btc >= btcacquis:
                                        ORDER('SELL')
                                        fdusd += vente*price  # Conversion de BTC en FDUSD
                                        btc -= btcacquis
                                        last_buy_price = price
                                        print(f"🔥VENTE à 💰{last_buy_price:.6f}, 🪙: {btc_balance:.6f}, 💲 : {fdusd_balance:.6f},  {last_buy_price_window[i]} AUTRES SIGNAL SHORT")
                                        print(f"SIMU 🪙: {btc:.6f}, 💲 : {fdusd:.6f}, 💰{close_price:.6f}")
                                        last_buy_price_window.remove(last_buy_price_window[i])
                                        if last_buy_price not in last_buy_price_window:
                                            last_buy_price_window.append(last_buy_price)
                                        print(list(last_buy_price_window)[-38:])
                        previous_signal = 'SHORT'
                        print(f"Position Signal: {previous_signal}")
            else:
                print(f" {candle_time} |❤️ n  (pente TEMA20: {slope20s} ), (pente TEMA50: {slope50s} )( (TEMA20: {f'\033[94m{tema20s:.2f}\033[0m'} >= TEMA50: {f'\033[93m{tema50s:.2f}\033[0m'}) 🪙: {btc_balance:.6f}, 💲 : {fdusd_balance:.6f}, 💰: {price:.6f}")
                if (slope20_window_s[-1] - slope20_window_s[-2] > seuil_acceleration) and (slope20_window_s[-1] > slope50_window_s[-1]):
                    print("🔥 Signal valide : TEMA20 accélère avant croisement")
                    if not signal_detected:
                        previous_signal = 'LONG'
                        print(f"Position Signal: {previous_signal}")
                        signal_detected = True
                    if signal_detected and previous_signal != 'LONG':
                        signal='LONG'
                        send_signal(signal)
                        print(f"Position Signal: {signal}")
                        if not initiate:
                            if fdusd_balance >= achat*price and fdusd >= achat*price:
                                ORDER('BUY')
                                btc += btcacquis # Achat du maximum possible
                                fdusd -=  achat*price
                                last_buy_price = price  # Enregistrer le prix d'achat
                                print(f"🔥ACHAT à 💰{last_buy_price:.6f}, 🪙: {btc_balance:.6f}, 💲 : {fdusd_balance:.6f}, ENTREE SIGNAL LONG ")
                                print(f"SIMU 🪙: {btc:.6f}, 💲 : {fdusd:.6f}, 💰{close_price:.6f}")
                                
                                if last_buy_price not in last_buy_price_window:
                                    last_buy_price_window.append(last_buy_price)
                                    
                                print(list(last_buy_price_window)[-38:])
                                initiate = True
                        if len(last_buy_price_window) >=1:
                            for i in range(len(last_buy_price_window) - 1, -1, -1):
                                    if last_buy_price_window[i]  > price* seuil15 and fdusd_balance >= achat*price and fdusd >= achat*price:
                                        ORDER('BUY')
                                        btc += btcacquis # Achat du maximum possible
                                        fdusd -=  achat*price 
                                        last_buy_price = price  # Enregistrer le prix d'achat
                                        print(f"🔥ACHAT à 💰{last_buy_price:.6f}, 🪙: {btc_balance:.6f}, 💲 : {fdusd_balance:.6f}, {last_buy_price_window[i]}, AUTRES SINGAL LONG ")
                                        print(f"SIMU 🪙: {btc:.6f}, 💲 : {fdusd:.6f}, 💰{close_price:.6f}")
                                        last_buy_price_window.remove(last_buy_price_window[i])
                                        if last_buy_price not in last_buy_price_window:
                                            last_buy_price_window.append(last_buy_price)
                                            
                                        print(list(last_buy_price_window)[-38:])
                        previous_signal = 'LONG'  # Mise à jour du signal précédent# Fonction principale pour démarrer la simulation live
                        print(f"Position Signal: {previous_signal}")
def run_live_simulations():
    # Charger les données historiques au début
    get_historical_data()
    # Commencer à vérifier les nouvelles bougies après avoir chargé les données
    while True:
        try:
            handle_new_candle_s()
        except Exception as e:
            print(f"Erreur lors de la récupération des données: {e}")
            time.sleep(10)  # Attendre un peu avant de réessayer
if __name__ == "__main__":
    run_live_simulations()
