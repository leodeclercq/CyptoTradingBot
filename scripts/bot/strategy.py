def check_signal(df, execute_trade):
    """Vérifie s'il y a un signal d'achat ou de vente et exécute une action."""
    last_row = df.iloc[-1]
    lasts_row = df.iloc[-2]
    recent_data =  df['TEMA20'].iloc[-11:]
    recent_min = min(recent_data)
    recent_datas =  df['close'].iloc[-11:]
    recent_mins = min(recent_datas)
    # Récupérer le prix actuel (par exemple, le prix de cloture)
    if   last_row['TEMA20'] >= recent_min * 1.00005 and  last_row['TEMA20'] >= lasts_row['TEMA20'] * 1.00002 and last_row['close'] >= recent_mins *1.00025  and last_row['close'] >= lasts_row ['close'] *1.0001:
                    if last_row['slope'] is not None and last_row['slope'] > 1.3 and last_row['TEMA20'] < (last_row['TEMA50'] - 0.4):
                        execute_trade("BUY", last_row)
                        
                        

