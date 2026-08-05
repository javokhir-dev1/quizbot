/* ===== Sovg'a Bot WebApp ===== */
const tg = window.Telegram?.WebApp;
tg?.ready();
tg?.expand();

const $ = (s, el = document) => el.querySelector(s);
const view = $('#view');
let ME = null;
let quizTimer = null;

/* ---------- API ---------- */
async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', 'X-Init-Data': tg?.initData || '' };
  const devUser = new URLSearchParams(location.search).get('dev_user');
  const url = devUser ? `${path}${path.includes('?') ? '&' : '?'}dev_user=${devUser}` : path;
  const res = await fetch(url, { headers, ...opts });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Xatolik yuz berdi');
  return data;
}
const post = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body || {}) });

function toast(msg) {
  const t = $('#toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._h);
  t._h = setTimeout(() => t.classList.remove('show'), 2600);
}
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function stopTimer() { if (quizTimer) { clearInterval(quizTimer); quizTimer = null; } }

/* ---------- Tabs ---------- */
const TABS = [
  { id: 'home', ico: '🏠', label: 'Asosiy', c1: '#6366f1', c2: '#8b5cf6' },
  { id: 'quiz', ico: '🧠', label: 'Viktorina', c1: '#a855f7', c2: '#ec4899' },
  { id: 'top', ico: '🏆', label: 'Reyting', c1: '#f59e0b', c2: '#fbbf24' },
  { id: 'ref', ico: '🤝', label: 'Referal', c1: '#f97316', c2: '#ef4444' },
  { id: 'poll', ico: '🗳', label: "So'rov", c1: '#10b981', c2: '#14b8a6' },
];
const ADMIN_TAB = { id: 'adm', ico: '⚙️', label: 'Admin', c1: '#f43f5e', c2: '#e11d48' };

function renderTabs(active) {
  const tabs = ME?.is_admin ? [...TABS, ADMIN_TAB] : TABS;
  $('#tabbar').innerHTML = tabs.map(t => `
    <button class="tab ${t.id === active ? 'active' : ''}" style="--tabc1:${t.c1};--tabc2:${t.c2}" onclick="go('${t.id}')">
      <span class="tico">${t.ico}</span>${t.label}
    </button>`).join('');
}

const ROUTES = { home: renderHome, quiz: renderQuiz, top: renderTop, ref: renderRef, poll: renderPoll, adm: renderAdmin };
function go(tab) {
  stopTimer();
  renderTabs(tab);
  view.innerHTML = '<div class="spinner"></div>';
  ROUTES[tab]().catch(e => {
    view.innerHTML = `<div class="empty"><span class="e-ico">😕</span>${esc(e.message)}</div>`;
  });
}
window.go = go;

/* ---------- Boot ---------- */
async function boot() {
  try {
    ME = await api('/api/me');
  } catch (e) {
    view.innerHTML = `<div class="empty"><span class="e-ico">🔐</span>
      Ilovani Telegram bot orqali oching.<br><span class="hint">${esc(e.message)}</span></div>`;
    $('#tabbar').style.display = 'none';
    return;
  }
  $('#avatar').textContent = (ME.first_name || '?').slice(0, 1).toUpperCase();
  $('#head-name').textContent = ME.first_name || 'Foydalanuvchi';
  $('#head-sub').textContent = ME.username ? '@' + ME.username : `ID: ${ME.id}`;
  $('#head-badge').textContent = `⭐ ${ME.week_score} ball`;
  go('home');
}

async function refreshMe() {
  try { ME = await api('/api/me'); $('#head-badge').textContent = `⭐ ${ME.week_score} ball`; } catch {}
}

/* ================= HOME ================= */
async function renderHome() {
  const st = await api('/api/quiz/status');
  const quizLine = st.state === 'ready'
    ? (st.available ? "Bugungi viktorina sizni kutmoqda!" : "Bugun savollar hali qo'shilmagan")
    : st.state === 'done' ? `Bugun: ${st.score} ball (${st.correct}/${st.total} to'g'ri)` : "Boshlangan o'yiningiz bor — davom eting!";
  view.innerHTML = `
    <div class="hero">
      <h1>Salom, ${esc(ME.first_name)}! 👋</h1>
      <p>Har kuni bilimingizni sinang, do'stlaringizni taklif qiling va haftalik sovg'alarni qo'lga kiriting.</p>
    </div>
    <div class="stat-grid">
      <div class="stat"><span class="si">⭐</span><div class="sv">${ME.week_score}</div><div class="sl">Haftalik ball</div></div>
      <div class="stat"><span class="si">🏅</span><div class="sv">${ME.week_rank ? '#' + ME.week_rank : '—'}</div><div class="sl">Reytingdagi o'rni</div></div>
      <div class="stat"><span class="si">🤝</span><div class="sv">${ME.ref_count}</div><div class="sl">Takliflar</div></div>
      <div class="stat"><span class="si">📅</span><div class="sv">${ME.week_days}/7</div><div class="sl">Faol kunlar</div></div>
    </div>
    <div class="menu-row" onclick="go('quiz')">
      <div class="mi g-quiz">🧠</div>
      <div><div class="mt">Kunlik viktorina</div><div class="md">${esc(quizLine)}</div></div>
      <span class="arr">›</span>
    </div>
    <div class="menu-row" onclick="go('top')">
      <div class="mi g-top">🏆</div>
      <div><div class="mt">Haftalik reyting</div><div class="md">Dushanbadan yangi hafta boshlanadi</div></div>
      <span class="arr">›</span>
    </div>
    <div class="menu-row" onclick="go('ref')">
      <div class="mi g-ref">🎁</div>
      <div><div class="mt">Do'st taklif qil</div><div class="md">Sirli sovg'alar o'yinida qatnashing</div></div>
      <span class="arr">›</span>
    </div>
    <div class="menu-row" onclick="go('poll')">
      <div class="mi g-poll">🗳</div>
      <div><div class="mt">So'rovnoma</div><div class="md">Fikringizni bildiring</div></div>
      <span class="arr">›</span>
    </div>`;
}

/* ================= QUIZ ================= */
async function renderQuiz() {
  const st = await api('/api/quiz/status');
  if (st.state === 'ready') {
    view.innerHTML = `
      <div class="section-title"><span class="ico g-quiz">🧠</span> Kunlik viktorina</div>
      <div class="card center">
        <div style="font-size:56px">🎯</div>
        <h2 style="margin:10px 0 6px">Bugungi sinov tayyor!</h2>
        <p class="hint">${st.count} ta savol · har biriga cheklangan vaqt.<br>
        Kuniga faqat <b>1 marta</b> qatnashish mumkin.<br>
        Tez va to'g'ri javob — ko'proq ball!</p>
        <button class="btn g-quiz mt" ${st.available ? '' : 'disabled'} onclick="startQuiz()">
          ${st.available ? '🚀 Boshlash' : 'Savollar hali yo’q'}
        </button>
      </div>`;
  } else if (st.state === 'done') {
    showQuizDone(st.score, st.correct, st.total);
  } else {
    showQuestion(st);
  }
}

async function startQuiz() {
  try { showQuestion(await post('/api/quiz/start')); }
  catch (e) { toast(e.message); }
}
window.startQuiz = startQuiz;

function showQuestion(st) {
  stopTimer();
  const q = st.question;
  const R = 28, CIRC = 2 * Math.PI * R;
  const letters = ['A', 'B', 'C', 'D', 'E', 'F'];
  view.innerHTML = `
    <div class="quiz-topbar">
      <div class="q-progress">${Array.from({ length: st.total }, (_, i) =>
        `<i class="${i < st.index ? 'done' : ''}"></i>`).join('')}</div>
      <div class="timer-wrap">
        <svg width="64" height="64">
          <defs><linearGradient id="tgrad"><stop offset="0%" stop-color="#a855f7"/><stop offset="100%" stop-color="#ec4899"/></linearGradient></defs>
          <circle class="timer-ring" cx="32" cy="32" r="${R}"/>
          <circle class="timer-arc" id="tarc" cx="32" cy="32" r="${R}" stroke-dasharray="${CIRC}" stroke-dashoffset="0"/>
        </svg>
        <div class="timer-num" id="tnum"></div>
      </div>
    </div>
    <div class="card">
      <div class="hint" style="margin-bottom:8px">Savol ${st.index + 1} / ${st.total} · ⭐ ${st.score} ball</div>
      <div class="q-text">${esc(q.text)}</div>
      <div id="opts">${q.options.map((o, i) =>
        `<button class="opt" style="animation-delay:${i * 0.05}s" onclick="answer(${i})">
          <span class="letter">${letters[i]}</span>${esc(o)}</button>`).join('')}</div>
    </div>`;

  let remaining = st.remaining;
  const limit = q.time_limit;
  const tick = () => {
    remaining = Math.max(0, remaining - 0.1);
    const tnum = $('#tnum'), tarc = $('#tarc');
    if (!tnum) { stopTimer(); return; }
    tnum.textContent = Math.ceil(remaining);
    tnum.classList.toggle('low', remaining <= 5);
    tarc.style.strokeDashoffset = CIRC * (1 - remaining / limit);
    if (remaining <= 0) { stopTimer(); answer(null); }
  };
  tick();
  quizTimer = setInterval(tick, 100);
}

let answering = false;
async function answer(idx) {
  if (answering) return;
  answering = true;
  stopTimer();
  const opts = [...view.querySelectorAll('.opt')];
  opts.forEach(o => o.disabled = true);
  if (idx !== null) opts[idx]?.classList.add('sel');
  try {
    const r = await post('/api/quiz/answer', { answer_idx: idx });
    opts.forEach((o, i) => {
      if (i === r.correct_idx) o.classList.add('ok');
      else if (i === idx) o.classList.add('bad');
      else o.classList.add('dim');
    });
    if (r.points > 0) {
      const fly = document.createElement('div');
      fly.className = 'points-fly';
      fly.textContent = `+${r.points}`;
      document.body.appendChild(fly);
      setTimeout(() => fly.remove(), 1000);
      tg?.HapticFeedback?.notificationOccurred('success');
    } else {
      tg?.HapticFeedback?.notificationOccurred('error');
    }
    setTimeout(() => {
      answering = false;
      if (r.state === 'done') { showQuizDone(r.score, r.correct_count, r.total); refreshMe(); }
      else showQuestion(r.next);
    }, 1400);
  } catch (e) {
    answering = false;
    toast(e.message);
    renderQuiz();
  }
}
window.answer = answer;

function showQuizDone(score, correct, total) {
  stopTimer();
  const pct = total ? correct / total : 0;
  const emoji = pct >= 0.8 ? '🏆' : pct >= 0.5 ? '🎉' : '💪';
  const msg = pct >= 0.8 ? 'Ajoyib natija!' : pct >= 0.5 ? 'Yaxshi harakat!' : 'Ertaga yana urinib ko’ring!';
  view.innerHTML = `
    <div class="section-title"><span class="ico g-quiz">🧠</span> Kunlik viktorina</div>
    <div class="card result-big">
      <span class="emoji">${emoji}</span>
      <h2>${msg}</h2>
      <div class="result-score">${score}</div>
      <div class="hint">ball to'plandingiz · ${correct}/${total} to'g'ri javob</div>
      <p class="hint mt">Ertaga yangi savollar bilan qaytamiz.<br>Har kuni qatnashib reytingda yuqoriga chiqing!</p>
      <button class="btn g-top mt" onclick="go('top')">🏆 Reytingni ko'rish</button>
    </div>`;
}

/* ================= LEADERBOARD ================= */
async function renderTop() {
  const d = await api('/api/leaderboard/quiz');
  const [p1, p2, p3] = [d.items[0], d.items[1], d.items[2]];
  const pod = (p, cls, medal) => p ? `
    <div class="pod ${cls}">
      ${cls === 'p1' ? '<div class="crown">👑</div>' : ''}
      <div class="pav">${esc((p.name || '?').slice(0, 1).toUpperCase())}</div>
      <div class="pn">${esc(p.name)}</div>
      <div class="ps">${p.score} ball</div>
      <div class="hint">${medal}</div>
    </div>` : '<div class="pod"></div>';
  view.innerHTML = `
    <div class="section-title"><span class="ico g-top">🏆</span> Haftalik reyting
      <span class="hint" style="margin-left:auto">${esc(d.week)}</span></div>
    <div class="card">
      <p class="hint center">Har hafta yakunida eng yaxshilar sovg'a oladi.<br>Dushanba kuni reyting yangidan boshlanadi 🔄</p>
      ${d.items.length ? `
        <div class="podium">${pod(p2, 'p2', '🥈')}${pod(p1, 'p1', '🥇')}${pod(p3, 'p3', '🥉')}</div>
        ${d.items.slice(3).map(r => `
          <div class="lb-row ${r.me ? 'me' : ''}">
            <div class="lb-rank">${r.rank}</div>
            <div class="lb-name">${esc(r.name)}${r.me ? ' (siz)' : ''}<div class="lb-sub">${r.days} kun · ${r.correct} to'g'ri</div></div>
            <div class="lb-pts">${r.score}</div>
          </div>`).join('')}`
      : '<div class="empty"><span class="e-ico">🌱</span>Bu haftada hali hech kim qatnashmagan.<br>Birinchi bo’ling!</div>'}
    </div>`;
}

/* ================= REFERRAL ================= */
let refTab = 'top';
async function renderRef() {
  const d = await api('/api/referrals');
  const nextGoal = d.my_count >= d.group2_min ? null : d.my_count >= d.group1_min ? d.group2_min : d.group1_min;
  const progPct = nextGoal ? Math.min(100, d.my_count / nextGoal * 100) : 100;
  const myBadge = d.my_count >= d.group2_min
    ? '<span class="gbadge g2">💎 2-guruh a’zosi</span>'
    : d.my_count >= d.group1_min ? '<span class="gbadge g1">🎁 1-guruh a’zosi</span>' : '';
  view.innerHTML = `
    <div class="section-title"><span class="ico g-ref">🤝</span> Referal dasturi</div>
    <div class="card ref-link-card">
      <b>🔗 Shaxsiy taklif havolangiz</b>
      <div class="ref-link">${esc(ME.ref_link || 'Havola tayyorlanmoqda…')}</div>
      <div class="ref-btns">
        <button class="btn g-ref small" onclick="copyRef()">📋 Nusxalash</button>
        <button class="btn ghost small" onclick="shareRef()">📤 Ulashish</button>
      </div>
      <div class="prog-wrap">
        <div class="prog-bar"><div class="prog-fill" style="width:${progPct}%"></div></div>
        <div class="prog-lbls">
          <span>Sizda: <b style="color:#fb923c">${d.my_count} ta</b> ${myBadge}</span>
          <span>${nextGoal ? `Keyingi bosqich: ${nextGoal} ta` : 'Eng yuqori bosqichdasiz! 🎉'}</span>
        </div>
      </div>
    </div>
    <div class="card">
      <b>🎁 Sovg'a guruhlari</b>
      <p class="hint" style="margin-top:6px">
        <span class="gbadge g1">🎁 1-guruh</span> ${d.group1_min}+ do'st — sirli sovg'a o'yini<br>
        <span class="gbadge g2">💎 2-guruh</span> ${d.group2_min}+ do'st — yanada zo'r sovg'a o'yini<br>
        G'oliblar tasodifiy (random) tanlanadi. Omadingizni sinang!
      </p>
    </div>
    ${d.winners.length ? `<div class="card"><b>🏅 So'nggi g'oliblar</b>
      ${d.winners.map(w => `<div class="lb-row mt" style="margin-top:8px">
        <div class="lb-rank">${w.group === 2 ? '💎' : '🎁'}</div>
        <div class="lb-name">${esc(w.name)}<div class="lb-sub">${w.refs} taklif · ${w.date}</div></div>
      </div>`).join('')}</div>` : ''}
    <div class="card">
      <div class="seg">
        <button class="${refTab === 'top' ? 'on' : ''}" onclick="setRefTab('top')">🏆 Umumiy</button>
        <button class="${refTab === 'g1' ? 'on' : ''}" onclick="setRefTab('g1')">🎁 1-guruh</button>
        <button class="${refTab === 'g2' ? 'on' : ''}" onclick="setRefTab('g2')">💎 2-guruh</button>
      </div>
      <div id="ref-list">${refListHtml(d)}</div>
    </div>`;
  window._refData = d;
}

function refListHtml(d) {
  const src = refTab === 'top' ? d.top : refTab === 'g1' ? d.group1 : d.group2;
  if (!src.length) return '<div class="empty"><span class="e-ico">🌵</span>Bu ro’yxat hali bo’sh</div>';
  return src.map((r, i) => `
    <div class="lb-row ${r.me ? 'me' : ''}">
      <div class="lb-rank">${r.rank || i + 1}</div>
      <div class="lb-name">${esc(r.name)}${r.me ? ' (siz)' : ''}</div>
      <div class="lb-pts">${r.refs} <span class="hint">do'st</span></div>
    </div>`).join('');
}
function setRefTab(t) { refTab = t; renderRef(); }
window.setRefTab = setRefTab;

function copyRef() {
  navigator.clipboard?.writeText(ME.ref_link).then(() => toast('✅ Havola nusxalandi!'))
    .catch(() => toast(ME.ref_link));
}
function shareRef() {
  const text = "🎁 Qo'shil! Savollarga javob ber, sovg'alar yut!";
  const url = `https://t.me/share/url?url=${encodeURIComponent(ME.ref_link)}&text=${encodeURIComponent(text)}`;
  tg?.openTelegramLink ? tg.openTelegramLink(url) : window.open(url);
}
window.copyRef = copyRef;
window.shareRef = shareRef;

/* ================= POLLS ================= */
async function renderPoll() {
  const d = await api('/api/polls');
  view.innerHTML = `
    <div class="section-title"><span class="ico g-poll">🗳</span> So'rovnomalar</div>
    ${d.polls.length ? d.polls.map(pollHtml).join('')
      : '<div class="card"><div class="empty"><span class="e-ico">🗳</span>Hozircha faol so’rovnoma yo’q.<br>Tez orada yangisi boshlanadi!</div></div>'}`;
  requestAnimationFrame(() =>
    view.querySelectorAll('.poll-opt .fill').forEach(f => f.style.width = f.dataset.w + '%'));
}

function pollHtml(p) {
  const voted = p.my_vote !== null;
  const showResults = voted || p.status === 'closed';
  return `
  <div class="card poll-card">
    <span class="poll-status ${p.status}">${p.status === 'active' ? '● Faol' : 'Yakunlangan'}</span>
    <div class="poll-title">${esc(p.title)}</div>
    ${p.description ? `<div class="poll-desc">${esc(p.description)}</div>` : ''}
    ${p.options.map(o => `
      <button class="poll-opt ${p.my_vote === o.id ? 'myvote' : ''}"
        ${showResults || p.status !== 'active' ? 'disabled' : ''} onclick="vote(${p.id},${o.id})">
        ${showResults ? `<span class="fill" data-w="${o.percent}"></span>` : ''}
        <span class="row"><span>${esc(o.text)}</span>
        ${showResults ? `<span class="pct">${o.percent}% · ${o.votes}</span>` : ''}</span>
      </button>`).join('')}
    <div class="poll-total">Jami: ${p.total_votes} ovoz${voted ? ' · Siz ovoz bergansiz ✓' : ''}</div>
  </div>`;
}

async function vote(pollId, optionId) {
  try {
    await post(`/api/polls/${pollId}/vote`, { option_id: optionId });
    tg?.HapticFeedback?.notificationOccurred('success');
    toast('✅ Ovozingiz qabul qilindi!');
    renderPoll();
  } catch (e) { toast(e.message); }
}
window.vote = vote;

/* ================= ADMIN ================= */
let admTab = 'stats';
async function renderAdmin() {
  view.innerHTML = `
    <div class="section-title"><span class="ico g-adm">⚙️</span> Admin panel</div>
    <div class="seg" style="flex-wrap:wrap">
      ${[['stats', '📊'], ['q', '🧠'], ['ch', '📢'], ['p', '🗳'], ['draw', '🎰'], ['set', '🔧']].map(([t, i]) =>
        `<button class="${admTab === t ? 'on' : ''}" onclick="setAdmTab('${t}')">${i}</button>`).join('')}
    </div>
    <div id="adm-body"><div class="spinner"></div></div>`;
  const body = $('#adm-body');
  const renderers = { stats: admStats, q: admQuestions, ch: admChannels, p: admPolls, draw: admDraw, set: admSettings };
  await renderers[admTab](body);
}
function setAdmTab(t) { admTab = t; renderAdmin(); }
window.setAdmTab = setAdmTab;

async function admStats(el) {
  const s = await api('/api/admin/stats');
  el.innerHTML = `
    <div class="stat-grid">
      <div class="stat"><span class="si">👥</span><div class="sv">${s.total_users}</div><div class="sl">Jami foydalanuvchi</div></div>
      <div class="stat"><span class="si">✅</span><div class="sv">${s.active_users}</div><div class="sl">Faollashgan</div></div>
      <div class="stat"><span class="si">🎯</span><div class="sv">${s.today_players}</div><div class="sl">Bugun o'ynadi</div></div>
      <div class="stat"><span class="si">🧠</span><div class="sv">${s.active_questions}</div><div class="sl">Faol savollar</div></div>
    </div>`;
}

async function admQuestions(el) {
  const d = await api('/api/admin/questions');
  el.innerHTML = `
    <div class="card">
      <b>➕ Yangi savol</b>
      <div class="mt">
        <label class="fld">Savol matni</label>
        <textarea id="nq-text" rows="2" placeholder="Savolni yozing…"></textarea>
        <label class="fld">Variantlar (har qatorda bittadan, 2–6 ta)</label>
        <textarea id="nq-opts" rows="4" placeholder="Variant 1&#10;Variant 2&#10;Variant 3&#10;Variant 4"></textarea>
        <label class="fld">To'g'ri javob raqami (1 dan boshlab)</label>
        <input id="nq-correct" type="number" min="1" placeholder="1">
        <label class="fld">Vaqt (soniya)</label>
        <input id="nq-time" type="number" min="5" max="300" value="30">
        <button class="btn g-adm" onclick="addQuestion()">Saqlash</button>
      </div>
    </div>
    <div class="card"><b>📚 Savollar (${d.questions.length})</b>
      ${d.questions.map(q => `
        <div class="adm-item mt" style="margin-top:8px">
          <div class="top"><span><b>#${q.id}</b> ${esc(q.text)}</span></div>
          <div class="meta">${q.options.map((o, i) =>
            i === q.correct_idx ? `<b style="color:#34d399">✓ ${esc(o)}</b>` : esc(o)).join(' · ')} · ⏱ ${q.time_limit}s</div>
          <div class="acts">
            <button class="chip ${q.active ? '' : 'green'}" onclick="toggleQuestion(${q.id},${q.active ? 0 : 1})">
              ${q.active ? '⏸ O’chirib turish' : '▶️ Yoqish'}</button>
            <button class="chip red" onclick="delQuestion(${q.id})">🗑 O'chirish</button>
          </div>
        </div>`).join('') || '<div class="empty">Savollar hali yo’q</div>'}
    </div>`;
}

async function addQuestion() {
  const text = $('#nq-text').value.trim();
  const options = $('#nq-opts').value.split('\n').map(s => s.trim()).filter(Boolean);
  const correct = parseInt($('#nq-correct').value) - 1;
  const time_limit = parseInt($('#nq-time').value) || 30;
  try {
    await post('/api/admin/questions', { text, options, correct_idx: correct, time_limit });
    toast('✅ Savol qo’shildi');
    renderAdmin();
  } catch (e) { toast(e.message); }
}
async function toggleQuestion(id, active) {
  try { await api(`/api/admin/questions/${id}`, { method: 'PATCH', body: JSON.stringify({ active: !!active }) }); renderAdmin(); }
  catch (e) { toast(e.message); }
}
async function delQuestion(id) {
  if (!confirm('Savol o’chirilsinmi?')) return;
  try { await api(`/api/admin/questions/${id}`, { method: 'DELETE' }); renderAdmin(); }
  catch (e) { toast(e.message); }
}
window.addQuestion = addQuestion; window.toggleQuestion = toggleQuestion; window.delQuestion = delQuestion;

async function admChannels(el) {
  const d = await api('/api/admin/channels');
  el.innerHTML = `
    <div class="card">
      <b>📢 Majburiy obuna kanallari</b>
      <p class="hint" style="margin:6px 0 10px">Bot kanalga <b>admin</b> qilib qo'shilgan bo'lishi shart, aks holda obunani tekshira olmaydi.</p>
      <label class="fld">Kanal @username yoki -100… ID</label>
      <input id="nch-id" placeholder="@mykanal">
      <label class="fld">Taklif havolasi (ixtiyoriy, yopiq kanallar uchun)</label>
      <input id="nch-link" placeholder="https://t.me/+abc…">
      <button class="btn g-adm" onclick="addChannel()">Qo'shish</button>
    </div>
    <div class="card"><b>Ro'yxat (${d.channels.length})</b>
      ${d.channels.map(c => `
        <div class="adm-item mt" style="margin-top:8px">
          <div class="top"><span><b>${esc(c.title)}</b><div class="meta">${esc(c.chat_id)}</div></span>
          <button class="chip red" onclick="delChannel(${c.id})">🗑</button></div>
        </div>`).join('') || '<div class="empty">Kanallar qo’shilmagan — obuna talab qilinmaydi</div>'}
    </div>`;
}
async function addChannel() {
  try {
    await post('/api/admin/channels', { chat_id: $('#nch-id').value.trim(), invite_link: $('#nch-link').value.trim() });
    toast('✅ Kanal qo’shildi');
    renderAdmin();
  } catch (e) { toast(e.message); }
}
async function delChannel(id) {
  if (!confirm('Kanal olib tashlansinmi?')) return;
  try { await api(`/api/admin/channels/${id}`, { method: 'DELETE' }); renderAdmin(); }
  catch (e) { toast(e.message); }
}
window.addChannel = addChannel; window.delChannel = delChannel;

async function admPolls(el) {
  const d = await api('/api/admin/polls');
  el.innerHTML = `
    <div class="card">
      <b>➕ Yangi so'rovnoma</b>
      <div class="mt">
        <label class="fld">Sarlavha</label>
        <input id="np-title" placeholder="Masalan: Eng yaxshi kitob?">
        <label class="fld">Izoh (ixtiyoriy)</label>
        <input id="np-desc" placeholder="Qisqacha tavsif">
        <label class="fld">Variantlar (har qatorda bittadan)</label>
        <textarea id="np-opts" rows="4" placeholder="Variant 1&#10;Variant 2"></textarea>
        <button class="btn g-adm" onclick="addPoll()">Yaratish</button>
      </div>
    </div>
    ${d.polls.map(p => `
      <div class="adm-item">
        <div class="top"><span><b>${esc(p.title)}</b>
          <div class="meta">${p.status === 'active' ? '🟢 Faol' : p.status === 'closed' ? '⚪ Yakunlangan' : '📝 Qoralama'} · ${p.total_votes} ovoz</div></span></div>
        <div class="meta">${p.options.map(o => `${esc(o.text)} (${o.votes})`).join(' · ')}</div>
        <div class="acts">
          ${p.status !== 'active' ? `<button class="chip green" onclick="pollAction(${p.id},'start')">▶️ Boshlash</button>` : ''}
          ${p.status === 'active' ? `<button class="chip" onclick="pollAction(${p.id},'close')">⏹ Yakunlash</button>` : ''}
          <button class="chip red" onclick="pollAction(${p.id},'delete', true)">🗑</button>
        </div>
      </div>`).join('') || '<div class="empty">So’rovnomalar yo’q</div>'}`;
}
async function addPoll() {
  try {
    await post('/api/admin/polls', {
      title: $('#np-title').value.trim(),
      description: $('#np-desc').value.trim(),
      options: $('#np-opts').value.split('\n').map(s => s.trim()).filter(Boolean),
    });
    toast('✅ So’rovnoma yaratildi');
    renderAdmin();
  } catch (e) { toast(e.message); }
}
async function pollAction(id, action, confirmIt) {
  if (confirmIt && !confirm('O’chirilsinmi?')) return;
  try { await post(`/api/admin/polls/${id}/${action}`); renderAdmin(); }
  catch (e) { toast(e.message); }
}
window.addPoll = addPoll; window.pollAction = pollAction;

async function admDraw(el) {
  const d = await api('/api/referrals');
  el.innerHTML = `
    <div id="draw-result"></div>
    <div class="card">
      <b>🎰 Sirli sovg'a g'olibini aniqlash</b>
      <p class="hint" style="margin:6px 0 12px">Tasodifiy (random) tanlov. Natija darhol ro'yxatga yoziladi.</p>
      <button class="btn g-ref" onclick="draw(1)">🎁 1-guruhdan g'olib (${d.group1.filter(m => m.refs < d.group2_min).length} nomzod)</button>
      <button class="btn g-quiz mt" onclick="draw(2)">💎 2-guruhdan g'olib (${d.group2.length} nomzod)</button>
    </div>
    ${d.winners.length ? `<div class="card"><b>🏅 G'oliblar tarixi</b>
      ${d.winners.map(w => `<div class="lb-row" style="margin-top:8px">
        <div class="lb-rank">${w.group === 2 ? '💎' : '🎁'}</div>
        <div class="lb-name">${esc(w.name)}<div class="lb-sub">${w.refs} taklif · ${w.date}</div></div>
      </div>`).join('')}</div>` : ''}`;
}
async function draw(group) {
  try {
    const r = await post('/api/admin/draw', { group });
    $('#draw-result').innerHTML = `
      <div class="winner-flash">
        <div style="font-size:40px">🎉</div>
        <div class="wname">${esc(r.winner.name)}</div>
        <div class="hint">${r.winner.refs} taklif · ${group}-guruh g'olibi · ID: ${r.winner.id}</div>
      </div>`;
    tg?.HapticFeedback?.notificationOccurred('success');
  } catch (e) { toast(e.message); }
}
window.draw = draw;

async function admSettings(el) {
  const s = await api('/api/admin/settings');
  el.innerHTML = `
    <div class="card">
      <b>🔧 Sozlamalar</b>
      <div class="mt">
        <label class="fld">Kunlik savollar soni</label>
        <input id="st-count" type="number" min="1" value="${s.daily_question_count}">
        <label class="fld">Standart vaqt (soniya)</label>
        <input id="st-time" type="number" min="5" value="${s.default_time_limit}">
        <label class="fld">1-guruh uchun minimal takliflar</label>
        <input id="st-g1" type="number" min="1" value="${s.ref_group1_min}">
        <label class="fld">2-guruh uchun minimal takliflar</label>
        <input id="st-g2" type="number" min="1" value="${s.ref_group2_min}">
        <button class="btn g-adm" onclick="saveSettings()">Saqlash</button>
      </div>
    </div>`;
}
async function saveSettings() {
  try {
    await post('/api/admin/settings', {
      daily_question_count: $('#st-count').value,
      default_time_limit: $('#st-time').value,
      ref_group1_min: $('#st-g1').value,
      ref_group2_min: $('#st-g2').value,
    });
    toast('✅ Saqlandi');
  } catch (e) { toast(e.message); }
}
window.saveSettings = saveSettings;

boot();
