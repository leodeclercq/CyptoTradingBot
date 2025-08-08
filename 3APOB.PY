import pandas as pd
import os
import requests
import sqlite3
from datetime import datetime, timedelta
import time
import json
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import numpy as np
from typing import List, Dict, Tuple, Optional
import asyncio
import logging
import talib
import hmac
import hashlib
from urllib.parse import urlencode
import sys
from collections import deque
import threading

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "scalping_bot_jurgen.db")

BINANCE_BASE_URL = "https://api.binance.com/api/v3"
BINANCE_TESTNET = "https://testnet.binance.vision/api/v3"

# Clés API Binance (IMPORTANT: Configurez vos vraies clés ici)
API_KEY = "your_api_key_here"
API_SECRET = "your_api_secret_here"
USE_TESTNET = True  # False pour le trading réel

TELEGRAM_BOT_TOKEN = "432551:GSDSD-FDFQDQ"
TELEGRAM_CHANNEL_ID = "-0000"

# Configuration du trading automatique
ENABLE_AUTO_TRADING = True  # Active/désactive le trading automatique
TRADE_AMOUNT_USDT = 20.0    # Montant par trade en USDT
MAX_POSITIONS_PER_SYMBOL = 1 # Nombre maximum de positions par crypto
RISK_PERCENTAGE = 2.0       # % du capital à risquer par trade

# Configuration du logging - VERSION CORRIGÉE POUR WINDOWS
class WindowsSafeFormatter(logging.Formatter):
    """Formateur qui remplace les emojis par du texte pour éviter les erreurs d'encodage"""
    
    def format(self, record):
        msg = super().format(record)
        
        # Remplacer les emojis problématiques par du texte
        emoji_replacements = {
            '🔍': '[ANALYSE]',
            '✅': '[OK]',
            '❌': '[ERREUR]',
            '⚡': '[SIGNAL]',
            '🤖': '[BOT]',
            '📊': '[STATS]',
            '🟢': '[LONG]',
            '🔴': '[SHORT]',
            '🟡': '[ATTENTE]',
            '⚪': '[NEUTRE]',
            '🎯': '[CIBLE]',
            '📈': '[HAUSSE]',
            '📉': '[BAISSE]',
            '🔄': '[CYCLE]',
            '💡': '[INFO]',
            '🛡️': '[PROTECTION]',
            '⭐': '[ETOILE]',
            '🕐': '[TEMPS]',
            '🔸': '[PUCE]',
            '⬇️': '[BAS]',
            '⬆️': '[HAUT]',
            '🔥': '[FEU]',
            '💰': '[MONEY]',
            '📊': '[CHART]'
        }
        
        for emoji, replacement in emoji_replacements.items():
            msg = msg.replace(emoji, replacement)
        
        return msg

