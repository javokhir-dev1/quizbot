"""Bot: /start, majburiy obuna tekshiruvi, referal qabul qilish, webapp havolasi."""
import time

from . import config, db, tgapi

BOT_USERNAME = ""  # ishga tushganda getMe orqali to'ldiriladi


def webapp_keyboard():
    if config.WEBAPP_URL.startswith("https://"):
        btn = {"text": "🚀 Ilovani ochish", "web_app": {"url": config.WEBAPP_URL}}
    else:
        # web_app tugmalari faqat https bilan ishlaydi — lokal testda oddiy havola
        btn = {"text": "🚀 Ilovani ochish", "url": config.WEBAPP_URL}
    return {"inline_keyboard": [[btn]]}


def unsubscribed_channels(user_id: int) -> list:
    """Foydalanuvchi hali obuna bo'lmagan kanallar ro'yxati."""
    channels = db.get_conn().execute("SELECT * FROM channels").fetchall()
    missing = []
    for ch in channels:
        member = tgapi.get_chat_member(ch["chat_id"], user_id)
        status = (member or {}).get("status", "left")
        if status not in ("member", "administrator", "creator"):
            missing.append(ch)
    return missing


def channel_url(ch) -> str:
    if ch["invite_link"]:
        return ch["invite_link"]
    cid = str(ch["chat_id"])
    if cid.startswith("@"):
        return f"https://t.me/{cid[1:]}"
    return "https://t.me/"


def send_subscribe_prompt(chat_id: int, missing: list, edit_message_id=None):
    rows = [[{"text": f"📢 {ch['title'] or ch['chat_id']}", "url": channel_url(ch)}]
            for ch in missing]
    rows.append([{"text": "✅ Obuna bo'ldim", "callback_data": "check_sub"}])
    text = (
        "👋 <b>Xush kelibsiz!</b>\n\n"
        "Botni faollashtirish va savollarga javob berib sovg'a olish imkoniga "
        "ega bo'lish uchun quyidagi kanal(lar)ga obuna bo'lishingiz shart:\n\n"
        "Obuna bo'lgach, «✅ Obuna bo'ldim» tugmasini bosing."
    )
    markup = {"inline_keyboard": rows}
    if edit_message_id:
        tgapi.edit_message(chat_id, edit_message_id, text, reply_markup=markup)
    else:
        tgapi.send_message(chat_id, text, reply_markup=markup)


def send_welcome(chat_id: int, first_name: str):
    text = (
        f"🎉 <b>Tabriklaymiz, {first_name}!</b>\n\n"
        "Bot faollashtirildi. Endi barcha imkoniyatlar siz uchun ochiq:\n\n"
        "🧠 <b>Kunlik viktorina</b> — har kuni 1 marta qatnashing, "
        "haftalik reytingda yuqoriga chiqing va sovg'a yutib oling\n"
        "🤝 <b>Referal</b> — do'stlaringizni taklif qiling, "
        "sirli sovg'alar o'yiniga qatnashing\n"
        "🗳 <b>So'rovnoma</b> — fikringizni bildiring\n\n"
        "Hammasi ilova ichida 👇"
    )
    tgapi.send_message(chat_id, text, reply_markup=webapp_keyboard())


def handle_start(msg: dict):
    user = msg["from"]
    uid = user["id"]
    text = msg.get("text", "")

    # referal payload: /start r123456
    referred_by = None
    parts = text.split(maxsplit=1)
    if len(parts) == 2 and parts[1].startswith("r") and parts[1][1:].isdigit():
        referred_by = int(parts[1][1:])

    db.upsert_user(uid, user.get("first_name", ""), user.get("username", ""), referred_by)

    missing = unsubscribed_channels(uid)
    if missing:
        send_subscribe_prompt(uid, missing)
        return

    already = db.get_user(uid)
    first_time = already["activated_at"] is None
    db.activate_user(uid)
    if first_time:
        send_welcome(uid, user.get("first_name", "do'stim"))
    else:
        tgapi.send_message(uid, "✅ Bot allaqachon faol. Ilovani oching 👇",
                           reply_markup=webapp_keyboard())


def handle_callback(cb: dict):
    uid = cb["from"]["id"]
    data = cb.get("data", "")
    msg = cb.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id", uid)
    message_id = msg.get("message_id")

    if data == "check_sub":
        missing = unsubscribed_channels(uid)
        if missing:
            tgapi.answer_callback(cb["id"],
                                  "❌ Hali barcha kanallarga obuna bo'lmadingiz!",
                                  show_alert=True)
            send_subscribe_prompt(chat_id, missing, edit_message_id=message_id)
        else:
            tgapi.answer_callback(cb["id"], "✅ Obuna tasdiqlandi!")
            user = db.get_user(uid)
            first_time = user is not None and user["activated_at"] is None
            db.activate_user(uid)
            if message_id:
                tgapi.edit_message(chat_id, message_id,
                                   "✅ <b>Obuna tasdiqlandi!</b>")
            name = cb["from"].get("first_name", "do'stim")
            if first_time:
                send_welcome(chat_id, name)
            else:
                tgapi.send_message(chat_id, "Ilovani oching 👇",
                                   reply_markup=webapp_keyboard())
    else:
        tgapi.answer_callback(cb["id"])


def log_update(update: dict):
    """Kelgan yangilanishni logga yozadi. Konsol kodlashi qanday bo'lishidan
    qat'i nazar bot to'xtab qolmasligi uchun butunlay xavfsiz."""
    try:
        src = update.get("message") or update.get("callback_query") or {}
        who = src.get("from") or {}
        what = update.get("message", {}).get("text") \
            or update.get("callback_query", {}).get("data") or "?"
        print(f"[bot] {who.get('first_name', '?')} (id={who.get('id')}) -> {what}")
    except Exception:
        pass


def handle_update(update: dict):
    try:
        if "message" in update:
            msg = update["message"]
            text = msg.get("text", "")
            if text.startswith("/start"):
                handle_start(msg)
            elif text.startswith("/app"):
                handle_start({**msg, "text": "/start"})
        elif "callback_query" in update:
            handle_callback(update["callback_query"])
    except Exception as e:
        print(f"[bot] update xatosi: {e}")


def run_polling():
    global BOT_USERNAME
    db.init_db()
    me = tgapi.get_me()
    if me:
        BOT_USERNAME = me.get("username", "")
        db.set_setting("bot_username", BOT_USERNAME)
        print(f"[bot] @{BOT_USERNAME} ishga tushdi")
    else:
        print("[bot] DIQQAT: BOT_TOKEN noto'g'ri yoki internet yo'q — bot ishlamaydi")

    offset = None
    while True:
        updates = tgapi.get_updates(offset=offset)
        if updates is None:
            time.sleep(3)
            continue
        for u in updates:
            offset = u["update_id"] + 1
            log_update(u)
            handle_update(u)
