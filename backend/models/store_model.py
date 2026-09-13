import os
import json
import copy
import random
import shutil
import logging
import threading
from contextlib import contextmanager
from backend.core.config import DATA_FILE, DATA_BACKUP_FILE, DEFAULT_STORE_CONFIG

logger = logging.getLogger("MihQuanStore")
_DATA_LOCK = threading.RLock()


def _load_data_internal() -> dict:
    data = None
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Lỗi đọc {DATA_FILE}: {e}")
            if os.path.exists(DATA_BACKUP_FILE):
                try:
                    with open(DATA_BACKUP_FILE, "r", encoding="utf-8") as bf:
                        data = json.load(bf)
                except Exception as be:
                    logger.error(f"Lỗi đọc backup: {be}")

    if not data:
        data = copy.deepcopy(DEFAULT_STORE_CONFIG)

    if not isinstance(data.get("processedTxCodes"), list):
        data["processedTxCodes"] = []
    if not isinstance(data.get("users"), dict):
        data["users"] = {}
    if not isinstance(data.get("categories"), list):
        data["categories"] = []
    if not isinstance(data.get("products"), list):
        data["products"] = []
    if not isinstance(data.get("vouchers"), dict):
        data["vouchers"] = copy.deepcopy(DEFAULT_STORE_CONFIG["vouchers"])
    if not isinstance(data.get("giftcodes"), dict):
        data["giftcodes"] = copy.deepcopy(DEFAULT_STORE_CONFIG["giftcodes"])
    if "musicUrl" not in data:
        data["musicUrl"] = ""

    shop = data.setdefault("shopInfo", {})
    shop.setdefault("bankCode", "MB")
    shop.setdefault("bankAccount", "0365908079")
    shop.setdefault("accountName", "LE MINH QUAN")
    shop.setdefault("name", "Mih Quân - Store Hack")
    shop.setdefault("notice", "CỬA HÀNG SẴN SÀNG - VUI LÒNG CHỌN SẢN PHẨM")

    bank = data.setdefault("bankApi", {})
    bank.setdefault("url", "https://thueapibank.vn/historyapimbbank/{token}")
    bank["token"] = os.getenv("BANK_API_TOKEN", bank.get("token", "")).strip()
    bank.setdefault("prefix", "MIHQUAN")

    return data

def _save_data_internal(data: dict) -> bool:
    if isinstance(data.get("processedTxCodes"), list) and len(data["processedTxCodes"]) > 1000:
        data["processedTxCodes"] = data["processedTxCodes"][-1000:]

    temp_file = f"{DATA_FILE}.tmp_{random.randint(1000, 9999)}"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if os.path.exists(DATA_FILE):
            shutil.copyfile(DATA_FILE, DATA_BACKUP_FILE)
        os.replace(temp_file, DATA_FILE)
        return True
    except Exception as e:
        logger.error(f"Lỗi lưu file {DATA_FILE}: {e}")
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
        return False

def load_server_store_data() -> dict:
    with _DATA_LOCK:
        return _load_data_internal()

def save_server_store_data(data: dict) -> bool:
    with _DATA_LOCK:
        return _save_data_internal(data)

@contextmanager
def store_data_transaction():
    """Atomic transaction context manager for read-modify-write operations to prevent double-spending."""
    with _DATA_LOCK:
        data = _load_data_internal()
        try:
            yield data
        finally:
            _save_data_internal(data)

