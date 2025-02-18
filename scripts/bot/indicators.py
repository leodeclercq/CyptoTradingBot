import pandas as pd
# garde en mémoire x éléments de liste
from collections import deque
import ta
# Calcul du RSI
#  calcul scientifique, tableau, db etc
import numpy as np


# Calcul de l'EMA
def EMA(series, period):
    return series.ewm(span=period, adjust=False).mean()

# Calcul du TEMA
def TEMA(series, period):
    ema1 = EMA(series, period)
    ema2 = EMA(ema1, period)
    ema3 = EMA(ema2, period)
    return 3 * (ema1 - ema2) + ema3
    
tema_window =deque(maxlen=21)

TEMA_period = 20  # nombre de points pour calculer TEMA20
slope_window = 3

def compute_slope(data, window=slope_window):
    if len(data) < window:
        return None
    y = np.array(data[-window:], dtype=float)
    x = np.arange(window)
    slope, _ = np.polyfit(x, y, 1)
    return slope



def calculate_indicators(df):
    """Calcule slope et TEMA."""
    df['TEMA20'] = TEMA(df['close'], 20)
    tema_window.append(df['TEMA20'])
    df['TEMA50'] = TEMA(df['close'], 50)
    df['slope'] = compute_slope(list(tema_window), window=slope_window)
    return df
