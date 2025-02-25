from datetime import datetime
import numpy as np
from collections import deque
from binance.client import Client
import talib
import requests
import time

# Paramètres API (ne pas utiliser en production avec ces clés !)
API_KEY = ""
API_SECRET = ""

client = Client(API_KEY, API_SECRET)

# Paramètres globaux
symbol = 'BTCUSDT'
interval = Client.KLINE_INTERVAL_15MINUTE  # Intervalle de 15 minutes
limit = 300  # Nombre de bougies à récupérer au début

close_window = deque(maxlen=300)  # stockage des 300 premières valeurs de closes
tema20_window = deque(maxlen=300)   # stockage des TEMA20 associés
tema50_window = deque(maxlen=300)
slopes20_window = deque(maxlen=300)
slopes50_window = deque(maxlen=300)

# Variables simulation
usdt_balance = 0.000000  # Balance initiale en USDT
btc_balance = 0.001000  # Balance initiale en BTC
last_buy_price = 91000
current_position = "buy"  # "none" ou "buy"
# Initialisation pour l'affichage de l'état
initial_display_done = False
# Calcul de la TEMA avec TA-Lib
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

# fonction pour définir la couleur de slope selon sa valeur
def colorize_slope(slope):
    if slope < 0:
        return f'\033[91m{slope:.6f}\033[0m'  # Rouge pour une valeur négative
    elif slope == 0:
        return f'\033[97m{slope:.6f}\033[0m'  # Blanc pour une valeur nulle
    else:
        return f'\033[92m{slope:.6f}\033[0m'  # Vert pour une valeur positive

def get_price():
    """Récupère le prix actuel du marché pour un symbole donné."""
    response = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}")
    return float(response.json()["price"])

# Fonction pour récupérer et traiter les bougies historiques
def get_historical_data():
    global close_window, tema20_window, tema50_window, slopes20_window, slopes50_window, initial_display_done
    
    # Récupérer les dernières bougies historiques
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    
    # Initialiser les données avec les bougies récupérées
    initial_data = [float(kline[4]) for kline in klines]  # Utilisation des prix de clôture
    
    # Remplir les fenêtres avec les données historiques
    close_window.extend(initial_data)
    
    for price in initial_data:
        tema20 = compute_TEMA(list(close_window), period=20)
        tema20_window.append(tema20)
        
        tema50 = compute_TEMA(list(close_window), period=50)
        tema50_window.append(tema50)
        
        if len(tema20_window) > 2 and len(tema50_window) > 2:
            slope20 = compute_slope(list(tema20_window))
            slopes20_window.append(slope20)
            
            slope50 = compute_slope(list(tema50_window))
            slopes50_window.append(slope50)

