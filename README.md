# 🎁 Sovg'a Bot — Telegram viktorina va referal WebApp

Telegram bot + WebApp: kunlik viktorina (haftalik reyting va sovg'alar), referal
dasturi (sirli sovg'a o'yinlari), so'rovnomalar va to'liq admin panel.

## Imkoniyatlar

**Foydalanuvchi uchun (WebApp ichida):**
- 🧠 **Kunlik viktorina** — kuniga 1 marta, har savolga alohida taymer,
  tez javob uchun bonus ball
- 🏆 **Haftalik reyting** — dushanbadan yakshanbagacha, hafta yakunida sovg'a
- 🤝 **Referal** — shaxsiy havola, 1-guruh (3+ do'st) va 2-guruh (5+ do'st)
  sirli sovg'a o'yinlari, umumiy reyting
- 🗳 **So'rovnomalar** — har kim 1 marta ovoz beradi, natijalar ovozlar bo'yicha saralanadi

**Bot:**
- Majburiy kanal obunasi tekshiruvi («✅ Obuna bo'ldim» tugmasi bilan qayta tekshirish)
- Referal havolalarni qabul qilish (`/start r<id>`)

**Admin uchun (WebApp'da faqat adminga ko'rinadi):**
- 📊 Statistika · 🧠 Savollar qo'shish/o'chirish · 📢 Kanallar boshqaruvi
- 🗳 So'rovnoma yaratish/boshlash/yakunlash · 🎰 Random g'olib aniqlash · 🔧 Sozlamalar

## Ishga tushirish

Eng oson yo'l — tayyor skript. U tunnel ochadi, manzilni `.env` ga yozadi,
Telegram menyu tugmasini yangilaydi va botni ishga tushiradi:

```powershell
powershell -ExecutionPolicy Bypass -File "D:\O'zimga\quizbot\start.ps1"
```

Qo'lda ishga tushirish uchun (tunnel allaqachon ochiq bo'lsa):

```
python app.py
```

Talablar: Python 3.11+ va Flask (`pip install -r requirements.txt`).

## WEBAPP_URL haqida muhim

Telegram'ning `web_app` tugmasi faqat **https** manzil bilan ishlaydi.

- **Lokal (bepul tunnel):** `start.ps1` buni avtomatik bajaradi.
  Diqqat: bepul `trycloudflare.com` manzili **har safar o'zgaradi** va kompyuter
  o'chsa bot ham to'xtaydi. Shu sababli u faqat test uchun mos.
- **Doimiy ishlashi uchun:** VPS (masalan Ubuntu) + o'z domeningiz + nginx/SSL,
  yoki Cloudflare'da nomli (named) tunnel yarating — u holda manzil o'zgarmaydi.

Agar `WEBAPP_URL` http bo'lsa, bot tugmani oddiy havola sifatida yuboradi
(brauzerda ochiladi, lekin Telegram ichidagi WebApp autentifikatsiyasi ishlamaydi).

## Brauzerda Telegramsiz test qilish

`.env` da `DEV_MODE=1` qiling va oching:

- Oddiy foydalanuvchi: `http://127.0.0.1:8080/?dev_user=111`
- Admin sifatida: `http://127.0.0.1:8080/?dev_user=5552033632`

**Ishga tushirishdan oldin `DEV_MODE=0` qilishni unutmang!**

## Kanal qo'shish

1. Kanalingizni oching → **Administrators** → **Add Administrator**
2. `@Muslimbekuz_robot` ni qidirib qo'shing (huquqlar minimal bo'lsa ham bo'ladi)
3. WebApp → Admin (⚙️) → 📢 → kanal `@username`'ini kiriting

Bot kanalga admin qilib qo'shilmasa, Telegram API `chat not found` qaytaradi va
obunani tekshirib bo'lmaydi. Kanallar ro'yxati bo'sh bo'lsa, obuna talab qilinmaydi
va hamma to'g'ridan-to'g'ri ilovaga kiraveradi.

## Tuzilma

```
start.ps1         — tunnel + bot bitta buyruq bilan
app.py            — kirish nuqtasi (bot + server)
src/config.py     — .env sozlamalari
src/db.py         — SQLite sxema va so'rovlar
src/tgapi.py      — Telegram Bot API
src/bot.py        — /start, obuna tekshiruvi, referal
src/web.py        — Flask API (initData imzo tekshiruvi bilan)
webapp/           — WebApp (HTML/CSS/JS)
data.db           — ma'lumotlar bazasi (avto-yaratiladi)
```
