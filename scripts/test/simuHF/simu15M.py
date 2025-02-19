# récupérer temps de notre machine
import time
#  calcul scientifique, tableau, db etc
import numpy as np
# garde en mémoire x éléments de liste
from collections import deque
# instance de La bibliothèque binance pqui ermet d'interagir avec l'API de Binance (échange de cryptomonnaies).
from binance.client import Client
# La classe ThreadedWebsocketManager est spécifiquement conçue pour gérer les connexions WebSocket à Binance.
from binance import ThreadedWebsocketManager
# Importation de toutes les énumérations disponibles dans le module `binance.enums` de la bibliothèque Binance.
from binance.enums import *
# (Technical Analysis Library)
import talib
# fonction colored, change la couleur du text pour les print()
from termcolor import colored
# clés API Binance
API_KEY = ""
API_SECRET = ""
# Initialisation du client Binance, instance
client = Client(API_KEY, API_SECRET)
# Paramètres globaux
symbol = 'BTCUSDT'
interval = Client.KLINE_INTERVAL_15MINUTE  # Intervalle de 15 minutes
limit = 151  # Récupérer 151 premières bougies
data_window = deque(maxlen=151)  # stockage des 151 dernières valeurs de closes

update_interval = 15 * 60  # 15 minutes en secondes


data_window = deque(maxlen=151)  # stockage des 151 dernières valeurs de closes
time_window = deque(maxlen=151)  # stockage des timestamps associés
tema_window = deque(maxlen=151)   # stockage des TEMA20 associés
# Paramètres pour le calcul du TEMA et du slope
TEMA_period = 20  # nombre de points pour calculer TEMA20
slope_window = 3  # nombre de points pour calculer la pente
# Variable simulation
usdt_balance = 1000.000000  # Balance initiale en USDT
btc_balance = 0.0000000  # Balance initiale en BTC
last_buy_price = 0.0
# Seuils
bearish_slope_threshold = -1  # seuil pour détecter une pente baissière forte
bullish_slope_threshold = 35  # seuil pour détecter une pente haussière forte
# On considère soit "en position" (buy) soit "hors position"
current_position = "none"

# Calcul de la TEMA avec TA-Lib. Renvoie la dernière valeur calculée.
def compute_TEMA(data, period):
    if len(data) < period:
        return None
    np_data = np.array(data, dtype=float)
    if np_data.ndim != 1:
        print(f"Erreur: Les données doivent être un tableau unidimensionnel. Dimensions actuelles: {np_data.ndim}")
        return None
    tema = talib.TEMA(np_data, timeperiod=period)
    return tema[-1]

