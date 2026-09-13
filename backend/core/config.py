import os
import time
import json
import logging
import hmac
import hashlib
import urllib.parse
from datetime import timezone, timedelta

logger = logging.getLogger("MihQuanStore")

VN_TZ = timezone(timedelta(hours=7))

BOT_TOKEN = os.getenv("BOT_TOKEN", "8978285583:AAHfPf188aX9t83v_qFIkwP1G7182YBelss").strip()

ADMIN_IDS = [7775104850, 6476569159]
env_admins = os.getenv("ADMIN_IDS")
if env_admins:
    ADMIN_IDS = [int(x.strip()) for x in env_admins.split(",") if x.strip().isdigit()]

DEFAULT_WEBAPP_URL = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("WEBAPP_URL") or "https://demo-mini-app.onrender.com"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DATA_FILE = os.path.join(BASE_DIR, "store_data.json")
DATA_BACKUP_FILE = os.path.join(BASE_DIR, "store_data.json.bak")
INDEX_HTML_PATH = os.path.join(BASE_DIR, "index.html")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

DEFAULT_STORE_CONFIG = {
    "shopInfo": {
        "name": "Mih Quân - Store Hack",
        "notice": "CỬA HÀNG SẴN SÀNG - VUI LÒNG CHỌN SẢN PHẨM",
        "bankCode": "MB",
        "bankAccount": "0365908079",
        "accountName": "LE MINH QUAN"
    },
    "bankApi": {
        "url": "https://thueapibank.vn/historyapimbbank/{token}",
        "token": os.getenv("BANK_API_TOKEN", "e70fe684dea3da0cb1b088c1c3d0c605").strip(),
        "prefix": "MIHQUAN"
    },
    "theme": {
        "primary": "#00e5ff",
        "secondary": "#0070f3",
        "bgBase": "#080c14",
        "bgCard": "#0e1624",
        "border": "#1a2a44"
    },
    "uiText": {
        "shopName": "Mih Quân - Store Hack",
        "shopNotice": "CỬA HÀNG SẴN SÀNG - VUI LÒNG CHỌN SẢN PHẨM"
    },
    "categories": [],
    "products": [],
    "recentTransactions": [],
    "processedTxCodes": [],
    "users": {},
    "vouchers": {
        "MIHQUAN2026": {"type": "balance", "amount": 20000, "usedBy": []},
        "TRIAN50K": {"type": "balance", "amount": 50000, "usedBy": []}
    },
    "giftcodes": {
        "FREEKEYVIP": {"type": "key", "productName": "Key VIP MihQuan", "key": "MIHQUAN-VIP-TEST-888", "usedBy": []},
        "TANTHU": {"type": "balance", "amount": 10000, "usedBy": []}
    },
    "musicUrl": ""
}

def verify_telegram_init_data(init_data_raw: str, bot_token: str = None) -> dict | None:
    token = bot_token or BOT_TOKEN
    if not token or not init_data_raw:
        return None
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data_raw, keep_blank_values=True))
        hash_val = parsed.pop("hash", None)
        if not hash_val:
            return None

        # Validate auth_date (prevent replay attacks older than 7 days)
        auth_date = int(parsed.get("auth_date", 0))
        now = int(time.time())
        if auth_date <= 0 or (now - auth_date > 86400 * 7) or (auth_date - now > 600):
            logger.warning(f"Telegram initData expired or invalid auth_date: {auth_date}")
            return None

        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", token.encode("utf-8"), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

        if hmac.compare_digest(calculated_hash, hash_val):
            user_json = parsed.get("user")
            if user_json:
                if isinstance(user_json, str):
                    return json.loads(user_json)
                return user_json
            return parsed
    except Exception as e:
        logger.error(f"Telegram initData verification error: {e}")
    return None

