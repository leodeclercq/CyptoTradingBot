
import requests

# 🔧 Remplace par ton TOKEN de bot et ID de canal
TELEGRAM_BOT_TOKEN = "8027599831:AAEhXtUFwv4ZQc48YSwk-Uemm4BesZLBVHI"
TELEGRAM_CHAT_ID = "-1002264309587"

def send_telegram_message(message):
    """Envoie un message à Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"⚠️ Erreur envoi Telegram : {e}")