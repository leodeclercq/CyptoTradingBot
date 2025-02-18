import numpy as np
import matplotlib.pyplot as plt
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
from decimal import Decimal, ROUND_FLOOR
import math


DB_FILE = "C:\\zarov\\trading_data.db"

API_KEY = ""
API_SECRET = ""

client = Client(API_KEY, API_SECRET)
SYMBOL = "BTCFDUSD"
INTERVAL = Client.KLINE_INTERVAL_1SECOND

# URL Binance
BASE_URL = "https://api.binance.com"



    
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
        start_time = end_time - (24* 60 * 60 * 1000)  # 1 heure en arrière
        klines = client.get_historical_klines(SYMBOL, INTERVAL, start_time)
        df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                        'quote_asset_volume', 'num_trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'])
        
        df = df[['time', 'open', 'high', 'low', 'close']].astype(float)
        df['time'] = pd.to_datetime(df['time'], unit='ms').astype(str)

        # Sauvegarder les nouvelles bougies dans la table 'market_data'
        for _, row in df.iterrows():
            save_candle(tuple(row))  # Sauvegarde dans la base

        print("✅ Historique récupéré et sauvegardé dans la base de données.")

            
# 🔹 2. Paramètres de simulation
T = 60  # Simulation sur 30 jours
N = 1000  # Nombre de pas de temps
dt = T / N  # Discrétisation du temps
mu = df["close"].pct_change().mean() * 3600  # Rendement moyen annualisé
sigma = df["close"].pct_change().std() * np.sqrt(3600)  # Volatilité annualisée

# Génération du mouvement brownien
dW = np.sqrt(dt) * np.random.randn(N)  # Incréments gaussiens
W = np.cumsum(dW)  # Somme cumulative
time = np.linspace(0, T, N)  # Echelle de temps 

S0 = df['close'].iloc[-1]  # Dernier prix connu
# Processus de GBM : S(t) = S0 * exp((mu - 0.5 * sigma²) * t + sigma * W_t)
S = S0 * np.exp((mu - 0.5 * sigma**2) * time + sigma * W)

# Tracé
plt.figure(figsize=(10, 5))
plt.plot(np.linspace(0, T, N), W, label="Mouvement brownien Simulation BTC (GBM)")
plt.axhline(S0, color="r", linestyle="--", label="Prix actuel")
plt.xlabel("Temps")
plt.ylabel("W(t) Prix du BTC (USD)")
plt.title("Simulation d’un mouvement brownien")
plt.legend()
plt.show()
