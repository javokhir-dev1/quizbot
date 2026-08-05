"""Kirish nuqtasi: bot (long polling) + webapp server bitta jarayonda."""
import sys
import threading

# Loglar darhol ko'rinishi uchun (bot alohida oqimda ishlaydi) va
# ismidagi emoji/kirill harflar konsolni yiqitmasligi uchun UTF-8 majburlanadi
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

from src import config, db
from src.bot import run_polling
from src.web import app


def main():
    db.init_db()
    if config.BOT_TOKEN:
        t = threading.Thread(target=run_polling, daemon=True, name="bot-polling")
        t.start()
    else:
        print("DIQQAT: .env faylida BOT_TOKEN yo'q — faqat webapp ishlaydi (DEV_MODE uchun)")
    print(f"WebApp: http://127.0.0.1:{config.PORT}")
    app.run(host="0.0.0.0", port=config.PORT, threaded=True)


if __name__ == "__main__":
    main()
