HELLO !!!

# I A   T R A D E   B O T

[![zarov](https://github.com/user-attachments/assets/1d904d1b-2956-4002-a799-819b797bd1e7)](https://github.com/leodeclercq)

IA TRADE BOT est un bot de trading crypto (BTC/USDT) en Python, gratuit et open source. Il utilise l'API Binance pour récupérer les informations de marché et exécuter les ordres de trading, ainsi que l'API Telegram pour l'interface utilisateur (mise à jour des infos en live 💚). Un script permet de récupérer les données de backtest depuis la date limite disponible sur Binance (modifiable pour d'autres exchanges). La stratégie et son optimisation sont déjà en cours de développement, toute aide est la bienvenue.

SVP renseignez-vous [Notes spécifique Binance Exchange](exchanges.md) pour plus d'info, configuration et frais.

- [X] [Binance](https://www.binance.com/)


investissement (1% de bénefice/jour = 0,01) : 

C = C(0) * (1+0,01)**jours

Si 100€ = C(0)   C = 3 778,34€ (1 an = 365 jours)

C = 136,14€ (1 mois = 31 jours)
                              
Si 1000€ = C(0) C = 37 783,43€ (1 an = 365 jours)

C = 1 361,33€ (1 mois = 31 jours)

## Close : dernier prix d'un actif à la fin d'une bougie (1 /s, 1/m).

### TEMA : moyenne mobile exponentielle triple sur  périodes, utilisée pour lisser les prix et détecter les tendances plus rapidement

#### 1. Architecture du bot de trading #IA 📊
   
📌 Données en entrée (1/s) :

•	Prix ‘Close’ en temps réel (Binance Websocket via API).

•	Indicateurs techniques : TEMA20, TEMA50.

📌 Traitement des données :

•	Calcul des indicateurs  (TEMA20, TEMA50)).

•	Normalisation des données (Close. TEMA20, TEMA50).

•	#Création d'une structure de données utilisable par le modèle IA

📌 Prise de décision IA :

•	#Un modèle de régression logistique ou un réseau de neurones (LSTM) donne une probabilité que le prix monte ou baisse.

•	Si Minima (11 Derniers points), Pente > 0.06 et TEMA20 Convexe par rapport à TEMA50 (=croisement) avec un décalage de -0.8 sur TEMA50 , ACHAT.

•	Si Maxima(11 Derniers points), Pente < -0.084 et TEMA20 Concave par rapport à TEMA50 (=croisement) avec un décalage de +0.45 sur TEMA50 , VENTE.

•	#Si P(hausse) > 60%, ACHAT.(Validation signal)

•	#Si P(baisse) > 60%, ouvrir un VENTE.(Validation signal)

📌 Exécution des ordres :

•	Utilisation d’ordres du marché.

•	Backtesting sur des données historiques pour optimiser la stratégie.
________________________________________

##### 2. Exemples Résultats bot de tranding#IA 🚀
   
📌 EXEMPLE ACHAT :

[Sun Feb 16 13:20:22 2025] ❤️ n  (pente: 0.209656):( (TEMA20: 97233.28 >= TEMA50: 97233.15)💰: 97232.870000

[Sun Feb 16 13:20:23 2025] ❤️ n  (pente: 0.148419):( (TEMA20: 97233.40 >= TEMA50: 97233.40)💰: 97232.870000

[Sun Feb 16 13:20:24 2025] 💚 U (pente: 0.097707):) (TEMA20: 97233.48 < TEMA50: 97233.62) 💰: 97232.870000

[Sun Feb 16 13:20:25 2025] 💚 U (pente: 0.055870):) (TEMA20: 97233.51 < TEMA50: 97233.80) 💰: 97232.860000

[Sun Feb 16 13:20:26 2025] 💚 U (pente: 0.024087):) (TEMA20: 97233.52 < TEMA50: 97233.97) 💰: 97232.870000

[Sun Feb 16 13:20:27 2025] 💚 U (pente: 0.000666):) (TEMA20: 97233.51 < TEMA50: 97234.11) 💰: 97232.870000