# Fonction pour récupérer et traiter les nouvelles bougies
def handle_new_candle():
    global usdt_balance, btc_balance, last_buy_price, current_position, initial_display_done
    # Récupérer la dernière bougie
    klines = client.get_klines(symbol=symbol, interval=interval, limit=1)
    
    
    # Obtenir la clôture de la dernière bougie
    close_price = float(klines[0][4])  # 4 = Close price
    close_window.append(close_price)
    print(f"🕒 Bougie clôturée, prix: {close_price:.2f}🪙")
    # Calculer les indicateurs TEMA
    tema20 = compute_TEMA(list(close_window), period=20)
    tema20_window.append(tema20)
    
    tema50 = compute_TEMA(list(close_window), period=50)
    tema50_window.append(tema50)
    if len(tema20_window) > 2 and len(tema50_window) > 2:
        slope20 = compute_slope(list(tema20_window))
        slopes20_window.append(slope20)
        
        slope50 = compute_slope(list(tema50_window))
        slopes50_window.append(slope50)
        # Affichage de l'état initial uniquement la première fois
        if not initial_display_done:
            print(f"🔄 État Initial - 📉 Dernière Bougie: {close_price:.2f} | "
                  f"📈 Pente TEMA20: {colorize_slope(slope20) if slope20 is not None else 'N/A'} | "
                  f"📉 Pente TEMA50: {colorize_slope(slope50) if slope50 is not None else 'N/A'} | "
                  f"TEMA20: {tema20:.2f} | TEMA50: {tema50:.2f}")
            initial_display_done = True
        # Attente de la fin de la bougie actuelle
        current_time = time.time()
        next_candle_time = (current_time // 900 + 1) * 900  # Prochain multiple de 900s (15min)
        sleep_time = next_candle_time - current_time
        print(f"Attente de {sleep_time:.2f} secondes jusqu'à la prochaine clôture de bougie...")
        time.sleep(sleep_time)
        if len(slopes20_window) > 2 and len(slopes50_window) > 2:
            
            # Vente (si en position et conditions remplies)
            if current_position == "buy" and tema20 > tema50 and btc_balance >= 0.000001 and tema20_window[-2] > tema50_window[-2] and tema20_window[-3] > tema50_window[-3] and last_buy_price * 1.00075 < close_price: 
                if slope20 is not None and slope50 is not None and slope20 < -1 and slope50 > 1 and slopes20_window[-2] > 1 and slopes50_window[-2] > 1 and slopes20_window[-3] > 1 and slopes50_window[-3] > 1:
                    usdt_balance = btc_balance * close_price * 0.99925  # Conversion de BTC en USDT
                    btc_balance = 0.000000  # Réinitialisation après vente
                    last_buy_price = close_price
                    print(f"🔥VENTE à 💰{close_price:.6f}, 🪙: {btc_balance:.6f}, 💲 : {usdt_balance:.6f}, prix d'achat {last_buy_price:.2f}")
                    current_position = "none"
            
            # Achat (si hors position et conditions remplies)
            if current_position == "none" and tema20 < tema50 and usdt_balance >= 1 and tema20_window[-2] < tema50_window[-2] and tema20_window[-3] < tema50_window[-3]:
                if slope20 is not None and slope50 is not None and slope20 > 1 and slope50 < -1 and slopes20_window[-2] < -1 and slopes50_window[-2] < -1 and slopes20_window[-3] < -1 and slopes50_window[-3] < -1 and last_buy_price * 1.00075 > close_price:
                    btc_balance = (usdt_balance * 0.99925) / close_price  # Achat du maximum possible
                    usdt_balance = 0.000000  # Tout l'USDT est converti en BTC
                    last_buy_price = close_price  # Enregistrer le prix d'achat
                    print(f"🔥ACHAT à 💰{close_price:.6f}, 🪙: {btc_balance:.6f}, 💲 :{usdt_balance:.6f}, prix d'achat {last_buy_price:.2f}")
                    current_position = "buy"
            
            # Affichage des informations
            candle_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if tema20 < tema50:
                print(f" {candle_time} |💚 U (pente TEMA20: {colorize_slope(slope20)} ), (pente TEMA50: {colorize_slope(slope50)} ) (TEMA20: {f'\033[94m{tema20:.2f}\033[0m'} < TEMA50: {f'\033[93m{tema50:.2f}\033[0m'}) 🪙: {btc_balance:.6f}, 💲 : {usdt_balance:.6f}, 💰: {close_price:.6f}")
            else:
                print(f" {candle_time} |❤️ n  (pente TEMA20: {colorize_slope(slope20)} ), (pente TEMA50: {colorize_slope(slope50)} )( (TEMA20: {f'\033[94m{tema20:.2f}\033[0m'} >= TEMA50: {f'\033[93m{tema50:.2f}\033[0m'}) 🪙: {btc_balance:.6f}, 💲 : {usdt_balance:.6f},💰: {close_price:.6f}")

# Fonction principale pour démarrer la simulation live
def run_live_simulation():
    # Charger les données historiques au début
    get_historical_data()
    
    # Commencer à vérifier les nouvelles bougies après avoir chargé les données
    while True:
        try:
            handle_new_candle()
        except Exception as e:
            print(f"Erreur lors de la récupération des données: {e}")
            time.sleep(10)  # Attendre un peu avant de réessayer

if __name__ == "__main__":
    run_live_simulation()
