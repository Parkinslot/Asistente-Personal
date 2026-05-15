import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN:
    raise ValueError("Falta TELEGRAM_TOKEN en .env")

if not TELEGRAM_CHAT_ID:
    print("⚠️ Falta TELEGRAM_CHAT_ID en .env. Los recordatorios no se enviarán.")