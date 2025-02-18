def check_signal(df, execute_trade):
    """Vérifie s'il y a un signal d'achat ou de vente et exécute une action."""
    last_row = df.iloc[-1]
    recent_data =  df['TEMA20'].iloc[-11:]
    recent_min = min(recent_data)
    # Récupérer le prix actuel (par exemple, le prix de cloture)
    if   last_row['TEMA20'] >= recent_min * 1.0000001:
                    if last_row['slope'] is not None and last_row['slope'] > 0.06 and last_row['TEMA20'] < (last_row['TEMA50'] - 0.8):# 0.13 FOR SLOPE 
                        execute_trade("BUY", last_row)
                        
                        

