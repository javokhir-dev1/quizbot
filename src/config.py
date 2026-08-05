import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# .env faylini yuklash (oddiy parser, tashqi kutubxona kerak emas)
def _load_env():
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

_load_env()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = {int(x) for x in os.environ.get("ADMIN_IDS", "").replace(";", ",").split(",") if x.strip().isdigit()}
WEBAPP_URL = os.environ.get("WEBAPP_URL", "http://127.0.0.1:8080").rstrip("/")
PORT = int(os.environ.get("PORT", "8080"))
TZ_OFFSET = int(os.environ.get("TZ_OFFSET", "5"))  # Toshkent UTC+5
DEV_MODE = os.environ.get("DEV_MODE", "0") == "1"
DB_PATH = str(BASE_DIR / "data.db")
