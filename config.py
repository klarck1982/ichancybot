import os

# ===== Telegram =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")

# ===== Dashboard credentials (ichancy100.com) =====
AGENT_USERNAME = os.getenv("AGENT_USERNAME", "your_email@gmail.com")
AGENT_PASSWORD = os.getenv("AGENT_PASSWORD", "your_password")
PARENT_ID = os.getenv("PARENT_ID", "2751155")

# ===== API endpoints =====
# الداشبورد الجديد: agents.ichancy100.com
BASE_URL = os.getenv("BASE_URL", "https://agents.ichancy100.com/global/api")

CURRENCY_CODE = os.getenv("CURRENCY_CODE", "NSP")
MONEY_STATUS = int(os.getenv("MONEY_STATUS", "5"))

# ===== HTTP client =====
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "30"))
