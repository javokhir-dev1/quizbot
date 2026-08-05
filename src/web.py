"""Flask: WebApp statikasi + API. Telegram initData orqali autentifikatsiya."""
import hashlib
import hmac
import json
import random
import time
import urllib.parse

from flask import Flask, jsonify, request, send_from_directory

from . import config, db, tgapi

app = Flask(__name__, static_folder=None)
WEBAPP_DIR = str(config.BASE_DIR / "webapp")

GRACE_SECONDS = 3  # tarmoq kechikishi uchun qo'shimcha vaqt


# ---------- Autentifikatsiya ----------

def validate_init_data(init_data: str) -> dict | None:
    """Telegram WebApp initData imzosini tekshiradi, user dict qaytaradi."""
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        their_hash = parsed.pop("hash", "")
        check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret = hmac.new(b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, their_hash):
            return None
        if time.time() - int(parsed.get("auth_date", "0")) > 86400:
            return None
        return json.loads(parsed.get("user", "{}"))
    except Exception:
        return None


def current_user():
    if config.DEV_MODE and request.args.get("dev_user"):
        uid = int(request.args["dev_user"])
        return {"id": uid, "first_name": f"Dev{uid}", "username": f"dev{uid}"}
    init_data = request.headers.get("X-Init-Data", "")
    return validate_init_data(init_data)


def is_admin(uid: int) -> bool:
    return uid in config.ADMIN_IDS


