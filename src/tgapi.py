"""Telegram Bot API bilan to'g'ridan-to'g'ri ishlash (tashqi kutubxonasiz)."""
import json
import urllib.request
import urllib.error

from . import config

API_BASE = f"https://api.telegram.org/bot{config.BOT_TOKEN}"


def call(method: str, _http_timeout: int = 20, **params):
    data = json.dumps({k: v for k, v in params.items() if v is not None}).encode()
    req = urllib.request.Request(
        f"{API_BASE}/{method}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=_http_timeout) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode())
        except Exception:
            payload = {"ok": False, "description": str(e)}
    except Exception as e:
        payload = {"ok": False, "description": str(e)}
    if not payload.get("ok"):
        print(f"[tgapi] {method} xato: {payload.get('description')}")
        return None
    return payload.get("result")


def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    return call("sendMessage", chat_id=chat_id, text=text,
                reply_markup=reply_markup, parse_mode=parse_mode,
                disable_web_page_preview=True)


def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    return call("editMessageText", chat_id=chat_id, message_id=message_id,
                text=text, reply_markup=reply_markup, parse_mode=parse_mode,
                disable_web_page_preview=True)


def answer_callback(callback_id, text=None, show_alert=False):
    return call("answerCallbackQuery", callback_query_id=callback_id,
                text=text, show_alert=show_alert)


def get_chat_member(chat_id, user_id):
    return call("getChatMember", chat_id=chat_id, user_id=user_id)


def get_chat(chat_id):
    return call("getChat", chat_id=chat_id)


def get_me():
    return call("getMe")


def get_updates(offset=None, poll_timeout=50):
    return call("getUpdates", _http_timeout=poll_timeout + 15,
                offset=offset, timeout=poll_timeout,
                allowed_updates=["message", "callback_query"])
