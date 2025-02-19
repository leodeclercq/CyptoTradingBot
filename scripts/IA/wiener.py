import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 🔗 Connexion à la base SQLite et récupération des données
conn = sqlite3.connect("C:\\zarov\\trading_data.db")  # Remplace par ton fichier
query = "SELECT time, close FROM market_data"
df = pd.read_sql_query(query, conn)
conn.close()

# 🕒 Conversion de la colonne time en datetime
df["time"] = pd.to_datetime(df["time"])

# 🔍 Garder les données des dernières 24 heures (ici, on suppose que les données sont enregistrées chaque seconde)
df = df.tail(60*50)

# 📊 Affichage des prix de clôture sur les 24 dernières heures
fig, ax1 = plt.subplots(figsize=(12, 6))
ax1.plot(df["time"], df["close"], label="Prix de clôture", color="black", linewidth=1.5)
ax1.set_ylabel("Prix")
ax1.set_title("Prix sur les dernières 24h")
ax1.legend()
ax1.grid()
plt.xticks(rotation=45)
plt.show()

# 📈 Calcul des rendements logarithmiques
# On prend le logarithme des prix et on calcule la différence entre chaque seconde
log_returns = np.diff(np.log(df["close"]))
mu_sec = 0.00000033                     # Dérive par seconde
sigma_sec = 0.0001         # Volatilité par seconde

# Affichage des paramètres sur 24h pour information
drift_24h = mu_sec * 60*50
volatility_24h = sigma_sec * np.sqrt(60*50)
print(f"Dérive par seconde : {mu_sec:.8f}")
print(f"Dérive sur 24h     : {drift_24h:.4f}")
print(f"Volatilité par sec : {sigma_sec:.8f}")
print(f"Volatilité sur 24h : {volatility_24h:.4f}")

# 🎲 Simulation du modèle GBM pour les 10 prochaines minutes
T = 5 * 60       # Durée de la simulation : 10 minutes en secondes
dt = 1            # Pas de temps : 1 seconde
N = int(T / dt)   # Nombre d'étapes
t = np.linspace(0, T, N + 1)

# Condition initiale : dernier prix observé
S0 = df["close"].iloc[-1]
np.random.seed(42)
# Simulation vectorisée du GBM
# On utilise la formule : S(t+dt) = S(t) * exp((mu_sec - 0.5 * sigma_sec^2) * dt + sigma_sec * sqrt(dt) * Z)
increments = (mu_sec - 0.5 * sigma_sec**2) * dt + sigma_sec * np.sqrt(dt) * np.random.normal(size=N)
log_S = np.log(S0) + np.concatenate(([0], np.cumsum(increments)))
S = np.exp(log_S)

# 📉 Affichage de la trajectoire simulée
plt.figure(figsize=(10, 5))
plt.plot(t, S, label="Prix simulé (GBM)", color="blue")
plt.xlabel("Temps (secondes)")
plt.ylabel("Prix")
plt.title("Simulation GBM sur les 10 prochaines minutes")
plt.legend()
plt.grid()
plt.show()
