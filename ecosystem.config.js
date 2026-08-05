// pm2 konfiguratsiyasi — /root/quizbot/ecosystem.config.js
// Ishga tushirish: cd /root/quizbot && pm2 start ecosystem.config.js

module.exports = {
  apps: [
    {
      name: "quizbot",
      cwd: "/root/quizbot",
      script: "/root/quizbot/app.py",
      interpreter: "/root/quizbot/.venv/bin/python",
      autorestart: true,
      max_restarts: 10,
      env: {
        PYTHONUNBUFFERED: "1",
        HOST: "127.0.0.1",
      },
    },
  ],
};
