import pandas as pd

import ta
# Calcul du RSI

def calculate_rsi_14(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    loss = loss.replace(0, 1e-10)  # Empèche la division par zéro
    rs = gain / loss
    rsi_14 = 100 - (100 / (1 + rs))
    return rsi_14

def calculate_rsi_50(data, window=50):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    loss = loss.replace(0, 1e-10)  # Empèche la division par zéro
    rs = gain / loss
    rsi_50 = 100 - (100 / (1 + rs))
    return rsi_50

# Fonction pour calculer une moyenne mobile simple (SMA)
def SMA(series, period):
    return series.rolling(window=period).mean()

# Fonction pour calculer MA100
def calculate_MA100(data):
    return SMA(data, 100)

# Fonction pour calculer MA200
def calculate_MA200(data):
    return SMA(data, 200)


# Calcul de l'EMA
def EMA(series, period):
    return series.ewm(span=period, adjust=False).mean()

# Calcul du TEMA
def TEMA(series, period):
    ema1 = EMA(series, period)
    ema2 = EMA(ema1, period)
    ema3 = EMA(ema2, period)
    return 3 * (ema1 - ema2) + ema3


def calculate_indicators(df):
    """Calcule RSI et TEMA."""
    df['RSI14'] = calculate_rsi_14(df['close'])
    df['RSI50'] = calculate_rsi_50(df['close']) 
    df['TEMA20'] = TEMA(df['close'], 20)
    df['TEMA50'] = TEMA(df['close'], 50)
    return df

