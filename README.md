# 🎰 Ichancy Telegram Bot

بوت تيليغرام لإدارة حسابات Ichancy (تسجيل، إيداع، سحب، رصيد).

## ⚙️ الإعداد على Railway

### 1. ارفع المشروع على GitHub
```bash
git init
git add .
git commit -m "first commit"
git remote add origin https://github.com/YOUR_USERNAME/ichancy-bot.git
git push -u origin main
```

### 2. أنشئ مشروعاً على Railway
- اذهب إلى https://railway.app
- اضغط **New Project → Deploy from GitHub**
- اختر الريبو

### 3. أضف المتغيرات في Railway
اذهب إلى **Variables** وأضف:
```
BOT_TOKEN=your_telegram_bot_token
AGENT_USERNAME=your_email@gmail.com
AGENT_PASSWORD=your_password
PARENT_ID=2751155
```

### 4. Railway سيبني ويشغل تلقائياً ✅

---

## 📁 هيكلة المشروع
```
ichancy_bot/
├── main.py              # نقطة البداية
├── config.py            # الإعدادات
├── requirements.txt     # المكتبات
├── railway.toml         # إعدادات Railway
├── api/
│   └── ichancy.py       # طلبات API مع Playwright
├── handlers/
│   ├── register.py      # تسجيل لاعب جديد
│   └── balance.py       # إيداع / سحب / رصيد
└── database/
    └── db.py            # SQLite
```

## 🤖 أوامر البوت
| الزر | الوظيفة |
|------|---------|
| 📝 تسجيل لاعب جديد | إنشاء حساب على ichancy |
| 💰 إيداع | إضافة رصيد |
| 💸 سحب | سحب رصيد |
| 💳 عرض الرصيد | الرصيد الحالي |
| 📊 سجل العمليات | آخر 5 عمليات |
