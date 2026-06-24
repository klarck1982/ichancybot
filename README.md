# 🎰 Ichancy Telegram Bot

بوت تيليغرام لإدارة حسابات **Ichancy100** (تسجيل، إيداع، سحب، رصيد، سجل).

> **تم التحديث (v6):** استخدام `curl_cffi` لتجاوز Cloudflare (يقلّد بصفة TLS لمتصفح Chrome 124).

---

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
- اذهب إلى [https://railway.app](https://railway.app/)
- اضغط **New Project → Deploy from GitHub**
- اختر الريبو

### 3. أضف المتغيرات في Railway

اذهب إلى **Variables** وأضف:

| المتغير | الوصف | القيمة الافتراضية |
|---|---|---|
| `BOT_TOKEN` | توكن بوت تيليغرام | - |
| `AGENT_USERNAME` | إيميل حساب الـ agent على ichancy100 | - |
| `AGENT_PASSWORD` | كلمة سر الـ agent | - |
| `PARENT_ID` | رقم الـ parent | `2751155` |
| `BASE_URL` | رابط الـ API | `https://agents.ichancy100.com/global/api` |
| `CURRENCY_CODE` | كود العملة | `NSP` |
| `MONEY_STATUS` | حالة المبلغ | `5` |
| `HTTP_TIMEOUT` | مهلة الاتصال (ثانية) | `30` |

### 4. Railway سيبني ويشغل تلقائياً ✅

---

## 📁 هيكلة المشروع

```
ichancy_bot/
├── main.py              # نقطة البداية + لوحة المفاتيح
├── config.py            # الإعدادات (من Environment Variables)
├── requirements.txt     # aiogram + curl-cffi
├── Dockerfile           # Python 3.11-slim
├── railway.toml         # إعدادات Railway
├── nixpacks.toml        # إعدادات Nixpacks
├── api/
│   └── ichancy.py       # طلبات API مع curl_cffi (يقلّد Chrome)
├── handlers/
│   ├── register.py      # تسجيل لاعب جديد
│   └── balance.py       # إيداع / سحب / رصيد / سجل
└── database/
    └── db.py            # SQLite
```

---

## 🔌 الـ API Endpoints المستخدمة

| العملية | Endpoint |
|---|---|
| تسجيل لاعب | `POST /Player/registerPlayer` |
| إيداع | `POST /Player/depositToPlayer` |
| سحب | `POST /Player/withdrawFromPlayer` |
| عرض الرصيد | `POST /Player/getPlayerBalanceById` |
| إحصائيات | `POST /Statistics/getPlayersStatisticsPro` |

كل الطلبات تستخدم **HTTP Basic Auth** (`username:password`).

---

## 🤖 أوامر البوت

| الزر | الوظيفة |
|---|---|
| 📝 تسجيل لاعب جديد | إنشاء حساب على ichancy100 |
| 💰 إيداع | إضافة رصيد |
| 💸 سحب | سحب رصيد |
| 💳 عرض الرصيد | الرصيد الحالي |
| 📊 سجل العمليات | آخر 5 عمليات |

---

## 🛠️ التشغيل المحلي

```bash
pip install -r requirements.txt
export BOT_TOKEN=xxx AGENT_USERNAME=xxx AGENT_PASSWORD=xxx
python main.py
```

---

## 🆕 ما الجديد في v6؟

- ❌ **حذفنا Playwright** (كان بطيء جداً ويستهلك ذاكرة كبيرة)
- ❌ **تجاوزنا مشكلة Cloudflare 403**:
  - `httpx` وحده لا يكفي — Cloudflare يفحص **بصمة TLS** (JA3/JA4) وليس فقط الـ headers
  - ✅ استبدلناه بـ **`curl_cffi`** مع `impersonate="chrome124"` — يقلّد بصمة Chrome الحقيقية
  - النتيجة: `Login → 200` بدلاً من `403 Forbidden` (تم اختباره فعلياً)
- ✅ **إدارة جلسة كاملة** (Login → Cookies → Auto Re-login)
  - `login()` تلقائي عند أول طلب على `/User/signIn`
  - الكوكيز تُحفظ تلقائياً في `AsyncSession`
  - عند انتهاء الجلسة (401/403) → re-login تلقائي + retry
- ✅ **دعم نمط استجابة Ichancy100**
  - الـ API يعيد HTTP 200 دائماً تقريباً حتى عند الفشل
  - الكود يفحص حقل `result` ويُحوّل `result:false` إلى `{"error":...}`
  - يستخرج رسائل الخطأ من `notification[]`
- ✅ **معالجة أخطاء محسّنة** (timeout, network errors, invalid JSON)
- ✅ **إغلاق آمن** (`api.close()` يُستدعى عند إيقاف البوت)
- ✅ **متغيرات جديدة** (`BASE_URL`, `HTTP_TIMEOUT`) لسهولة التبديل بين الداشبوردات

## 🔄 كيف يعمل النظام؟

```
┌──────────────────────────────────────────────────────┐
│  1️⃣  أول طلب (مثل /Player/getPlayerBalanceById)     │
│      ↓                                               │
│  2️⃣  _ensure_login() → login() → GET / (warmup)      │
│      ↓     curl_cffi يحاكي Chrome لتجاوز Cloudflare  │
│  3️⃣  POST /User/signIn (login)                       │
│      ↓                                               │
│  4️⃣  السيرفر يعيد كوكيز (PHPSESSID, __cf_bm, ...)   │
│      ↓                                               │
│  5️⃣  AsyncSession يحفظ الكوكيز تلقائياً              │
│      ↓                                               │
│  6️⃣  الطلب الفعلي يُرسل مع الكوكيز تلقائياً         │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  ⚠️  إذا انتهت الجلسة (HTTP 401/403):               │
│      ↓                                               │
│  ✅  re-login تلقائي + retry مرة واحدة               │
└──────────────────────────────────────────────────────┘
```
