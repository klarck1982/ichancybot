# api/ichancy.py - نسخة اختبار (للتحقق من حظر الـ IP)

import logging
from curl_cffi import requests as cf_requests

logger = logging.getLogger(__name__)

class IchancyAPI:
    def __init__(self):
        self.username = "test"
        self.password = "test"

    async def test_ip_block(self):
        """اختبار بسيط لمعرفة إذا كان الـ IP محظور"""
        test_url = "https://agents.ichancy.com/global/api/User/signIn"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Origin": "https://agents.ichancy.com",
            "Referer": "https://agents.ichancy.com/",
        }

        try:
            # طلب بسيط بدون كوكيز
            response = cf_requests.post(
                test_url,
                json={"username": "test", "password": "test"},
                headers=headers,
                impersonate="chrome124",
                timeout=15
            )

            logger.info(f"=== نتيجة اختبار الـ IP ===")
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Response (أول 500 حرف): {response.text[:500]}")

            if response.status_code == 403:
                logger.warning("❌ الـ IP محظور (403) حتى بدون كوكيز")
            elif response.status_code == 200:
                logger.info("✅ الـ IP غير محظور")
            else:
                logger.info(f"رد غير متوقع: {response.status_code}")

            return response.status_code

        except Exception as e:
            logger.error(f"خطأ في الاختبار: {e}")
            return None


api = IchancyAPI()