def auth_required(admin: bool = False):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            tg_user = current_user()
            if not tg_user or "id" not in tg_user:
                return jsonify({"error": "auth"}), 401
            uid = tg_user["id"]
            db.upsert_user(uid, tg_user.get("first_name", ""), tg_user.get("username", ""))
            if admin and not is_admin(uid):
                return jsonify({"error": "forbidden"}), 403
            return fn(uid, *args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator


def display_name(row) -> str:
    return row["first_name"] or (("@" + row["username"]) if row["username"] else f"ID{row['id']}")


# ---------- Statika ----------

@app.route("/")
def index():
    return send_from_directory(WEBAPP_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(WEBAPP_DIR, path)


# ---------- Profil ----------

@app.route("/api/me")
@auth_required()
def api_me(uid):
    user = db.get_user(uid)
    bot_username = db.get_setting("bot_username", "")
    g1 = int(db.get_setting("ref_group1_min", "4"))
    g2 = int(db.get_setting("ref_group2_min", "6"))
    refs = db.ref_count(uid)
    week = db.week_key()
    my_week = db.get_conn().execute(
        "SELECT COALESCE(SUM(score),0) s, COALESCE(SUM(correct_count),0) c, COUNT(*) d "
        "FROM quiz_sessions WHERE user_id=? AND week=? AND finished=1",
        (uid, week),
    ).fetchone()
    # haftalik o'rnim
    rank = None
    for i, row in enumerate(db.quiz_leaderboard(week, 1000), 1):
        if row["id"] == uid:
            rank = i
            break
    return jsonify({
        "id": uid,
        "first_name": user["first_name"],
        "username": user["username"],
        "is_admin": is_admin(uid),
        "ref_link": f"https://t.me/{bot_username}?start=r{uid}" if bot_username else "",
        "ref_count": refs,
        "ref_group1_min": g1,
        "ref_group2_min": g2,
        "week": week,
        "week_score": my_week["s"],
        "week_correct": my_week["c"],
        "week_days": my_week["d"],
        "week_rank": rank,
    })


# ---------- Viktorina ----------

def _today_session(uid):
    return db.get_conn().execute(
        "SELECT * FROM quiz_sessions WHERE user_id=? AND day=?",
        (uid, db.day_key()),
    ).fetchone()


def _question_payload(qid):
    q = db.get_conn().execute("SELECT * FROM questions WHERE id=?", (qid,)).fetchone()
    return {
        "id": q["id"],
        "text": q["text"],
        "options": json.loads(q["options"]),
        "time_limit": q["time_limit"],
    }


def _serve_current(session_row):
    """Joriy savolni (qolgan vaqt bilan) qaytaradi."""
    qs = db.session_questions(session_row)
    idx = session_row["current_idx"]
    item = qs[idx]
    q = _question_payload(item["qid"])
    elapsed = time.time() - item["served_at"]
    remaining = max(0, q["time_limit"] - elapsed)
    return {
        "state": "playing",
        "index": idx,
        "total": len(qs),
        "question": q,
        "remaining": round(remaining, 1),
        "score": session_row["score"],
    }


@app.route("/api/quiz/status")
@auth_required()
def quiz_status(uid):
    sess = _today_session(uid)
    active_count = db.get_conn().execute(
        "SELECT COUNT(*) c FROM questions WHERE active=1").fetchone()["c"]
    if sess is None:
        return jsonify({"state": "ready", "available": active_count > 0,
                        "count": min(active_count, int(db.get_setting("daily_question_count", "10")))})
    if sess["finished"]:
        qs = db.session_questions(sess)
        return jsonify({"state": "done", "score": sess["score"],
                        "correct": sess["correct_count"], "total": len(qs)})
    return jsonify(_serve_current(sess))


@app.route("/api/quiz/start", methods=["POST"])
@auth_required()
def quiz_start(uid):
    if _today_session(uid) is not None:
        return jsonify({"error": "Bugun allaqachon qatnashgansiz"}), 400
    count = int(db.get_setting("daily_question_count", "10"))
    rows = db.get_conn().execute(
        "SELECT id FROM questions WHERE active=1").fetchall()
    if not rows:
        return jsonify({"error": "Hozircha savollar yo'q"}), 400
    qids = [r["id"] for r in rows]
    random.shuffle(qids)
    qids = qids[:count]
    questions = [{"qid": q, "served_at": None, "answer_idx": None,
                  "correct": False, "points": 0} for q in qids]
    questions[0]["served_at"] = time.time()
    conn = db.get_conn()
    cur = conn.execute(
        """INSERT INTO quiz_sessions(user_id, day, week, questions, created_at)
           VALUES(?,?,?,?,?)""",
        (uid, db.day_key(), db.week_key(), json.dumps(questions), db.now_ts()),
    )
    conn.commit()
    sess = conn.execute("SELECT * FROM quiz_sessions WHERE id=?", (cur.lastrowid,)).fetchone()
    return jsonify(_serve_current(sess))


@app.route("/api/quiz/answer", methods=["POST"])
@auth_required()
def quiz_answer(uid):
    sess = _today_session(uid)
    if sess is None or sess["finished"]:
        return jsonify({"error": "Faol sessiya yo'q"}), 400
    body = request.get_json(silent=True) or {}
    answer_idx = body.get("answer_idx")  # None = vaqt tugadi

    qs = db.session_questions(sess)
    idx = sess["current_idx"]
    item = qs[idx]
    qrow = db.get_conn().execute("SELECT * FROM questions WHERE id=?", (item["qid"],)).fetchone()
    elapsed = time.time() - item["served_at"]
    limit = qrow["time_limit"]

    correct = False
    points = 0
    if answer_idx is not None and elapsed <= limit + GRACE_SECONDS:
        correct = int(answer_idx) == qrow["correct_idx"]
        if correct:
            remaining = max(0, limit - elapsed)
            points = 10 + round(remaining / limit * 5)  # tezlik bonusi
    item["answer_idx"] = answer_idx
    item["correct"] = correct
    item["points"] = points
    item["elapsed"] = round(elapsed, 1)

    score = sess["score"] + points
    correct_count = sess["correct_count"] + (1 if correct else 0)
    finished = idx + 1 >= len(qs)
    if not finished:
        qs[idx + 1]["served_at"] = time.time()
    db.save_session_questions(sess["id"], qs, idx + (0 if finished else 1),
                              score, correct_count, finished)

    result = {
        "correct": correct,
        "correct_idx": qrow["correct_idx"],
        "points": points,
        "score": score,
    }
    if finished:
        result["state"] = "done"
        result["correct_count"] = correct_count
        result["total"] = len(qs)
    else:
        sess2 = db.get_conn().execute(
            "SELECT * FROM quiz_sessions WHERE id=?", (sess["id"],)).fetchone()
        result["next"] = _serve_current(sess2)
    return jsonify(result)


@app.route("/api/leaderboard/quiz")
@auth_required()
def api_quiz_leaderboard(uid):
    week = db.week_key()
    rows = db.quiz_leaderboard(week, 50)
    return jsonify({
        "week": week,
        "items": [{"rank": i, "name": display_name(r), "score": r["score"],
                   "correct": r["correct"], "days": r["days_played"],
                   "me": r["id"] == uid}
                  for i, r in enumerate(rows, 1)],
    })


# ---------- Referal ----------

@app.route("/api/referrals")
@auth_required()
def api_referrals(uid):
    g1 = int(db.get_setting("ref_group1_min", "4"))
    g2 = int(db.get_setting("ref_group2_min", "6"))
    top = db.ref_leaderboard(50)
    group1 = db.ref_group_members(g1)
    group2 = db.ref_group_members(g2)
    winners = db.get_conn().execute(
        """SELECT w.*, u.first_name, u.username FROM ref_winners w
           JOIN users u ON u.id = w.user_id ORDER BY w.drawn_at DESC LIMIT 10"""
    ).fetchall()
    return jsonify({
        "my_count": db.ref_count(uid),
        "group1_min": g1, "group2_min": g2,
        "top": [{"rank": i, "name": display_name(r), "refs": r["refs"], "me": r["id"] == uid}
                for i, r in enumerate(top, 1)],
        "group1": [{"name": display_name(r), "refs": r["refs"], "me": r["id"] == uid} for r in group1],
        "group2": [{"name": display_name(r), "refs": r["refs"], "me": r["id"] == uid} for r in group2],
        "winners": [{"group": w["group_num"], "name": display_name(w),
                     "refs": w["ref_count"],
                     "date": time.strftime("%d.%m.%Y", time.localtime(w["drawn_at"]))}
                    for w in winners],
    })


# ---------- So'rovnoma ----------

def _poll_payload(poll, uid):
    conn = db.get_conn()
    options = conn.execute(
        """SELECT o.id, o.text, COUNT(v.user_id) AS votes
           FROM poll_options o
           LEFT JOIN poll_votes v ON v.option_id = o.id
           WHERE o.poll_id = ?
           GROUP BY o.id
           ORDER BY votes DESC, o.id ASC""",
        (poll["id"],),
    ).fetchall()
    my_vote = conn.execute(
        "SELECT option_id FROM poll_votes WHERE poll_id=? AND user_id=?",
        (poll["id"], uid),
    ).fetchone()
    total = sum(o["votes"] for o in options)
    return {
        "id": poll["id"],
        "title": poll["title"],
        "description": poll["description"],
        "status": poll["status"],
        "total_votes": total,
        "my_vote": my_vote["option_id"] if my_vote else None,
        "options": [{"id": o["id"], "text": o["text"], "votes": o["votes"],
                     "percent": round(o["votes"] / total * 100) if total else 0}
                    for o in options],
    }


@app.route("/api/polls")
@auth_required()
def api_polls(uid):
    rows = db.get_conn().execute(
        "SELECT * FROM polls WHERE status IN ('active','closed') "
        "ORDER BY CASE status WHEN 'active' THEN 0 ELSE 1 END, created_at DESC LIMIT 10"
    ).fetchall()
    return jsonify({"polls": [_poll_payload(p, uid) for p in rows]})


@app.route("/api/polls/<int:poll_id>/vote", methods=["POST"])
@auth_required()
def api_vote(uid, poll_id):
    conn = db.get_conn()
    poll = conn.execute("SELECT * FROM polls WHERE id=?", (poll_id,)).fetchone()
    if poll is None or poll["status"] != "active":
        return jsonify({"error": "So'rovnoma faol emas"}), 400
    body = request.get_json(silent=True) or {}
    option_id = body.get("option_id")
    opt = conn.execute(
        "SELECT id FROM poll_options WHERE id=? AND poll_id=?", (option_id, poll_id)
    ).fetchone()
    if opt is None:
        return jsonify({"error": "Variant topilmadi"}), 400
    try:
        conn.execute(
            "INSERT INTO poll_votes(poll_id, option_id, user_id, voted_at) VALUES(?,?,?,?)",
            (poll_id, option_id, uid, db.now_ts()),
        )
        conn.commit()
    except Exception:
        return jsonify({"error": "Siz allaqachon ovoz bergansiz"}), 400
    return jsonify(_poll_payload(poll, uid))


# ---------- ADMIN ----------

@app.route("/api/admin/stats")
@auth_required(admin=True)
def admin_stats(uid):
    conn = db.get_conn()
    total = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    active = conn.execute("SELECT COUNT(*) c FROM users WHERE activated_at IS NOT NULL").fetchone()["c"]
    today = conn.execute("SELECT COUNT(*) c FROM quiz_sessions WHERE day=?",
                         (db.day_key(),)).fetchone()["c"]
    questions = conn.execute("SELECT COUNT(*) c FROM questions WHERE active=1").fetchone()["c"]
    return jsonify({"total_users": total, "active_users": active,
                    "today_players": today, "active_questions": questions})


# -- Savollar --

@app.route("/api/admin/questions", methods=["GET", "POST"])
@auth_required(admin=True)
def admin_questions(uid):
    conn = db.get_conn()
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        text = (body.get("text") or "").strip()
        options = [o.strip() for o in (body.get("options") or []) if o.strip()]
        correct_idx = body.get("correct_idx")
        time_limit = int(body.get("time_limit") or db.get_setting("default_time_limit", "30"))
        if not text or len(options) < 2 or correct_idx is None or not (0 <= int(correct_idx) < len(options)):
            return jsonify({"error": "Savol matni, kamida 2 variant va to'g'ri javob shart"}), 400
        conn.execute(
            "INSERT INTO questions(text, options, correct_idx, time_limit, created_at) VALUES(?,?,?,?,?)",
            (text, json.dumps(options), int(correct_idx), max(5, min(300, time_limit)), db.now_ts()),
        )
        conn.commit()
    rows = conn.execute("SELECT * FROM questions ORDER BY id DESC").fetchall()
    return jsonify({"questions": [
        {"id": r["id"], "text": r["text"], "options": json.loads(r["options"]),
         "correct_idx": r["correct_idx"], "time_limit": r["time_limit"],
         "active": bool(r["active"])} for r in rows]})


@app.route("/api/admin/questions/<int:qid>", methods=["DELETE", "PATCH"])
@auth_required(admin=True)
def admin_question_edit(uid, qid):
    conn = db.get_conn()
    if request.method == "DELETE":
        conn.execute("DELETE FROM questions WHERE id=?", (qid,))
    else:
        body = request.get_json(silent=True) or {}
        if "active" in body:
            conn.execute("UPDATE questions SET active=? WHERE id=?",
                         (int(bool(body["active"])), qid))
    conn.commit()
    return jsonify({"ok": True})


# -- Kanallar --

@app.route("/api/admin/channels", methods=["GET", "POST"])
@auth_required(admin=True)
def admin_channels(uid):
    conn = db.get_conn()
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        chat_id = (body.get("chat_id") or "").strip()
        if not chat_id:
            return jsonify({"error": "Kanal @username yoki ID kiriting"}), 400
        chat = tgapi.get_chat(chat_id)
        if chat is None:
            return jsonify({"error": "Kanal topilmadi. Bot kanalga admin qilib qo'shilganmi?"}), 400
        title = chat.get("title", chat_id)
        invite = chat.get("invite_link", "") or (body.get("invite_link") or "").strip()
        try:
            conn.execute(
                "INSERT INTO channels(chat_id, title, invite_link, created_at) VALUES(?,?,?,?)",
                (chat_id, title, invite, db.now_ts()),
            )
            conn.commit()
        except Exception:
            return jsonify({"error": "Bu kanal allaqachon qo'shilgan"}), 400
    rows = conn.execute("SELECT * FROM channels ORDER BY id").fetchall()
    return jsonify({"channels": [
        {"id": r["id"], "chat_id": r["chat_id"], "title": r["title"],
         "invite_link": r["invite_link"]} for r in rows]})


@app.route("/api/admin/channels/<int:cid>", methods=["DELETE"])
@auth_required(admin=True)
def admin_channel_delete(uid, cid):
    conn = db.get_conn()
    conn.execute("DELETE FROM channels WHERE id=?", (cid,))
    conn.commit()
    return jsonify({"ok": True})


# -- So'rovnomalar --

@app.route("/api/admin/polls", methods=["GET", "POST"])
@auth_required(admin=True)
def admin_polls(uid):
    conn = db.get_conn()
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        title = (body.get("title") or "").strip()
        options = [o.strip() for o in (body.get("options") or []) if o.strip()]
        if not title or len(options) < 2:
            return jsonify({"error": "Sarlavha va kamida 2 variant shart"}), 400
        cur = conn.execute(
            "INSERT INTO polls(title, description, created_at) VALUES(?,?,?)",
            (title, (body.get("description") or "").strip(), db.now_ts()),
        )
        for opt in options:
            conn.execute("INSERT INTO poll_options(poll_id, text) VALUES(?,?)",
                         (cur.lastrowid, opt))
        conn.commit()
    rows = conn.execute("SELECT * FROM polls ORDER BY id DESC").fetchall()
    return jsonify({"polls": [_poll_payload(p, uid) for p in rows]})


@app.route("/api/admin/polls/<int:poll_id>/<action>", methods=["POST"])
@auth_required(admin=True)
def admin_poll_action(uid, poll_id, action):
    conn = db.get_conn()
    if action == "start":
        conn.execute("UPDATE polls SET status='active', started_at=? WHERE id=?",
                     (db.now_ts(), poll_id))
    elif action == "close":
        conn.execute("UPDATE polls SET status='closed', closed_at=? WHERE id=?",
                     (db.now_ts(), poll_id))
    elif action == "delete":
        conn.execute("DELETE FROM polls WHERE id=?", (poll_id,))
    else:
        return jsonify({"error": "Noma'lum amal"}), 400
    conn.commit()
    return jsonify({"ok": True})


# -- Referal g'olibini aniqlash --

@app.route("/api/admin/draw", methods=["POST"])
@auth_required(admin=True)
def admin_draw(uid):
    body = request.get_json(silent=True) or {}
    group = int(body.get("group", 1))
    key = "ref_group2_min" if group == 2 else "ref_group1_min"
    min_refs = int(db.get_setting(key, "4"))
    members = db.ref_group_members(min_refs)
    if group == 1:
        # 1-guruh: faqat 2-guruhga kirmaganlar
        g2_min = int(db.get_setting("ref_group2_min", "6"))
        members = [m for m in members if m["refs"] < g2_min]
    if not members:
        return jsonify({"error": "Bu guruhda hali hech kim yo'q"}), 400
    winner = random.choice(members)
    conn = db.get_conn()
    conn.execute(
        "INSERT INTO ref_winners(group_num, user_id, ref_count, drawn_at) VALUES(?,?,?,?)",
        (group, winner["id"], winner["refs"], db.now_ts()),
    )
    conn.commit()
    return jsonify({"winner": {"name": display_name(winner), "refs": winner["refs"],
                               "id": winner["id"], "group": group}})


# -- Sozlamalar --

@app.route("/api/admin/settings", methods=["GET", "POST"])
@auth_required(admin=True)
def admin_settings(uid):
    keys = ["daily_question_count", "default_time_limit", "ref_group1_min", "ref_group2_min"]
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        for k in keys:
            if k in body and str(body[k]).isdigit():
                db.set_setting(k, str(int(body[k])))
    return jsonify({k: int(db.get_setting(k, "0")) for k in keys})
