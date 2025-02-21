from datetime import datetime
import numpy as np
from collections import deque
from binance.client import Client
import talib

# Paramètres API (ne pas utiliser en production avec ces clés !)
API_KEY = ""
API_SECRET = ""
client = Client(API_KEY, API_SECRET)

# Paramètres globaux
symbol = 'BTCUSDT'
interval = Client.KLINE_INTERVAL_15MINUTE  # Intervalle de 15 minutes
limit = 151 + (4*24)  # Récupérer 151 premières bougies
data_window = deque(maxlen=151)  # stockage des 151 dernières valeurs de closes
tema20_window = deque(maxlen=151)   # stockage des TEMA20 associés
tema50_window = deque(maxlen=151)
slopes_window = deque(maxlen=151)
# Variable simulation

usdt_balance = 10.000000  # Balance initiale en USDT
btc_balance = 0.0000000  # Balance initiale en BTC
last_buy_price = 0.0
current_position = "FIRST"  # "none" ou "buy"

# Seuils
bearish_slope_threshold = -12  # seuil pour détecter une pente baissière forte
bullish_slope_threshold = 3.8  # seuil pour détecter une pente haussière forte

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


# Définition de la fonction de backtest
def backtest():
    global usdt_balance, btc_balance, last_buy_price, current_position
    
    # Récupération des 150 dernières bougies via l'API Binance
    print("Récupération des données historiques...")
    klines = client.get_historical_klines(symbol, interval, limit=limit)
    
    if not klines:
        print("Erreur: Aucune donnée récupérée.")
        return
    
    initial_data = [float(kline[4]) + 93 for kline in klines]  # Utilisation des prix de clôture
    
    # Vérification des données
    print(f"Données récupérées: {initial_data[-5:]} ...")  # Affiche les 5 premières valeurs
    
    data_window.clear()
    
    # Initialisation des fenêtres avec les données récupérées
    data_window.extend(initial_data)
    

    # Backtest sur chaque nouvelle donnée
    print(f"Lancement du backtest sur {len(initial_data)-151} bougies...")
    for i in range(151, len(initial_data)):  # Commencer après les 150 premières bougies
        # Dans la boucle for
        timestamp = klines[i][0]  # Timestamp en millisecondes
        candle_time = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
        # Ajouter la nouvelle donnée dans la fenêtre
        data_window.append(initial_data[i])
        
        # Calculer les TEMA avec les fenêtres mises à jour
        tema20 = compute_TEMA(list(data_window), period=20)
        tema20_window.append(tema20)
        tema50 = compute_TEMA(list(data_window), period=50)
        tema50_window.append(tema50)
        
        # Affichage de l'état des TEMA et du prix
        #print(f"bougie {i+1} - TEMA20: {tema20:.2f}, TEMA50: {tema50:.2f}, prix actuel: {initial_data[i]:.6f}")
        if len(tema20_window) > 2:
            slope = compute_slope(list(tema20_window))
            slopes_window.append(slope)
            last_data = list(data_window)[-1]
            last_datas = list(data_window)[-2]
            last_tema = list(tema20_window)[-2]
            if len(slopes_window) > 2:
                # Vente (si en position et conditions remplies)
                if   94500 < initial_data[i]  and last_buy_price < initial_data[i] * 1.0015 and current_position == "buy"  and tema20 > tema50 and tema20 <= (last_tema + 8) and last_data <=  (last_datas + 30) and btc_balance >= 0.0001: #last_buy_price < initial_data[i] * 1.00075
                    if slope is not None and slope < bearish_slope_threshold and slopes_window[-2] > 0 and tema50 >  (tema50_window[-2] + 10.5):
                        usdt_balance += btc_balance * initial_data[i] * 0.99925  # Conversion de BTC en USDT
                        btc_balance = 0.000000  # Réinitialisation après vente
                        print(f" {candle_time} | 🔥VENTE à 💰{initial_data[i]:.6f} (pente: {colorize_slope(slope)} ), 🪙: {btc_balance:.6f}, 💲 : {usdt_balance:.6f},prix d'achat {last_buy_price:.2f}")
                        current_position = "none"
                if   98500 < initial_data[i] and current_position == "buy" and tema20 > tema50 and  btc_balance >= 0.0001: # and initial_data[i] <= 96500.0:
                    usdt_balance += btc_balance * initial_data[i] * 0.99925  # Conversion de BTC en USDT
                    btc_balance = 0.000000  # Réinitialisation après vente
                    print(f" {candle_time} | 🔥VENTE à 💰{initial_data[i]:.6f} (pente: {colorize_slope(slope)} ), 🪙: {btc_balance:.6f}, 💲 : {usdt_balance:.6f},prix d'achat {last_buy_price:.2f}")
                    current_position = "none"
                # Achat (si hors position et conditions remplies)⚠️
                if initial_data[i] < 98000  and current_position == "none" and tema20 < tema50 and tema20 >= (last_tema + 8) and last_data >= (last_datas + 9) and usdt_balance >= 10.00: # and initial_data[i] <= 96500.0:
                    if slope is not None and slope > bullish_slope_threshold and slopes_window[-2] < 0 :
                        btc_balance = (usdt_balance * 0.99925) / initial_data[i]  # Achat du maximum possible
                        usdt_balance = 0.000000  # Tout l'USDT est converti en BTC
                        last_buy_price = initial_data[i]  # Enregistrer le prix d'achatH
                        current_position = "buy"
                        print(f" {candle_time} | 🔥ACHAT à 💰{initial_data[i]:.6f} (pente: {colorize_slope(slope)} ), 🪙: {btc_balance:.6f}, 💲 : 0.00")
                if current_position == "FIRST"  and usdt_balance >= 10.00: # and initial_data[i] <= 96500.0:
                    btc_balance = (usdt_balance * 0.99925) / initial_data[i]  # Achat du maximum possible
                    usdt_balance = 0.000000  # Tout l'USDT est converti en BTC
                    last_buy_price = initial_data[i]  # Enregistrer le prix d'achat
                    current_position = "buy"
                    print(f" {candle_time} | 🔥ACHAT à 💰{initial_data[i]:.6f} (pente: {colorize_slope(slope)} ), 🪙: {btc_balance:.6f}, 💲 : 0.00")
                
                #Affichage de l'état de la parabole
                        # Ajoute candle_time aux affichages
                #print(f"TEMA20: {tema20}, Last_TEMA: {last_tema}, Diff_TEMA: {tema20 - last_tema}")
                #print(f"Last Data: {last_data}, Last Datas: {last_datas}, Diff Price: {last_data - last_datas}")
                #print(f"Slope: {slope}, Previous Slope: {slopes_window[-2] if len(slopes_window) > 1 else 'N/A'}")

                if tema20 < tema50:
                    print(f" {candle_time} |💚 U (pente: {colorize_slope(slope)}):) (TEMA20: {f'\033[94m{tema20:.2f}\033[0m'} < TEMA50: {f'\033[93m{tema50:.2f}\033[0m'}) 💰: {initial_data[i]:.6f}")
                else:
                    print(f" {candle_time} |❤️ n  (pente: {colorize_slope(slope)}):( (TEMA20: {f'\033[94m{tema20:.2f}\033[0m'} >= TEMA50: {f'\033[93m{tema50:.2f}\033[0m'}) 💰: {initial_data[i]:.6f}")
    print(f"usd {usdt_balance:.6f} ")
    print(f"btc{btc_balance:.6f} ")


if __name__ == "__main__":
    backtest()