[Sun Feb 16 13:20:28 2025] 💚 U (pente: -0.018427):) (TEMA20: 97233.49 < TEMA50: 97234.22) 💰: 97232.870000

[Sun Feb 16 13:20:29 2025] 🔥ACHAT à 💰97236.510000 (pente: 0.439405 ), 🪙: 0.001032, 💲 : 0.00

[Sun Feb 16 13:20:29 2025] 💚 U (pente: 0.439405):) (TEMA20: 97234.39 < TEMA50: 97234.73) 💰: 97236.510000

[Sun Feb 16 13:20:30 2025] 💚 U (pente: 0.815618):) (TEMA20: 97235.12 < TEMA50: 97235.19) 💰: 97236.520000

[Sun Feb 16 13:20:31 2025] ❤️ n  (pente: 0.649447):( (TEMA20: 97235.69 >= TEMA50: 97235.60)💰: 97236.520000

[Sun Feb 16 13:20:32 2025] ❤️ n  (pente: 0.509620):( (TEMA20: 97236.14 >= TEMA50: 97235.97)💰: 97236.520000


[![Capture d'écran 2025-02-16 132744](https://github.com/user-attachments/assets/1299910d-5add-42fc-865c-06c460aa51fc)](https://www.binance.com/en/trade/BTC_FDUSD)

📌 EXEMPLE VENTE :

[Sun Feb 16 13:23:05 2025] 💚 U (pente: 0.000045):) (TEMA20: 97239.91 < TEMA50: 97239.92) 💰: 97239.920000

[Sun Feb 16 13:23:06 2025] 💚 U (pente: 0.000054):) (TEMA20: 97239.91 < TEMA50: 97239.92) 💰: 97239.910000

[Sun Feb 16 13:23:07 2025] ❤️ n  (pente: 1.260586):( (TEMA20: 97242.44 >= TEMA50: 97241.02)💰: 97249.640000

[Sun Feb 16 13:23:08 2025] ❤️ n  (pente: 2.291606):( (TEMA20: 97244.50 >= TEMA50: 97242.03)💰: 97249.650000

[Sun Feb 16 13:23:09 2025] ❤️ n  (pente: 1.863139):( (TEMA20: 97246.16 >= TEMA50: 97242.97)💰: 97249.640000

[Sun Feb 16 13:23:10 2025] ❤️ n  (pente: 1.613579):( (TEMA20: 97247.72 >= TEMA50: 97243.93)💰: 97250.510000

[Sun Feb 16 13:23:11 2025] ❤️ n  (pente: 1.462244):( (TEMA20: 97249.09 >= TEMA50: 97244.86)💰: 97250.970000

[Sun Feb 16 13:23:12 2025] ❤️ n  (pente: 1.250160):( (TEMA20: 97250.22 >= TEMA50: 97245.74)💰: 97251.210000

[Sun Feb 16 13:23:13 2025] ❤️ n  (pente: 1.102502):( (TEMA20: 97251.29 >= TEMA50: 97246.63)💰: 97251.910000

[Sun Feb 16 13:23:14 2025] ❤️ n  (pente: 0.959551):( (TEMA20: 97252.14 >= TEMA50: 97247.46)💰: 97252.010000

[Sun Feb 16 13:23:15 2025] ❤️ n  (pente: 0.750150):( (TEMA20: 97252.79 >= TEMA50: 97248.21)💰: 97252.020000

[Sun Feb 16 13:23:16 2025] ❤️ n  (pente: 0.564003):( (TEMA20: 97253.27 >= TEMA50: 97248.90)💰: 97252.020000

[Sun Feb 16 13:23:17 2025] ❤️ n  (pente: 0.409722):( (TEMA20: 97253.61 >= TEMA50: 97249.53)💰: 97252.020000

[Sun Feb 16 13:23:18 2025] ❤️ n  (pente: 0.282487):( (TEMA20: 97253.84 >= TEMA50: 97250.09)💰: 97252.010000

[Sun Feb 16 13:23:19 2025] ❤️ n  (pente: 0.180747):( (TEMA20: 97253.97 >= TEMA50: 97250.61)💰: 97252.020000

[Sun Feb 16 13:23:20 2025] ❤️ n  (pente: 0.100455):( (TEMA20: 97254.04 >= TEMA50: 97251.07)💰: 97252.020000

[Sun Feb 16 13:23:21 2025] ❤️ n  (pente: 0.034248):( (TEMA20: 97254.04 >= TEMA50: 97251.49)💰: 97252.010000

[Sun Feb 16 13:23:22 2025] ❤️ n  (pente: -0.016237):( (TEMA20: 97254.00 >= TEMA50: 97251.86)💰: 97252.020000

[Sun Feb 16 13:23:23 2025] ❤️ n  (pente: -0.053652):( (TEMA20: 97253.93 >= TEMA50: 97252.19)💰: 97252.020000

[Sun Feb 16 13:23:24 2025] 🔥VENTE à 💰97252.010000 (pente: -0.084144), 🪙: 0.000000, 💲 : 100.396936,prix d'achat 0.00

[Sun Feb 16 13:23:24 2025] ❤️ n  (pente: -0.084144):( (TEMA20: 97253.84 >= TEMA50: 97252.48)💰: 97252.010000

[Sun Feb 16 13:23:25 2025] ❤️ n  (pente: -0.105029):( (TEMA20: 97253.72 >= TEMA50: 97252.74)💰: 97252.020000

[Sun Feb 16 13:23:26 2025] ❤️ n  (pente: -0.119344):( (TEMA20: 97253.60 >= TEMA50: 97252.97)💰: 97252.010000

[Sun Feb 16 13:23:27 2025] ❤️ n  (pente: -0.129622):( (TEMA20: 97253.46 >= TEMA50: 97253.16)💰: 97252.010000

[Sun Feb 16 13:23:28 2025] 💚 U (pente: -0.134075):) (TEMA20: 97253.33 < TEMA50: 97253.33) 💰: 97252.010000

[Sun Feb 16 13:23:29 2025] 💚 U (pente: -0.135153):) (TEMA20: 97253.19 < TEMA50: 97253.48) 💰: 97252.010000

[![Capture d'écran 2025-02-16 132827](https://github.com/user-attachments/assets/e5757784-49d7-4c53-952d-a52f763c3156)](https://www.binance.com/en/trade/BTC_FDUSD)

 

•	Utilisation d’orde du marcher.

•	Backtesting sur des données historiques pour optimiser la stratégie.

[![Capture d'écran 2025-02-16 132711](https://github.com/user-attachments/assets/3d12566a-1aad-4b03-bd37-90bed44266a7)](https://www.binance.com/en/trade/BTC_FDUSD)


________________________________________

###### 3. Optimisations et prochaines étapes 📈📊 🚀
   
📌 To Do :

•	Optimisation et intégrations d’indicateurs.  Ajout d’IA (Régression Logistique, LTSM).

________________________________________

####### 4. Bot Simple 🚀
   
📌 stratégie (1/m) :

•	Si TEMA20 > TEMA50 , ACHAT.

•	Si TEMA20 < TEMA50, VENTE.

📌 script résultats:

 
[![Capture d'écran 2025-02-16 141527](https://github.com/user-attachments/assets/1bc3d41f-21b1-4d14-afac-1fdce45bdfa2)](https://www.binance.com/en/trade/BTC_FDUSD)


[![Capture d'écran 2025-02-16 140401](https://github.com/user-attachments/assets/2bfacc41-aa25-46f5-9b11-63cc4086eb01)](https://www.binance.com/en/trade/BTC_FDUSD)



[![Capture d'écran 2025-02-16 140415](https://github.com/user-attachments/assets/267a5178-3a6c-45eb-99df-7a3eb5ea1d5a)](https://www.binance.com/en/trade/BTC_FDUSD)

 
 
 
