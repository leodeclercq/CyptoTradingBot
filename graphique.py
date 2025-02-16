import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# 🔗 Connexion à la base SQLite
conn = sqlite3.connect("C:\\bot_trading\\trading_data.db")  # Remplace par ton fichier
query = "SELECT time, open, high, low, close, RSI14, RSI50, TEMA20, TEMA50 FROM market_data"
df = pd.read_sql_query(query, conn)
conn.close()

# 🕒 Convertir time en datetime
df["time"] = pd.to_datetime(df["time"])

# 🔍 Ne garder que les 100 dernières entrées
df = df.tail(100)

# 📊 Sélection des indicateurs à afficher
indicateurs = {
    "close": True,  # Prix de clôture toujours affiché
    "TEMA20": True,
    "TEMA50": True,
    "RSI14": False,
    "RSI50": False,
}

# 🎨 Créer la figure et les sous-graphiques
fig, ax1 = plt.subplots(figsize=(12, 6))

# 📈 Prix (Bougies)
ax1.plot(df["time"], df["close"], label="Close Price", color="black", linewidth=1.5)
if indicateurs["TEMA20"]:
    ax1.plot(df["time"], df["TEMA20"], label="TEMA 20", color="blue", linestyle="dashed")
if indicateurs["TEMA50"]:
    ax1.plot(df["time"], df["TEMA50"], label="TEMA 50", color="purple", linestyle="dashed")

ax1.set_ylabel("Prix")
ax1.set_title("Prix et Indicateurs TEMA")
ax1.legend()
ax1.grid()

# 📉 RSI (sous-graphique)
ax2 = ax1.twinx()
if indicateurs["RSI14"]:
    ax2.plot(df["time"], df["RSI14"], label="RSI 14", color="red", linestyle="dotted")
if indicateurs["RSI50"]:
    ax2.plot(df["time"], df["RSI50"], label="RSI 50", color="green", linestyle="dotted")

ax2.set_ylabel("RSI")
ax2.axhline(70, color="gray", linestyle="dashed")  # Seuil de surachat
ax2.axhline(30, color="gray", linestyle="dashed")  # Seuil de survente
ax2.legend(loc="upper right")

# 🔄 Rotation des dates pour meilleure lisibilité
plt.xticks(rotation=45)
plt.show()
