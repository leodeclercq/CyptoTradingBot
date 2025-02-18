
def check_signal(df, execute_trade):
    """Vérifie s'il y a un signal d'achat ou de vente et exécute une action."""
    last_row = df.iloc[-1]
    # Récupérer le prix actuel (par exemple, le prix de cloture)
    # Signal d'achat basé sur RSI(6), RSI(12), RSI(24) et croisement de TEMA(7), TEMA(25), TEMA(99)
    if (last_row['TEMA20'] > last_row['TEMA50'] ):
            execute_trade("BUY", last_row)
    
    # Signal de vente basé sur RSI(6), RSI(12), RSI(24) et croisement de TEMA(7), TEMA(25), TEMA(99)
    elif (last_row['TEMA20'] < last_row['TEMA50'] ):
            execute_trade("SELL", last_row)
