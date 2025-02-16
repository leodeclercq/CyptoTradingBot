# récupérer temps de notre machine
import time
#  calcul scientifique, tableau, db etc
import numpy as np
# garde en mémoire x éléments de liste
from collections import deque
# instance de La bibliothèque binance pqui ermet d'interagir avec l'API de Binance (échange de cryptomonnaies). 
from binance.client import Client
# La classe ThreadedWebsocketManager est spécifiquement conçue pour gérer les connexions WebSocket à Binance.
# Un WebSocket est une technologie qui permet d'établir une connexion permanente entre le client et le serveur
# pour recevoir des mises à jour en temps réel, sans avoir à faire des appels API répétitifs.
# Cette classe gère plusieurs WebSockets de manière efficace en utilisant des threads séparés,
# ce qui permet de recevoir des données en temps réel (comme les prix ou les ordres) de manière fluide
# tout en gardant l'application réactive.
from binance import ThreadedWebsocketManager
# Importation de toutes les énumérations disponibles dans le module `binance.enums` de la bibliothèque Binance.
# Le module `binance.enums` contient des constantes sous forme d'énumérations (enums) qui sont utilisées
# pour spécifier des valeurs fixes et prédéfinies pour différents paramètres lors des appels API.
# Ces énumérations sont utilisées dans des méthodes comme `create_order()`, `get_order()`, etc.,
# pour rendre le code plus lisible et éviter d'utiliser des valeurs littérales comme des chaînes de caractères ou des entiers.
# Par exemple, les énumérations peuvent inclure :
# - `Side.BUY` ou `Side.SELL` pour indiquer si l'ordre est un achat ou une vente.
# -  `OrderType.MARKET` pour spécifier le type d'ordre.
# - `TimeInForce.GTC` (Good Till Canceled), `TimeInForce.IOC` (Immediate or Cancel) pour spécifier la durée de validité d'un ordre.
# L'importation avec * permet d'importer toutes les énumérations à la fois, ce qui simplifie l'utilisation du code
# sans avoir à les importer spécifiquement une par une. Cela permet d'écrire un code plus propre et plus lisible.
# Cependant, l'importation avec `*` peut entraîner des conflits de noms si plusieurs modules ou classes
# contiennent des membres portant le même nom. Dans de tels cas, il est conseillé d'importer uniquement
# les énumérations nécessaires comme suit :
# `from binance.enums import OrderType, Side, TimeInForce`
from binance.enums import *
# (Technical Analysis Library)
# Cette bibliothèque permet de calculer des indicateurs techniques comme TEMA20 et TEMA50 (RSI, MACD, etc.)
# Elle est utilisée pour l'analyse technique des données financières, notamment dans les stratégies de trading automatisées.
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
data_window = deque(maxlen=151)  # stockage des 151 dernières valeurs de closes
time_window = deque(maxlen=151)  # stockage des timestamps associés
tema_window =deque(maxlen=151)   # stockage des TEMA20 associés
# Paramètres pour le calcul du TEMA et du slope
TEMA_period = 20  # nombre de points pour calculer TEMA20
slope_window = 3  # nombre de points pour calculer la pente
# Variable simualtion
usdt_balance = 100.000000  # Balance initiale en USDT
btc_balance = 0.0000000  # Balance initiale en BTC
last_buy_price = 0.0000000
# Seuils
bearish_slope_threshold = -0.084  # seuil pour détecter une pente baissière forte  (-0.01, -0.087)
bullish_slope_threshold = 0.06  # seuil pour détecter une pente haussière forte (0.23, 0.13)
# On considère soit "en position" (buy) soit "hors position"
current_position = "none"
# Calcul de la TEMA avec TA-Lib. Renvoie la dernière valeur calculée.
def compute_TEMA(data, period):
    if len(data) < period:
        return None
    np_data = np.array(data, dtype=float)
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
    #  'c' indique qu'il contient des informations sur le prix actuel.
    if 'c' in msg:
        # Conversion du prix en float
        price = float(msg['c'])
        # Récupération du temps de l'événement en millisecondes
        event_time = msg['E']
        # Mise à jour des fenêtres de données
        data_window.append(price)
        time_window.append(event_time)
        # Si la fenêtre de données contient au moins 151 éléments (pour une analyse complète, TEMA50 !)
        if len(data_window) >= 151:
            # Calcul du TEMA20 et TEMA50
            tema20 = compute_TEMA(list(data_window), period=TEMA_period)
            tema_window.append(tema20)
            tema50 = compute_TEMA(list(data_window), period=50)
            # Si la fenêtre de TEMA contient au moins 61 éléments pour slope
            if len(tema_window) >= 61:
                # Calcul slope
                slope = compute_slope(list(tema_window), window=slope_window)
                # valeurs de TEMA20 pour détecter extrema
                recent_data = list(tema_window)[-11:]
                recent_max = max(recent_data)
                recent_min = min(recent_data)
                # Vente (si en position et conditions remplies)
                if current_position == "buy" and tema20 <= recent_max * 0.9999999 and btc_balance >= 0.0001: #and price >= last_buy_price * 1.001
                    if slope is not None and slope < bearish_slope_threshold and tema20 > (tema50 - 0.4):
                        usdt_balance += btc_balance * price  # Conversion de BTC en USDT
                        btc_balance = 0.000000  # Réinitialisation après vente
                        last_buy_price = 0.000000  # Réinitialisation du prix d'achat
                        print(f"[{time.ctime(event_time/1000)}] 🔥VENTE à 💰{price:.6f} (pente: {colorize_slope(slope)}), 🪙: {btc_balance:.6f}, 💲 : {usdt_balance:.6f},prix d'achat {last_buy_price:.2f}")
                        current_position = "none"
                # Achat (si hors position et conditions remplies)⚠️
                if current_position == "none" and tema20 >= recent_min * 1.0000001 and usdt_balance >= 10:
                    if slope is not None and slope > bullish_slope_threshold and tema20 < (tema50 - 0.8):
                        btc_balance = usdt_balance / price  # Achat du maximum possible
                        usdt_balance = 0.000000  # Tout l'USDT est converti en BTC
                        last_buy_price = price  # Enregistrer le prix d'achat
                        current_position = "buy"
                        print(f"[{time.ctime(event_time/1000)}] 🔥ACHAT à 💰{price:.6f} (pente: {colorize_slope(slope)} ), 🪙: {btc_balance:.6f}, 💲 : 0.00")
                # Affichage de l'état de la parabole
                if tema20 < tema50:
                    print(f"[{time.ctime(event_time/1000)}] 💚 U (pente: {colorize_slope(slope)}):) (TEMA20: {f'\033[94m{tema20:.2f}\033[0m'} < TEMA50: {f'\033[93m{tema50:.2f}\033[0m'}) 💰: {price:.6f}")
                else:
                    print(f"[{time.ctime(event_time/1000)}] ❤️ n  (pente: {colorize_slope(slope)}):( (TEMA20: {f'\033[94m{tema20:.2f}\033[0m'} >= TEMA50: {f'\033[93m{tema50:.2f}\033[0m'})💰: {price:.6f}")
# fonction principale 'main()' qui démarre le processus de gestion du websocket
def main():
     # Boucle infinie pour gérer la connexion WebSocket et les erreurs
    while True:
        try:
            # Création d'une instance du 'ThreadedWebsocketManager' en utilisant la clé API et le secret API
            # Cela permet de se connecter à Binance via WebSocket de manière multithreadée
            twm = ThreadedWebsocketManager(api_key=API_KEY, api_secret=API_SECRET)
            # Démarrage du WebSocket Manager
            twm.start()
            # Démarrage du socket pour récupérer les données de ticker en temps réel pour un symbole donné
            # Le callback 'process_message' sera appelé chaque fois qu'un message est reçu pour traiter les données
            twm.start_symbol_ticker_socket(callback=process_message, symbol=symbol)
            # Boucle interne pour maintenir le WebSocket ouvert
            while True:
                time.sleep(1)
        # Si une exception se produit (erreur de connexion, etc.), cela attrape l'erreur
        except Exception as e:
            print(f"Erreur détectée : {e}. Redémarrage du websocket dans 5s...")
            time.sleep(5)  # Pause avant redémarrage
# Exécution du script
if __name__ == '__main__':
    main()