# Configuration du logging avec gestion Windows
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scalping_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Appliquer le formateur sécurisé pour Windows
if sys.platform == "win32":
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setFormatter(WindowsSafeFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialise les tables de la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table des cryptos surveillées
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watched_cryptos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'active',
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_update TIMESTAMP
            )
        ''')
        
        # Table des signaux de trading
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                entry_price REAL,
                tp1 REAL,
                tp2 REAL,
                tp3 REAL,
                stop_loss REAL,
                tema20 REAL,
                tema50 REAL,
                rsi REAL,
                adx REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # Table des positions ouvertes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS open_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL,
                quantity REAL,
                tp1 REAL,
                tp2 REAL,
                tp3 REAL,
                stop_loss REAL,
                order_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'open',
                current_pnl REAL DEFAULT 0.0
            )
        ''')
        
        # Table des trades terminés
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS completed_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL,
                exit_price REAL,
                quantity REAL,
                pnl REAL,
                pnl_percentage REAL,
                entry_time TIMESTAMP,
                exit_time TIMESTAMP,
                duration_minutes INTEGER,
                exit_reason TEXT
            )
        ''')
        
        # Table historique des prix pour 15min et 1min
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                open_time TIMESTAMP,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                timeframe TEXT,
                tema20 REAL,
                tema50 REAL,
                rsi REAL,
                adx REAL,
                bb_upper REAL,
                bb_lower REAL,
                volatility REAL,
                UNIQUE(symbol, open_time, timeframe)
            )
        ''')
        
        # Table des performances
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                total_profit REAL DEFAULT 0.0,
                max_drawdown REAL DEFAULT 0.0,
                win_rate REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_crypto(self, symbol: str) -> bool:
        """Ajoute une crypto à la surveillance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO watched_cryptos (symbol) VALUES (?)",
                (symbol.upper(),)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Erreur ajout crypto {symbol}: {e}")
            return False
        finally:
            conn.close()
    
    def get_watched_cryptos(self) -> List[str]:
        """Récupère la liste des cryptos surveillées actives"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT symbol FROM watched_cryptos WHERE status = 'active'"
        )
        result = [row[0] for row in cursor.fetchall()]
        conn.close()
        return result
    
    def save_signal(self, symbol: str, signal_data: Dict):
        """Sauvegarde un signal de trading"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trading_signals 
            (symbol, signal_type, entry_price, tp1, tp2, tp3, stop_loss, tema20, tema50, rsi, adx)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            symbol, signal_data['type'], signal_data['entry_price'],
            signal_data['tp1'], signal_data['tp2'], signal_data['tp3'],
            signal_data['stop_loss'], signal_data['tema20'], signal_data['tema50'],
            signal_data['rsi'], signal_data['adx']
        ))
        conn.commit()
        conn.close()
    
    def add_position(self, position_data: Dict):
        """Ajoute une nouvelle position"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO open_positions 
            (symbol, side, entry_price, quantity, tp1, tp2, tp3, stop_loss, order_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            position_data['symbol'], position_data['side'], position_data['entry_price'],
            position_data['quantity'], position_data['tp1'], position_data['tp2'],
            position_data['tp3'], position_data['stop_loss'], position_data.get('order_id', '')
        ))
        conn.commit()
        conn.close()
    
    def get_open_positions(self, symbol: str = None) -> List[Dict]:
        """Récupère les positions ouvertes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute('''
                SELECT * FROM open_positions 
                WHERE symbol = ? AND status = 'open'
            ''', (symbol,))
        else:
            cursor.execute("SELECT * FROM open_positions WHERE status = 'open'")
        
        columns = [desc[0] for desc in cursor.description]
        positions = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return positions
    
    def close_position(self, position_id: int, exit_price: float, exit_reason: str):
        """Ferme une position"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Récupérer les détails de la position
        cursor.execute("SELECT * FROM open_positions WHERE id = ?", (position_id,))
        position = cursor.fetchone()
        
        if position:
            # Calculer le PnL
            entry_price = position[3]
            quantity = position[4]
            side = position[2]
            
            if side == 'LONG':
                pnl = (exit_price - entry_price) * quantity
                pnl_percentage = ((exit_price - entry_price) / entry_price) * 100
            else:  # SHORT
                pnl = (entry_price - exit_price) * quantity
                pnl_percentage = ((entry_price - exit_price) / entry_price) * 100
            
            # Ajouter aux trades terminés
            entry_time = datetime.fromisoformat(position[9])
            exit_time = datetime.now()
            duration = int((exit_time - entry_time).total_seconds() / 60)
            
            cursor.execute('''
                INSERT INTO completed_trades
                (symbol, side, entry_price, exit_price, quantity, pnl, pnl_percentage, 
                 entry_time, exit_time, duration_minutes, exit_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                position[1], side, entry_price, exit_price, quantity, pnl, pnl_percentage,
                position[9], exit_time.isoformat(), duration, exit_reason
            ))
            
            # Mettre à jour le statut de la position
            cursor.execute(
                "UPDATE open_positions SET status = 'closed' WHERE id = ?",
                (position_id,)
            )
            
            conn.commit()
            logger.info(f"💰 Position fermée: {position[1]} {side} - PnL: {pnl:.2f} USDT ({pnl_percentage:.2f}%)")
        
        conn.close()
    
    def save_price_data(self, symbol: str, timeframe: str, kline_data: List, indicators: Dict):
        """Sauvegarde l'historique des prix avec indicateurs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for i, kline in enumerate(kline_data):
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO price_history 
                    (symbol, open_time, open, high, low, close, volume, timeframe, 
                     tema20, tema50, rsi, adx, bb_upper, bb_lower, volatility)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol,
                    datetime.fromtimestamp(kline[0] / 1000).isoformat(),
                    float(kline[1]), float(kline[2]), float(kline[3]),
                    float(kline[4]), float(kline[5]), timeframe,
                    indicators.get('tema20', [0])[i] if i < len(indicators.get('tema20', [])) else 0,
                    indicators.get('tema50', [0])[i] if i < len(indicators.get('tema50', [])) else 0,
                    indicators.get('rsi', [0])[i] if i < len(indicators.get('rsi', [])) else 0,
                    indicators.get('adx', [0])[i] if i < len(indicators.get('adx', [])) else 0,
                    indicators.get('bb_upper', [0])[i] if i < len(indicators.get('bb_upper', [])) else 0,
                    indicators.get('bb_lower', [0])[i] if i < len(indicators.get('bb_lower', [])) else 0,
                    indicators.get('volatility', [0])[i] if i < len(indicators.get('volatility', [])) else 0
                ))
            except Exception as e:
                logger.error(f"Erreur sauvegarde prix {symbol}: {e}")
                continue
        
        conn.commit()
        conn.close()

class BinanceClient:
    def __init__(self):
        self.base_url = BINANCE_TESTNET if USE_TESTNET else BINANCE_BASE_URL
        self.api_key = API_KEY
        self.api_secret = API_SECRET
        
        # Session pour les requêtes
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json", 
            "X-MBX-APIKEY": self.api_key
        })
    
    def get_binance_server_time(self):
        """Récupère l'heure du serveur Binance"""
        try:
            response = requests.get(f"{self.base_url}/time")
            return response.json()["serverTime"]
        except Exception as e:
            logger.error(f"Erreur récupération heure serveur: {e}")
            return int(time.time() * 1000)
    
    def _generate_signature(self, params: dict) -> str:
        """Génère la signature HMAC pour l'authentification"""
        query_string = urlencode(sorted(params.items()))
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def send_signed_request(self, http_method: str, url_path: str, payload: dict = {}):
        """Envoie une requête signée à Binance"""
        payload["timestamp"] = self.get_binance_server_time()
        payload["recvWindow"] = 5000
        
        query_string = urlencode(sorted(payload.items()))
        signature = self._generate_signature(payload)
        url = f"{self.base_url}{url_path}?{query_string}&signature={signature}"
        
        try:
            response = self.session.request(http_method, url)
            return response.json()
        except Exception as e:
            logger.error(f"Erreur requête signée: {e}")
            return {}
    
    def validate_symbol(self, symbol: str) -> bool:
        """Valide l'existence d'une paire sur Binance"""
        try:
            response = requests.get(f"{self.base_url}/exchangeInfo")
            data = response.json()
            symbols = [s['symbol'] for s in data['symbols']]
            return symbol.upper() in symbols
        except Exception as e:
            logger.error(f"Erreur validation symbole {symbol}: {e}")
            return False
    
    def get_klines(self, symbol: str, interval: str = "15m", limit: int = 500) -> List:
        """Récupère les données OHLCV"""
        try:
            params = {
                'symbol': symbol.upper(),
                'interval': interval,
                'limit': limit
            }
            response = requests.get(f"{self.base_url}/klines", params=params)
            return response.json()
        except Exception as e:
            logger.error(f"Erreur récupération klines {symbol}: {e}")
            return []
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Récupère le prix actuel"""
        try:
            params = {'symbol': symbol.upper()}
            response = requests.get(f"{self.base_url}/ticker/price", params=params)
            data = response.json()
            return float(data['price'])
        except Exception as e:
            logger.error(f"Erreur prix actuel {symbol}: {e}")
            return None
    
    def get_account_balance(self) -> Dict[str, float]:
        """Récupère les balances du compte"""
        try:
            account_info = self.send_signed_request("GET", "/account")
            balances = {}
            
            if "balances" in account_info:
                for balance in account_info["balances"]:
                    asset = balance["asset"]
                    free = float(balance["free"])
                    if free > 0:
                        balances[asset] = free
            
            return balances
        except Exception as e:
            logger.error(f"Erreur récupération balances: {e}")
            return {}
    
    def place_market_order(self, symbol: str, side: str, quantity: float) -> Dict:
        """Place un ordre au marché"""
        if USE_TESTNET:
            logger.info(f"💰 [TESTNET] Ordre {side}: {quantity:.6f} {symbol}")
            return {
                "orderId": f"test_{int(time.time())}",
                "status": "FILLED",
                "executedQty": str(quantity),
                "fills": [{"price": str(self.get_current_price(symbol)), "qty": str(quantity)}]
            }
        
        try:
            params = {
                "symbol": symbol.upper(),
                "side": side.upper(),
                "type": "MARKET",
                "quantity": quantity
            }
            
            result = self.send_signed_request("POST", "/order", params)
            logger.info(f"💰 Ordre {side} exécuté: {quantity:.6f} {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Erreur placement ordre {symbol}: {e}")
            return {}
    
    def calculate_trade_quantity(self, symbol: str, amount_usdt: float, current_price: float) -> float:
        """Calcule la quantité à trader"""
        try:
            # Récupérer les infos du symbole pour les précisions
            response = requests.get(f"{self.base_url}/exchangeInfo")
            exchange_info = response.json()
            
            symbol_info = None
            for s in exchange_info['symbols']:
                if s['symbol'] == symbol.upper():
                    symbol_info = s
                    break
            
            if not symbol_info:
                return 0.0
            
            # Trouver la précision de quantité
            step_size = None
            for f in symbol_info['filters']:
                if f['filterType'] == 'LOT_SIZE':
                    step_size = float(f['stepSize'])
                    break
            
            if not step_size:
                step_size = 0.00001  # Valeur par défaut
            
            # Calculer la quantité
            quantity = amount_usdt / current_price
            
            # Arrondir selon la précision
            precision = len(str(step_size).split('.')[-1].rstrip('0'))
            quantity = round(quantity, precision)
            
            return quantity
            
        except Exception as e:
            logger.error(f"Erreur calcul quantité {symbol}: {e}")
            return 0.0

class TechnicalAnalyzer:
    def __init__(self):
        self.lookback_period = 200
    
    def calculate_tema(self, prices: np.array, period: int = 20) -> np.array:
        """Calcule le Triple Exponential Moving Average (TEMA)"""
        try:
            return talib.TEMA(prices, timeperiod=period)
        except Exception as e:
            logger.error(f"Erreur calcul TEMA: {e}")
            return np.full_like(prices, np.nan)
    
    def calculate_rsi(self, prices: np.array, period: int = 14) -> np.array:
        """Calcule le RSI"""
        try:
            return talib.RSI(prices, timeperiod=period)
        except Exception as e:
            logger.error(f"Erreur calcul RSI: {e}")
            return np.full_like(prices, np.nan)
    
    def calculate_adx(self, high: np.array, low: np.array, close: np.array, period: int = 14) -> np.array:
        """Calcule l'ADX"""
        try:
            return talib.ADX(high, low, close, timeperiod=period)
        except Exception as e:
            logger.error(f"Erreur calcul ADX: {e}")
            return np.full_like(close, np.nan)
    
    def calculate_bollinger_bands(self, prices: np.array, period: int = 20) -> Tuple[np.array, np.array, np.array]:
        """Calcule les Bollinger Bands"""
        try:
            upper, middle, lower = talib.BBANDS(prices, timeperiod=period)
            return upper, middle, lower
        except Exception as e:
            logger.error(f"Erreur calcul Bollinger: {e}")
            return np.full_like(prices, np.nan), np.full_like(prices, np.nan), np.full_like(prices, np.nan)
    
    def calculate_volatility(self, prices: np.array, period: int = 20) -> np.array:
        """Calcule la volatilité"""
        try:
            returns = np.diff(prices) / prices[:-1]
            volatility = np.array([
                np.std(returns[max(0, i-period+1):i+1]) * np.sqrt(period) 
                for i in range(len(returns))
            ])
            return np.concatenate([[np.nan], volatility])
        except Exception as e:
            logger.error(f"Erreur calcul volatilité: {e}")
            return np.full_like(prices, np.nan)
    
    def calculate_all_indicators(self, klines: List) -> Dict:
        """Calcule tous les indicateurs techniques"""
        if len(klines) < 50:
            return {}
        
        # Conversion en numpy arrays
        close = np.array([float(k[4]) for k in klines])
        high = np.array([float(k[2]) for k in klines])
        low = np.array([float(k[3]) for k in klines])
        volume = np.array([float(k[5]) for k in klines])
        
        # Calcul des indicateurs
        tema20 = self.calculate_tema(close, 20)
        tema50 = self.calculate_tema(close, 50)
        rsi = self.calculate_rsi(close)
        adx = self.calculate_adx(high, low, close)
        bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(close)
        volatility = self.calculate_volatility(close)
        
        return {
            'tema20': tema20,
            'tema50': tema50,
            'rsi': rsi,
            'adx': adx,
            'bb_upper': bb_upper,
            'bb_middle': bb_middle,
            'bb_lower': bb_lower,
            'volatility': volatility,
            'close': close,
            'high': high,
            'low': low,
            'volume': volume
        }
    
    def generate_scalping_signals(self, indicators: Dict, symbol: str) -> Optional[Dict]:
        """Génère les signaux de scalping basés sur TEMA, RSI, ADX"""
        if not indicators or len(indicators['close']) < 50:
            return None
        
        # Dernières valeurs
        current_price = indicators['close'][-1]
        tema20_current = indicators['tema20'][-1]
        tema50_current = indicators['tema50'][-1]
        rsi_current = indicators['rsi'][-1]
        adx_current = indicators['adx'][-1]
        volatility_current = indicators['volatility'][-1]
        
        # Vérification des valeurs NaN
        if any(np.isnan([tema20_current, tema50_current, rsi_current, adx_current])):
            return None
        
        signal = None
        
        # Signal LONG
        if (current_price > tema20_current and 
            tema20_current > tema50_current and
            rsi_current > 50 and rsi_current < 70 and
            adx_current > 25):
            
            # Calcul des niveaux TP/SL pour LONG
            tp1 = current_price * 1.005  # 0.5%
            tp2 = current_price * 1.010  # 1.0%
            tp3 = current_price * 1.015  # 1.5%
            stop_loss = current_price * 0.997  # 0.3%
            
            signal = {
                'type': 'LONG',
                'symbol': symbol,
                'entry_price': current_price,
                'tp1': tp1,
                'tp2': tp2,
                'tp3': tp3,
                'stop_loss': stop_loss,
                'tema20': tema20_current,
                'tema50': tema50_current,
                'rsi': rsi_current,
                'adx': adx_current,
                'volatility': volatility_current,
                'confidence': self._calculate_confidence(indicators, 'LONG')
            }
        
        # Signal SHORT
        elif (current_price < tema20_current and 
              tema20_current < tema50_current and
              rsi_current < 50 and rsi_current > 30 and
              adx_current > 25):
            
            # Calcul des niveaux TP/SL pour SHORT
            tp1 = current_price * 0.995  # -0.5%
            tp2 = current_price * 0.990  # -1.0%
            tp3 = current_price * 0.985  # -1.5%
            stop_loss = current_price * 1.003  # +0.3%
            
            signal = {
                'type': 'SHORT',
                'symbol': symbol,
                'entry_price': current_price,
                'tp1': tp1,
                'tp2': tp2,
                'tp3': tp3,
                'stop_loss': stop_loss,
                'tema20': tema20_current,
                'tema50': tema50_current,
                'rsi': rsi_current,
                'adx': adx_current,
                'volatility': volatility_current,
                'confidence': self._calculate_confidence(indicators, 'SHORT')
            }
        
        return signal
    
    def _calculate_confidence(self, indicators: Dict, signal_type: str) -> float:
        """Calcule la confiance du signal (0-100%)"""
        confidence = 50.0  # Base
        
        # Bonus pour ADX fort
        if indicators['adx'][-1] > 30:
            confidence += 15
        elif indicators['adx'][-1] > 25:
            confidence += 10
        
        # Bonus pour RSI dans la zone optimale
        rsi = indicators['rsi'][-1]
        if signal_type == 'LONG' and 50 < rsi < 65:
            confidence += 10
        elif signal_type == 'SHORT' and 35 < rsi < 50:
            confidence += 10
        
        # Bonus pour volatilité modérée
        if 0.01 < indicators['volatility'][-1] < 0.05:
            confidence += 10
        
        return min(confidence, 95.0)

class TradingEngine:
    """Moteur de trading automatique"""
    def __init__(self, binance_client, db_manager):
        self.binance = binance_client
        self.db = db_manager
        self.active_trades = {}  # Dictionnaire des trades actifs par symbole
        
    def can_open_position(self, symbol: str) -> bool:
        """Vérifie si on peut ouvrir une nouvelle position"""
        if not ENABLE_AUTO_TRADING:
            return False
            
        open_positions = self.db.get_open_positions(symbol)
        return len(open_positions) < MAX_POSITIONS_PER_SYMBOL
    
    def execute_signal(self, signal: Dict) -> bool:
        """Exécute un signal de trading"""
        symbol = signal['symbol']
        
        if not self.can_open_position(symbol):
            logger.info(f"⚠️ Position déjà ouverte pour {symbol}, signal ignoré")
            return False
        
        try:
            current_price = signal['entry_price']
            
            # Calculer la quantité à trader
            quantity = self.binance.calculate_trade_quantity(symbol, TRADE_AMOUNT_USDT, current_price)
            
            if quantity <= 0:
                logger.error(f"❌ Quantité invalide pour {symbol}: {quantity}")
                return False
            
            # Placer l'ordre
            if signal['type'] == 'LONG':
                order = self.binance.place_market_order(symbol, 'BUY', quantity)
            else:
                order = self.binance.place_market_order(symbol, 'SELL', quantity)
            
            if order and order.get('status') == 'FILLED':
                # Enregistrer la position
                position_data = {
                    'symbol': symbol,
                    'side': signal['type'],
                    'entry_price': current_price,
                    'quantity': quantity,
                    'tp1': signal['tp1'],
                    'tp2': signal['tp2'],
                    'tp3': signal['tp3'],
                    'stop_loss': signal['stop_loss'],
                    'order_id': order.get('orderId', '')
                }
                
                self.db.add_position(position_data)
                self.active_trades[symbol] = position_data
                
                logger.info(f"✅ Position ouverte: {signal['type']} {symbol} à {current_price:.6f}")
                return True
            
        except Exception as e:
            logger.error(f"❌ Erreur exécution signal {symbol}: {e}")
        
        return False
    
    def check_exit_conditions(self):
        """Vérifie les conditions de sortie pour toutes les positions ouvertes"""
        open_positions = self.db.get_open_positions()
        
        for position in open_positions:
            symbol = position['symbol']
            current_price = self.binance.get_current_price(symbol)
            
            if not current_price:
                continue
            
            side = position['side']
            entry_price = position['entry_price']
            stop_loss = position['stop_loss']
            tp1 = position['tp1']
            tp2 = position['tp2']
            tp3 = position['tp3']
            
            should_close = False
            exit_reason = ""
            
            if side == 'LONG':
                # Vérifier Stop Loss
                if current_price <= stop_loss:
                    should_close = True
                    exit_reason = "Stop Loss"
                # Vérifier Take Profits
                elif current_price >= tp3:
                    should_close = True
                    exit_reason = "TP3 atteint"
                elif current_price >= tp2:
                    should_close = True
                    exit_reason = "TP2 atteint"
                elif current_price >= tp1:
                    should_close = True
                    exit_reason = "TP1 atteint"
            
            else:  # SHORT
                # Vérifier Stop Loss
                if current_price >= stop_loss:
                    should_close = True
                    exit_reason = "Stop Loss"
                # Vérifier Take Profits
                elif current_price <= tp3:
                    should_close = True
                    exit_reason = "TP3 atteint"
                elif current_price <= tp2:
                    should_close = True
                    exit_reason = "TP2 atteint"
                elif current_price <= tp1:
                    should_close = True
                    exit_reason = "TP1 atteint"
            
            if should_close:
                self.close_position(position, current_price, exit_reason)
    
    def close_position(self, position: Dict, exit_price: float, exit_reason: str):
        """Ferme une position"""
        try:
            symbol = position['symbol']
            side = position['side']
            quantity = position['quantity']
            
            # Placer l'ordre de fermeture
            if side == 'LONG':
                order = self.binance.place_market_order(symbol, 'SELL', quantity)
            else:
                order = self.binance.place_market_order(symbol, 'BUY', quantity)
            
            if order and order.get('status') == 'FILLED':
                # Enregistrer la fermeture
                self.db.close_position(position['id'], exit_price, exit_reason)
                
                # Supprimer des trades actifs
                if symbol in self.active_trades:
                    del self.active_trades[symbol]
                
                logger.info(f"📊 Position fermée: {symbol} {side} - Raison: {exit_reason}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erreur fermeture position {symbol}: {e}")
        
        return False

class TradingConsole:
    def __init__(self, tracker):
        self.tracker = tracker
        self.console_message_id = None
        
    async def create_console(self):
        """Crée la console initiale sur Telegram"""
        console_text = await self.generate_console_text()
        
        try:
            message = await self.tracker.bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=console_text,
                parse_mode='HTML'
            )
            self.console_message_id = message.message_id
            logger.info(f"Console créée avec ID: {self.console_message_id}")
            return message
        except Exception as e:
            logger.error(f"Erreur création console: {e}")
            return None
    
    async def update_console(self):
        """Met à jour la console existante"""
        if not self.console_message_id:
            return await self.create_console()
        
        console_text = await self.generate_console_text()
        
        try:
            await self.tracker.bot.edit_message_text(
                chat_id=TELEGRAM_CHANNEL_ID,
                message_id=self.console_message_id,
                text=console_text,
                parse_mode='HTML'
            )
            logger.info("Console mise à jour avec succès")
        except Exception as e:
            logger.error(f"Erreur mise à jour console: {e}")
            await self.create_console()
    
    async def send_signal_alert(self, signal: Dict, trade_executed: bool = False):
        """Envoie une alerte de signal sur Telegram"""
        emoji = "🟢" if signal['type'] == 'LONG' else "🔴"
        confidence_stars = "⭐" * int(signal['confidence'] / 20)
        trade_status = "💰 TRADE EXÉCUTÉ" if trade_executed else "📊 SIGNAL DÉTECTÉ"
        
        alert_text = f"""
{emoji} <b>{trade_status} - {signal['type']}</b> {confidence_stars}

🔸 <b>{signal['symbol']}</b> - ${signal['entry_price']:.6f}
📊 Confiance: {signal['confidence']:.1f}%

📈 <b>Take Profits:</b>
TP1: ${signal['tp1']:.6f} (0.5%)
TP2: ${signal['tp2']:.6f} (1.0%) 
TP3: ${signal['tp3']:.6f} (1.5%)

🛡️ <b>Stop Loss:</b> ${signal['stop_loss']:.6f} (0.3%)

📊 <b>Indicateurs:</b>
TEMA20: {signal['tema20']:.6f}
TEMA50: {signal['tema50']:.6f}
RSI: {signal['rsi']:.1f}
ADX: {signal['adx']:.1f}

⏰ {datetime.now().strftime('%H:%M:%S')}
        """
        
        try:
            await self.tracker.bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=alert_text,
                parse_mode='HTML'
            )
            logger.info(f"Signal envoyé: {signal['type']} {signal['symbol']}")
        except Exception as e:
            logger.error(f"Erreur envoi signal: {e}")
    
    async def send_trade_alert(self, position: Dict, action: str, price: float, reason: str = ""):
        """Envoie une alerte de trade"""
        emoji = "💰" if action == "OUVERTURE" else "📊"
        side_emoji = "🟢" if position['side'] == 'LONG' else "🔴"
        
        if action == "OUVERTURE":
            alert_text = f"""
{emoji} <b>POSITION OUVERTE</b> {side_emoji}

🔸 <b>{position['symbol']}</b> - {position['side']}
💵 Prix d'entrée: ${price:.6f}
📦 Quantité: {position['quantity']:.6f}
💰 Montant: ~{TRADE_AMOUNT_USDT} USDT

🎯 <b>Objectifs:</b>
TP1: ${position['tp1']:.6f}
TP2: ${position['tp2']:.6f}
TP3: ${position['tp3']:.6f}
SL: ${position['stop_loss']:.6f}

⏰ {datetime.now().strftime('%H:%M:%S')}
            """
        else:  # FERMETURE
            entry_price = position['entry_price']
            pnl_percentage = 0
            
            if position['side'] == 'LONG':
                pnl_percentage = ((price - entry_price) / entry_price) * 100
            else:
                pnl_percentage = ((entry_price - price) / entry_price) * 100
            
            pnl_usdt = (TRADE_AMOUNT_USDT * pnl_percentage) / 100
            pnl_emoji = "📈" if pnl_percentage > 0 else "📉"
            
            alert_text = f"""
{emoji} <b>POSITION FERMÉE</b> {side_emoji}

🔸 <b>{position['symbol']}</b> - {position['side']}
📥 Entrée: ${entry_price:.6f}
📤 Sortie: ${price:.6f}
📝 Raison: {reason}

{pnl_emoji} <b>Résultat:</b>
PnL: {pnl_percentage:+.2f}% ({pnl_usdt:+.2f} USDT)

⏰ {datetime.now().strftime('%H:%M:%S')}
            """
        
        try:
            await self.tracker.bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=alert_text,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Erreur envoi alerte trade: {e}")
    
    async def generate_console_text(self):
        """Génère le texte de la console"""
        watched_cryptos = self.tracker.db.get_watched_cryptos()
        
        if not watched_cryptos:
            return "📊 <b>Console Scalping Bot</b>\n\n❌ Aucune crypto surveillée\n\nUtilise /add BTCUSDT pour ajouter une crypto"
        
        # Récupérer les positions ouvertes
        open_positions = self.tracker.db.get_open_positions()
        total_positions = len(open_positions)
        
        # Calculer le PnL total
        total_pnl = 0.0
        for position in open_positions:
            current_price = self.tracker.binance.get_current_price(position['symbol'])
            if current_price:
                entry_price = position['entry_price']
                if position['side'] == 'LONG':
                    pnl_percentage = ((current_price - entry_price) / entry_price) * 100
                else:
                    pnl_percentage = ((entry_price - current_price) / entry_price) * 100
                
                position_pnl = (TRADE_AMOUNT_USDT * pnl_percentage) / 100
                total_pnl += position_pnl
        
        console_lines = [
            "🤖 <b>SCALPING BOT CONSOLE</b>",
            f"⚡ Mode: {'TESTNET' if USE_TESTNET else 'LIVE TRADING'}",
            f"💰 Auto-Trading: {'✅ ACTIVÉ' if ENABLE_AUTO_TRADING else '❌ DÉSACTIVÉ'}",
            f"🕐 Mis à jour: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📊 <b>POSITIONS: {total_positions}</b> | PnL: {total_pnl:+.2f} USDT",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ]
        
        active_signals = 0
        for symbol in watched_cryptos:
            crypto_data = await self.get_crypto_summary(symbol)
            console_lines.append(crypto_data)
            if "🟢" in crypto_data or "🔴" in crypto_data:
                active_signals += 1
        
        console_lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📈 Total surveillé: {len(watched_cryptos)} cryptos",
            f"🎯 Signaux actifs: {active_signals}",
            f"⚡ Analyse: Toutes les 30 secondes",
            f"💵 Montant par trade: {TRADE_AMOUNT_USDT} USDT",
            "",
            "💡 <b>Commandes:</b>",
            "/add BTCUSDT - Ajouter une crypto",
            "/remove BTCUSDT - Supprimer une crypto", 
            "/list - Voir la liste des cryptos",
            "/positions - Positions ouvertes",
            "/stats - Statistiques de performance"
        ])
        
        return "\n".join(console_lines)
    
    async def get_crypto_summary(self, symbol: str) -> str:
        """Génère un résumé pour une crypto"""
        current_price = self.tracker.binance.get_current_price(symbol)
        if not current_price:
            return f"❌ <b>{symbol}</b> - Erreur prix"
        
        # Vérifier s'il y a une position ouverte
        open_positions = self.tracker.db.get_open_positions(symbol)
        position_status = ""
        
        if open_positions:
            position = open_positions[0]
            entry_price = position['entry_price']
            side = position['side']
            
            if side == 'LONG':
                pnl_percentage = ((current_price - entry_price) / entry_price) * 100
            else:
                pnl_percentage = ((entry_price - current_price) / entry_price) * 100
            
            pnl_emoji = "📈" if pnl_percentage > 0 else "📉"
            side_emoji = "🟢" if side == 'LONG' else "🔴"
            position_status = f" | {side_emoji} {pnl_emoji} {pnl_percentage:+.1f}%"
        
        # Récupérer les indicateurs récents
        indicators = await self.get_latest_indicators(symbol)
        signal_status = self.get_signal_status(indicators)
        variation_24h = await self.get_24h_variation(symbol)
        
        return f"{signal_status} <b>{symbol}</b> - ${current_price:.6f}\n   📊 24h: {variation_24h:+.2f}% | RSI: {indicators.get('rsi', 0):.1f} | ADX: {indicators.get('adx', 0):.1f}{position_status}"
    
    async def get_latest_indicators(self, symbol: str) -> Dict:
        """Récupère les derniers indicateurs calculés"""
        conn = sqlite3.connect(self.tracker.db.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT tema20, tema50, rsi, adx, volatility FROM price_history 
            WHERE symbol = ? AND timeframe = '15m' 
            ORDER BY open_time DESC LIMIT 1
        ''', (symbol,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'tema20': result[0] or 0,
                'tema50': result[1] or 0,
                'rsi': result[2] or 0,
                'adx': result[3] or 0,
                'volatility': result[4] or 0
            }
        return {'tema20': 0, 'tema50': 0, 'rsi': 0, 'adx': 0, 'volatility': 0}
    
    def get_signal_status(self, indicators: Dict) -> str:
        """Détermine le statut du signal"""
        if not indicators or indicators['rsi'] == 0:
            return "⚪"
        
        rsi = indicators['rsi']
        adx = indicators['adx']
        
        if adx > 25:
            if 50 < rsi < 70:
                return "🟢"  # Potentiel LONG
            elif 30 < rsi < 50:
                return "🔴"  # Potentiel SHORT
        
        return "🟡"  # Attente
    
    async def get_24h_variation(self, symbol: str) -> float:
        """Calcule la variation 24h"""
        try:
            params = {'symbol': symbol.upper()}
            response = requests.get(f"{self.tracker.binance.base_url}/ticker/24hr", params=params)
            data = response.json()
            return float(data['priceChangePercent'])
        except:
            return 0.0

class ScalpingBot:
    def __init__(self):
        self.db = DatabaseManager(DB_PATH)
        self.binance = BinanceClient()
        self.analyzer = TechnicalAnalyzer()
        self.trading_engine = TradingEngine(self.binance, self.db)
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.console = TradingConsole(self)
        self.is_running = False
        self.analysis_task = None
        self.update_task = None
        self.trading_task = None
        
    async def process_new_crypto(self, symbol: str) -> bool:
        """Traite l'ajout d'une nouvelle crypto"""
        if not self.binance.validate_symbol(symbol):
            logger.warning(f"Symbole {symbol} non trouvé sur Binance")
            return False
        
        if not self.db.add_crypto(symbol):
            logger.info(f"Symbole {symbol} déjà surveillé")
            return False
        
        await self.analyze_crypto(symbol)
        return True
    
    async def analyze_crypto(self, symbol: str):
        """Analyse une crypto et génère des signaux"""
        # Analyse sur 15min (signal principal)
        klines_15m = self.binance.get_klines(symbol, "15m", 200)
        if not klines_15m:
            return
        
        indicators_15m = self.analyzer.calculate_all_indicators(klines_15m)
        if not indicators_15m:
            return
        
        # Sauvegarde des données 15min
        self.db.save_price_data(symbol, "15m", klines_15m, indicators_15m)
        
        # Génération du signal
        signal = self.analyzer.generate_scalping_signals(indicators_15m, symbol)
        
        if signal:
            # Confirmation sur 1min
            klines_1m = self.binance.get_klines(symbol, "1m", 60)
            if klines_1m:
                indicators_1m = self.analyzer.calculate_all_indicators(klines_1m)
                if self._confirm_signal_1m(signal, indicators_1m):
                    # Sauvegarder le signal
                    self.db.save_signal(symbol, signal)
                    
                    # Exécuter le trade automatiquement
                    trade_executed = False
                    if ENABLE_AUTO_TRADING:
                        trade_executed = self.trading_engine.execute_signal(signal)
                        if trade_executed:
                            position_data = {
                                'symbol': symbol,
                                'side': signal['type'],
                                'entry_price': signal['entry_price'],
                                'quantity': self.binance.calculate_trade_quantity(symbol, TRADE_AMOUNT_USDT, signal['entry_price']),
                                'tp1': signal['tp1'],
                                'tp2': signal['tp2'],
                                'tp3': signal['tp3'],
                                'stop_loss': signal['stop_loss']
                            }
                            await self.console.send_trade_alert(position_data, "OUVERTURE", signal['entry_price'])
                    
                    # Envoyer l'alerte signal
                    await self.console.send_signal_alert(signal, trade_executed)
                    logger.info(f"Signal confirmé: {signal['type']} {symbol} - Trade: {'Exécuté' if trade_executed else 'Alerte seulement'}")
    
    def _confirm_signal_1m(self, signal_15m: Dict, indicators_1m: Dict) -> bool:
        """Confirme le signal 15min avec l'analyse 1min"""
        if not indicators_1m or len(indicators_1m['close']) < 20:
            return False
        
        # Vérification de la cohérence des indicateurs sur 1min
        tema20_1m = indicators_1m['tema20'][-1]
        current_price_1m = indicators_1m['close'][-1]
        rsi_1m = indicators_1m['rsi'][-1]
        
        if np.isnan(tema20_1m) or np.isnan(rsi_1m):
            return False
        
        if signal_15m['type'] == 'LONG':
            return (current_price_1m > tema20_1m and 
                   rsi_1m > 45 and rsi_1m < 75)
        else:  # SHORT
            return (current_price_1m < tema20_1m and 
                   rsi_1m < 55 and rsi_1m > 25)
    
    async def analyze_all_cryptos(self):
        """Analyse toutes les cryptos surveillées"""
        watched_cryptos = self.db.get_watched_cryptos()
        logger.info(f"Analyse de {len(watched_cryptos)} cryptos")
        
        for symbol in watched_cryptos:
            try:
                await self.analyze_crypto(symbol)
                await asyncio.sleep(0.1)  # Éviter le rate limiting
            except Exception as e:
                logger.error(f"Erreur analyse {symbol}: {e}")
    
    async def start_analysis_loop(self):
        """Lance l'analyse continue"""
        self.is_running = True
        
        async def analysis_loop():
            while self.is_running:
                try:
                    logger.info("🔍 Début de l'analyse des cryptos")
                    await self.analyze_all_cryptos()
                    logger.info("✅ Analyse terminée")
                    
                    # Attendre 30 secondes
                    for i in range(6):  # 6 * 5 sec = 30 sec
                        if not self.is_running:
                            break
                        await asyncio.sleep(5)
                        
                except Exception as e:
                    logger.error(f"Erreur dans la boucle d'analyse: {e}")
                    await asyncio.sleep(10)
        
        self.analysis_task = asyncio.create_task(analysis_loop())
    
    async def start_trading_monitor(self):
        """Lance le monitoring des trades"""
        async def trading_loop():
            while self.is_running:
                try:
                    if ENABLE_AUTO_TRADING:
                        self.trading_engine.check_exit_conditions()
                    
                    # Vérifier toutes les 10 secondes
                    for i in range(2):  # 2 * 5 sec = 10 sec
                        if not self.is_running:
                            break
                        await asyncio.sleep(5)
                        
                except Exception as e:
                    logger.error(f"Erreur monitoring trades: {e}")
                    await asyncio.sleep(10)
        
        self.trading_task = asyncio.create_task(trading_loop())
        
    async def start_console_updates(self, interval_minutes: int = 2):
        """Lance les mises à jour de la console"""
        await self.console.create_console()
        
        async def update_loop():
            while self.is_running:
                try:
                    await self.console.update_console()
                    
                    # Attendre 2 minutes
                    for i in range(interval_minutes * 12):  # 12 * 5 sec = 1 min
                        if not self.is_running:
                            break
                        await asyncio.sleep(5)
                        
                except Exception as e:
                    logger.error(f"Erreur mise à jour console: {e}")
                    await asyncio.sleep(30)
        
        self.update_task = asyncio.create_task(update_loop())
        
    def stop_bot(self):
        """Arrête le bot"""
        self.is_running = False
        if self.analysis_task:
            self.analysis_task.cancel()
        if self.update_task:
            self.update_task.cancel()
        if self.trading_task:
            self.trading_task.cancel()
        logger.info("Bot arrêté")

# Handlers pour les commandes Telegram
async def add_crypto_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /add pour ajouter une crypto"""
    if not context.args:
        await update.message.reply_text("Usage: /add BTCUSDT")
        return
    
    symbol = context.args[0].upper()
    bot = context.bot_data.get('bot')
    
    if bot:
        success = await bot.process_new_crypto(symbol)
        if success:
            await update.message.reply_text(f"✅ {symbol} ajouté au scalping bot!")
            await bot.console.update_console()
        else:
            await update.message.reply_text(f"❌ Impossible d'ajouter {symbol}")
    else:
        await update.message.reply_text("❌ Bot non initialisé")

async def remove_crypto_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /remove pour supprimer une crypto"""
    if not context.args:
        await update.message.reply_text("Usage: /remove BTCUSDT")
        return
    
    symbol = context.args[0].upper()
    bot = context.bot_data.get('bot')
    
    if bot:
        conn = sqlite3.connect(bot.db.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE watched_cryptos SET status = 'inactive' WHERE symbol = ?",
            (symbol,)
        )
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if success:
            await update.message.reply_text(f"✅ {symbol} supprimé du scalping!")
            await bot.console.update_console()
        else:
            await update.message.reply_text(f"❌ {symbol} non trouvé")

async def list_cryptos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /list pour voir les cryptos surveillées"""
    bot = context.bot_data.get('bot')
    
    if bot:
        cryptos = bot.db.get_watched_cryptos()
        if cryptos:
            message = "📈 <b>Cryptos en scalping:</b>\n\n"
            for crypto in cryptos:
                price = bot.binance.get_current_price(crypto)
                price_str = f"${price:.6f}" if price else "Erreur"
                message += f"⚡ {crypto} - {price_str}\n"
        else:
            message = "❌ Aucune crypto en surveillance"
        
        await update.message.reply_text(message, parse_mode='HTML')

async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /positions pour voir les positions ouvertes"""
    bot = context.bot_data.get('bot')
    
    if bot:
        positions = bot.db.get_open_positions()
        if positions:
            message = "💰 <b>Positions Ouvertes:</b>\n\n"
            total_pnl = 0.0
            
            for position in positions:
                symbol = position['symbol']
                side = position['side']
                entry_price = position['entry_price']
                current_price = bot.binance.get_current_price(symbol)
                
                if current_price:
                    if side == 'LONG':
                        pnl_percentage = ((current_price - entry_price) / entry_price) * 100
                    else:
                        pnl_percentage = ((entry_price - current_price) / entry_price) * 100
                    
                    position_pnl = (TRADE_AMOUNT_USDT * pnl_percentage) / 100
                    total_pnl += position_pnl
                    
                    pnl_emoji = "📈" if pnl_percentage > 0 else "📉"
                    side_emoji = "🟢" if side == 'LONG' else "🔴"
                    
                    message += f"{side_emoji} <b>{symbol}</b> - {side}\n"
                    message += f"   💵 {entry_price:.6f} → {current_price:.6f}\n"
                    message += f"   {pnl_emoji} PnL: {pnl_percentage:+.2f}% ({position_pnl:+.2f} USDT)\n\n"
            
            message += f"📊 <b>PnL Total: {total_pnl:+.2f} USDT</b>"
        else:
            message = "❌ Aucune position ouverte"
        
        await update.message.reply_text(message, parse_mode='HTML')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /stats pour voir les statistiques"""
    bot = context.bot_data.get('bot')
    
    if bot:
        conn = sqlite3.connect(bot.db.db_path)
        cursor = conn.cursor()
        
        # Compter les signaux
        cursor.execute("SELECT COUNT(*) FROM trading_signals WHERE created_at > datetime('now', '-24 hours')")
        signals_24h = cursor.fetchone()[0]
        
        cursor.execute("SELECT signal_type, COUNT(*) FROM trading_signals WHERE created_at > datetime('now', '-24 hours') GROUP BY signal_type")
        signal_breakdown = cursor.fetchall()
        
        # Statistiques des trades
        cursor.execute("SELECT COUNT(*), AVG(pnl), SUM(pnl), COUNT(CASE WHEN pnl > 0 THEN 1 END) FROM completed_trades")
        trade_stats = cursor.fetchone()
        
        conn.close()
        
        total_trades = trade_stats[0] or 0
        avg_pnl = trade_stats[1] or 0
        total_pnl = trade_stats[2] or 0
        winning_trades = trade_stats[3] or 0
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        stats_text = f"""
📊 <b>Statistiques Scalping Bot</b>

🔥 <b>Signaux (24h):</b>
• Total: {signals_24h}
"""
        
        for signal_type, count in signal_breakdown:
            emoji = "🟢" if signal_type == "LONG" else "🔴"
            stats_text += f"• {emoji} {signal_type}: {count}\n"
        
        stats_text += f"""

💰 <b>Performance Trading:</b>
• Trades totaux: {total_trades}
• Trades gagnants: {winning_trades}
• Win Rate: {win_rate:.1f}%
• PnL moyen: {avg_pnl:+.2f} USDT
• PnL total: {total_pnl:+.2f} USDT

⚡ <b>Configuration:</b>
• Mode: {"TESTNET" if USE_TESTNET else "LIVE TRADING"}
• Auto-Trading: {"✅ ON" if ENABLE_AUTO_TRADING else "❌ OFF"}
• Montant/Trade: {TRADE_AMOUNT_USDT} USDT
• Timeframes: 15min + 1min
• Indicateurs: TEMA 20/50, RSI, ADX
• TP: 0.5%, 1.0%, 1.5% | SL: 0.3%
        """
        
        await update.message.reply_text(stats_text, parse_mode='HTML')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /help"""
    help_text = f"""
🤖 <b>Scalping Bot - Guide Complet</b>

⚡ <b>Stratégie:</b>
• Timeframes: 15min + 1min
• Indicateurs: TEMA 20/50, RSI, ADX, Bollinger
• Signal LONG: Prix > TEMA20 > TEMA50, RSI 50-70, ADX > 25
• Signal SHORT: Prix < TEMA20 < TEMA50, RSI 30-50, ADX > 25

🎯 <b>Gestion des risques:</b>
• TP1: 0.5% | TP2: 1.0% | TP3: 1.5%
• Stop Loss: 0.3%
• Montant par trade: {TRADE_AMOUNT_USDT} USDT

💰 <b>Trading Automatique:</b>
• Mode: {"TESTNET" if USE_TESTNET else "LIVE TRADING"}
• Status: {"✅ ACTIVÉ" if ENABLE_AUTO_TRADING else "❌ DÉSACTIVÉ"}
• Max positions/crypto: {MAX_POSITIONS_PER_SYMBOL}

📱 <b>Commandes:</b>
/add BTCUSDT - Ajouter une crypto
/remove BTCUSDT - Supprimer une crypto
/list - Cryptos surveillées
/positions - Positions ouvertes
/stats - Statistiques de performance

🔄 Analyse automatique toutes les 30 secondes!
    """
    await update.message.reply_text(help_text, parse_mode='HTML')

async def post_init(application):
    """Fonction appelée après l'initialisation de l'application"""
    bot = application.bot_data.get('bot')
    if bot:
        # Ajouter quelques cryptos par défaut
        default_cryptos = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'BNBUSDT']
        for crypto in default_cryptos:
            await bot.process_new_crypto(crypto)
            await asyncio.sleep(0.5)
        
        # Démarrer les boucles d'analyse, trading et mise à jour
        await bot.start_analysis_loop()
        await bot.start_trading_monitor()
        await bot.start_console_updates(interval_minutes=2)
        
        logger.info("✅ Scalping Bot avec trading automatique initialisé!")