# Calcul de la pente sur les 'window' derniers points par régression linéaire.
def compute_slope(data, window=slope_window):
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
# Définition de la fonction process_message qui traite les messages entrants (des données de marché).
# 'msg' est l'argument, qui représente un message contenant des informations sur les prix.
def process_message(msg):
    # Déclaration des variables globales utilisées dans cette simulation
    global current_position, usdt_balance, btc_balance, last_buy_price
    # 'k' indique qu'il contient des informations sur la bougie
    if 'k' in msg and msg['k']['x']:  # Bougie fermée (close)
        # Récupération des informations de la bougie
        price = float(msg['k']['c']) + 93  # Ajouter 93 au prix de fermeture
        event_time = msg['k']['T']  # Timestamp de l'événement
        print(f"Prix actuel {price} à {time.ctime(event_time / 1000)}")
        print(f"usd {usdt_balance:.6f} ")
        print(f"btc{btc_balance:.6f} ")
        # Mise à jour des fenêtres de données
        data_window.append(price)
        time_window.append(event_time)
        print(f"Data window (longueur): {len(data_window)}")
        print(f"Data window (dernière valeur): {data_window[-1]}")
        # Si la fenêtre de données contient au moins 151 éléments (pour une analyse complète, TEMA50 !)
        if len(data_window) >= 150:
            # Calcul du TEMA20 et TEMA50
            tema20 = compute_TEMA(list(data_window), period=TEMA_period)
            tema_window.append(tema20)
            tema50 = compute_TEMA(list(data_window), period=50)
            # Si la fenêtre de TEMA contient au moins 61 éléments pour slope
            if len(tema_window) >= 61:
                # Calcul slope
                slope = compute_slope(list(tema_window), window=slope_window)
                last_data = list(data_window)[-1]
                last_datas = list(data_window)[-2]
                last_tema = list(tema_window)[-2]
                # Vente (si en position et conditions remplies)
                if  last_buy_price < price * 1.00075 and current_position == "buy"  and tema20 > tema50 and tema20 <= last_tema * 1.0002 and last_data <= last_datas * 1.0003 and btc_balance >= 0.0001: #last_buy_price < initial_data[i] * 1.00075
                    if slope is not None and slope < bearish_slope_threshold:
                        usdt_balance += btc_balance * price * 0.99925  # Conversion de BTC en USDT
                        btc_balance = 0.000000  # Réinitialisation après vente
                        print(f" 🔥VENTE à 💰{price:.6f} (pente: {colorize_slope(slope)} ), 🪙: {btc_balance:.6f}, 💲 : {usdt_balance:.6f},prix d'achat {last_buy_price:.2f}")
                        print(f"usd {usdt_balance:.6f} ")
                        print(f"btc{btc_balance:.6f} ")
                        current_position = "none" 
                # Achat (si hors position et conditions remplies)⚠️
                if current_position == "none" and tema20 < tema50 and tema20 >= last_tema * 1.0002 and last_data >= last_datas * 1.0003 and usdt_balance >= 10.00: # and initial_data[i] <= 96500.0:
                    if slope is not None and slope > bullish_slope_threshold:
                        btc_balance = (usdt_balance * 0.99925) / price  # Achat du maximum possible
                        usdt_balance = 0.000000  # Tout l'USDT est converti en BTC
                        last_buy_price = price  # Enregistrer le prix d'achat
                        print(f" 🔥ACHAT à 💰{price:.6f} (pente: {colorize_slope(slope)} ), 🪙: {btc_balance:.6f}, 💲 : 0.00")
                        print(f"usd {usdt_balance:.6f} ")
                        print(f"btc{btc_balance:.6f} ")
                        current_position = "buy"
                #Affichage de l'état de la parabole
                if tema20 < tema50:
                    print(f"[{time.ctime(event_time/1000)}] 💚 U (pente: {colorize_slope(slope)}):) (TEMA20: {f'\033[94m{tema20:.2f}\033[0m'} < TEMA50: {f'\033[93m{tema50:.2f}\033[0m'}) 💰: {price:.6f}")
                    print(f"usd {usdt_balance:.6f} ")
                    print(f"btc{btc_balance:.6f} ")
                else:
                    print(f"[{time.ctime(event_time/1000)}] ❤️ n  (pente: {colorize_slope(slope)}):( (TEMA20: {f'\033[94m{tema20:.2f}\033[0m'} >= TEMA50: {f'\033[93m{tema50:.2f}\033[0m'})💰: {price:.6f}")
                    print(f"usd {usdt_balance:.6f} ")
                    print(f"btc{btc_balance:.6f} ")
# Récupérer les 150 dernières bougies via l'API Binance avant de commencer le WebSocket
def fetch_initial_data(symbol, interval, limit=150):
    # Récupération des 150 dernières bougies de 15 minutes
    klines = client.get_historical_klines(symbol, interval, limit=limit)
    return [float(kline[4]) + 93 for kline in klines]  # Ajouter 93 au prix de clôture et garder uniquement le prix


def start_socket():
    # Fonction pour démarrer le WebSocket et récupérer les données de Kline (15 minutes)
    twm = ThreadedWebsocketManager(api_key=API_KEY, api_secret=API_SECRET)
    twm.start()
    # Remplacer 'symbol' par le symbole que vous souhaitez suivre (par exemple, 'BTCUSDT')
    twm.start_kline_socket(callback=process_message, symbol=symbol, interval=interval)

# Fonction principale 'main()' qui démarre le processus de gestion du websocket
def main():
    # Boucle infinie pour gérer la connexion WebSocket et les erreurs
    while True:
        try:
            # Récupérer les 150 dernières bougies (clôture) au début
            print("Téléchargement des 150 dernières bougies...")
            # Récupérer les données initiales
            initial_data = fetch_initial_data(symbol, interval, limit=151)  # Inclure une bougie pour la prochaine
            # Affichage pour vérifier la structure des données
            print(f"Structure des données initiales : {initial_data[:5]}...")

            # Initialisation des fenêtres de données avec les bougies récupérées
            global data_window, time_window, tema_window
            data_window = deque(initial_data, maxlen=151)  # Initialiser avec les 150 dernières bougies
            time_window = deque([int(time.time() * 1000)] * 151, maxlen=151)  # Simuler les timestamps
            tema_window = deque([compute_TEMA(initial_data, TEMA_period)] * 151, maxlen=151)

            # Démarrer la collecte de données via le WebSocket
            print("Démarrage du WebSocket pour récupérer les mises à jour toutes les 15 minutes...")
            start_socket()

            # Attendre 15 minutes avant la prochaine mise à jour
            print("Attente de 15 minutes avant la prochaine mise à jour...")
            time.sleep(update_interval)  # 15 minutes d'attente
        except Exception as e:
            print(f"Erreur détectée : {e}. Redémarrage du WebSocket dans 5 secondes...")
            time.sleep(5)

if __name__ == '__main__':
    main()
