# quizbot — serverga joylashtirish

Server: `185.191.141.190` · Domen: **quiz.sozlabot.uz** · Papka: `/root/quizbot` · Port: `8080`

> Serverda `sorovnoma` loyihasi allaqachon ishlayapti — nginx, certbot, pm2, Node.js
> o'rnatilgan. Quyida faqat quizbot uchun qadamlar.

---

## 1. Kodni serverga olish

```bash
cd /root
git clone https://github.com/javokhir-dev1/quizbot.git
cd quizbot
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

## 2. `.env` yaratish

`.env` git'da yo'q — serverda qo'lda yarating:

```bash
nano /root/quizbot/.env
```

```env
BOT_TOKEN=BotFather_dan_olingan_token
ADMIN_IDS=5552033632
WEBAPP_URL=https://quiz.sozlabot.uz
PORT=8080
TZ_OFFSET=5
DEV_MODE=0
```

`DEV_MODE=0` bo'lishi shart — aks holda Flask dev serveri ishlaydi va autentifikatsiya chetlab o'tiladi.

## 3. DNS

`quiz.sozlabot.uz` uchun A-record → `185.191.141.190`

```bash
dig +short quiz.sozlabot.uz
```

## 4. Nginx + SSL

```bash
cp /root/quizbot/nginx-quizbot.conf /etc/nginx/sites-available/quizbot
ln -sf /etc/nginx/sites-available/quizbot /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

certbot --nginx -d quiz.sozlabot.uz --redirect -m javokhir.dev1@gmail.com --agree-tos
```

## 5. pm2

```bash
cd /root/quizbot
pm2 start ecosystem.config.js
pm2 save
pm2 status
pm2 logs quizbot
```

`HOST=127.0.0.1` ecosystem faylida berilgan — port 8080 tashqaridan ochiq bo'lmaydi, faqat nginx orqali.

## 6. BotFather

`/mybots` → bot → Bot Settings → Menu Button → `https://quiz.sozlabot.uz`

## 7. Avtomatik deploy

`.github/workflows/deploy.yml` tayyor. Repo → **Settings → Secrets and variables → Actions**
ga `SSH_KEY` secret'ini qo'shing (sorovnoma repodagi bilan bir xil private kalit).

Push'dan keyin: `git reset --hard` → `pip install` → `pm2 restart quizbot`.
`.env` va `data.db` gitignore'da — deploy ularga tegmaydi.

---

## Production o'zgarishi

`app.py` endi `DEV_MODE=0` bo'lganda **waitress** (production WSGI server) ishlatadi,
`DEV_MODE=1` bo'lganda esa avvalgidek Flask dev serveri — lokal testga xalaqit bermaydi.
Bot polling xuddi shu jarayonda, alohida thread'da ishlaydi (pm2 bitta jarayon boshqaradi).

## Kundalik buyruqlar

```bash
pm2 restart quizbot
pm2 logs quizbot --lines 100
pm2 status
cp /root/quizbot/data.db /root/backups/quizbot-$(date +%F).db
```

## Ko'p uchraydigan xatolar

| Muammo | Yechim |
|---|---|
| WebApp ochilmaydi | `WEBAPP_URL` https emas yoki BotFather'dagi Menu Button eski |
| 502 Bad Gateway | pm2'da jarayon o'chgan — `pm2 logs quizbot` |
| Admin panel ko'rinmaydi | `.env` dagi `ADMIN_IDS` |
| `chat not found` | Bot kanalda administrator emas |
| Deploy'dan keyin ham eski kod | `pm2 restart` ishlamagan — Actions logini tekshiring |