def main():
    """Point d'entrée principal"""
    # Créer l'application Telegram
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Créer le bot de scalping
    scalping_bot = ScalpingBot()
    application.bot_data['bot'] = scalping_bot
    
    # Ajouter les handlers
    application.add_handler(CommandHandler("add", add_crypto_command))
    application.add_handler(CommandHandler("remove", remove_crypto_command))
    application.add_handler(CommandHandler("list", list_cryptos_command))
    application.add_handler(CommandHandler("positions", positions_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Configuration post-initialisation
    application.post_init = post_init
    
    # Messages de démarrage
    print("🚀 Scalping Bot avec Trading Automatique démarré!")
    print(f"⚡ Mode: {'TESTNET' if USE_TESTNET else 'LIVE TRADING'}")
    print(f"💰 Auto-Trading: {'✅ ACTIVÉ' if ENABLE_AUTO_TRADING else '❌ DÉSACTIVÉ'}")
    print(f"💵 Montant par trade: {TRADE_AMOUNT_USDT} USDT")
    print("📊 Console Telegram active")
    print("💡 Utilisez /help pour voir les commandes")
    
    # Démarrer le bot
    try:
        application.run_polling()
    except KeyboardInterrupt:
        logger.info("Arrêt du bot demandé")
        scalping_bot.stop_bot()
    except Exception as e:
        logger.error(f"Erreur critique: {e}")
        scalping_bot.stop_bot()

if __name__ == "__main__":
    main()
