import time
import numpy as np
from collections import deque
from binance.client import Client
import talib

# Paramètres API (REMPLACE PAR TES CLÉS réelles en production !) 
API_KEY = ""
API_SECRET = ""
client = Client(API_KEY, API_SECRET)

# Paramètres globaux
interval = Client.KLINE_INTERVAL_1MINUTE


data_window = deque(maxlen=200)
tema20_window = deque(maxlen=100)
price_window = deque(maxlen=200)

usdt_balance = 1000.0  # Balance initiale en USDT
btc_balance = 0.0  # Balance initiale en BTC

last_buy_price = 0.0

current_position = "none"

pente_vente = -1
pente_achat = 1

slope_window = 3

def compute_TEMA(data, period):
    """Calcule le TEMA sur une fenêtre de données."""
    if len(data) < period:
        return None
    np_data = np.array(data, dtype=float)
    return talib.TEMA(np_data, timeperiod=period)[-1]

def compute_slope(data, window=slope_window):
    """Calcule la pente sur une fenêtre de données donnée."""
    if len(data) <= window:
        return None
    y = np.array(data[-window:], dtype=float)
    x = np.arange(window)
    slope, _ = np.polyfit(x, y, 1)
    return slope

def get_latest_price():
    """Récupère le dernier prix du marché de BTC/USDT."""
    ticker = client.get_symbol_ticker(symbol='BTCUSDT')
    return float(ticker['price'])

def get_latest_closed_candle():
    """Récupère la dernière bougie clôturée et retourne son prix de clôture."""
    klines = client.get_klines(symbol='BTCUSDT', interval=interval, limit=2)
    return float(klines[-2][4])  + 80  # Prend la bougie précédente, car la dernière est encore en formation

def get_5_last_candle(symbol='BTCUSDT', interval='1m'):
    """Récupère les 5 dernières bougies clôturées et retourne leurs prix de clôture."""
    klines = client.get_klines(symbol=symbol, interval=interval, limit=6)  # On prend 6 bougies pour exclure la dernière en formation
    return [float(kline[4]) + 80 for kline in klines[:-1]]  # Exclure la dernière bougie en formation et récupérer les prix de clôture


def fetch_initial_data():
    """Récupère les données initiales de marché."""
    klines = client.get_klines(symbol='BTCUSDT', interval=interval, limit=200)
    return [float(kline[4]) + 80 for kline in klines]

def colorize_slope(slope):
    """Définit la couleur de la pente selon sa valeur."""
    if slope < 0:
        return f'\033[91m{slope:.6f}\033[0m'  # Rouge pour une valeur négative
    elif slope == 0:
        return f'\033[97m{slope:.6f}\033[0m'  # Blanc pour une valeur nulle
    else:
        return f'\033[92m{slope:.6f}\033[0m'  # Vert pour une valeur positive

def livetest():
    """Fonction principale de trading en live."""
    global usdt_balance, btc_balance, last_buy_price, current_position
    
    print("Initialisation des données...")
    initial_data = fetch_initial_data()
    data_window.extend(initial_data)
    
        # Affichage de l'état initial avant de commencer la boucle
    closed_price = get_latest_closed_candle()
    data_window.append(closed_price)
    slope = None   # Initialisation pour éviter l'erreur
    tema20 = None
    tema50 = None
    if len(data_window) >= 150:
        tema20 = compute_TEMA(list(data_window), period=20)
        tema201 = compute_TEMA(list(data_window)[:-1], period=20)
        tema202 = compute_TEMA(list(data_window)[:-2], period=20)
        tema203 = compute_TEMA(list(data_window)[:-3], period=20)
        tema205 = compute_TEMA(list(data_window)[:-4], period=20)
        tema204 = compute_TEMA(list(data_window)[:-5], period=20)
        tema20_window.append(tema205)
        tema20_window.append(tema204)
        tema20_window.append(tema203)
        tema20_window.append(tema202)
        tema20_window.append(tema201)
        tema20_window.append(tema20)
        print(tema20_window)
        tema50 = compute_TEMA(list(data_window), period=50)
        if len(tema20_window) >= 3:
            slope = compute_slope(list(tema20_window), window=slope_window)
    # Affichage de l'état initial avant d'attendre la prochaine bougie
    print(f"🔄 État Initial - 📉 Dernière Bougie: {closed_price:.2f} | "
          f"📈 Pente: {colorize_slope(slope) if slope is not None else 'N/A'} | "
          f"TEMA20: {tema20:.2f} | TEMA50: {tema50:.2f}")


    while True:
        try:
            # Attente de la fin de la bougie actuelle
            current_time = time.time()
            next_candle_time = (current_time // 60 + 1) * 60  # Prochain multiple de 900s (15min)
            sleep_time = next_candle_time - current_time
            print(f"Attente de {sleep_time:.2f} secondes jusqu'à la prochaine clôture de bougie...")
            time.sleep(sleep_time)

            # Récupérer le prix de clôture de la dernière bougie
            closed_price = get_latest_closed_candle()
            data_window.append(closed_price)
            print(f"🕒 Bougie clôturée, prix: {closed_price:.2f}")
            # Si la fenêtre de données contient au moins 151 éléments (pour une analyse complète, TEMA50 !)
            if len(data_window) >= 150:
                # Calcul des indicateurs
                tema20 = compute_TEMA(list(data_window), period=20)
                tema20_window.append(tema20)
                tema50 = compute_TEMA(list(data_window), period=50)
                if len(tema20_window) >= 3:
                    
                    slope = compute_slope(list(tema20_window), window=slope_window)
                    
                    # ⚡ Conditions de Trading ⚡
                    if current_position == "buy" and btc_balance >= 0.0001 and closed_price  >= last_buy_price * 1.00075  and tema20 > tema50 and tema20 <= tema20_window[-1] * 1.0008 and closed_price <= data_window[-1] * 1.0008:
                        if slope is not None and slope < pente_vente:
                            usdt_balance += btc_balance * closed_price * 0.99925
                            btc_balance = 0.0
                            current_position = "none"
                            print(f"🔥 VENTE à {closed_price:.2f}, USDT: {usdt_balance:.2f}, BTC: {btc_balance:.6f}")
    
                    if current_position == "none" and tema20 < tema50 and usdt_balance >= 10.00 and tema20 >= tema20_window[-1] * 1.0008 and closed_price >= data_window[-1] * 1.0008:
                        if slope is not None and slope > pente_achat:
                            btc_balance = (usdt_balance * 0.99925) / closed_price
                            usdt_balance = 0.0
                            last_buy_price = closed_price
                            current_position = "buy"
                            print(f"🔥 ACHAT à {closed_price:.2f}, USDT: {usdt_balance:.2f}, BTC: {btc_balance:.6f}")

            print(f"📊 TEMA20: {tema20:.2f}, TEMA50: {tema50:.2f}, Slope: {colorize_slope(slope)}")

        except Exception as e:
            print(f"Erreur: {e}")
            time.sleep(10)  # Pause avant de réessayer

if __name__ == "__main__":
    livetest()
