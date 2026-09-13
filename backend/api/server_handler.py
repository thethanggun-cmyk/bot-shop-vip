import os
import json
import re
import string
import random
import html
import hashlib
import mimetypes
import urllib.parse
import urllib.request
import logging
from datetime import datetime
from http.server import SimpleHTTPRequestHandler
from backend.core.config import (
    UPLOAD_DIR,
    STATIC_DIR,
    INDEX_HTML_PATH,
    VN_TZ,
    verify_telegram_init_data,
    DEFAULT_WEBAPP_URL
)
from backend.core.utils import (
    check_ip_vpn,
    notify_all_admins,
    send_telegram_direct,
    format_duration,
    get_tx_timestamp
)
import time
import threading
from backend.core.emoji_catalog import TG_EMOJI
from backend.models.store_model import (
    load_server_store_data,
    save_server_store_data,
    store_data_transaction
)

logger = logging.getLogger("MihQuanStore")

_BANK_CACHE = {
    "token": "",
    "timestamp": 0.0,
    "transactions": []
}
_BANK_CACHE_LOCK = threading.Lock()

def fetch_bank_transactions(api_url: str, api_token: str) -> list:
    global _BANK_CACHE
    now = time.time()
    with _BANK_CACHE_LOCK:
        if _BANK_CACHE["token"] == api_token and (now - _BANK_CACHE["timestamp"]) < 4.0:
            return _BANK_CACHE["transactions"]

    target_url = api_url.replace("{token}", api_token).replace("%7Btoken%7D", api_token)
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    req = urllib.request.Request(target_url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=10) as response:
        raw_data = response.read().decode("utf-8")
        res_json = json.loads(raw_data)

    transactions = []
    if isinstance(res_json, dict):
        transactions = res_json.get("TranList") or res_json.get("transactions") or res_json.get("data") or []
    elif isinstance(res_json, list):
        transactions = res_json

    if not isinstance(transactions, list):
        transactions = []

    with _BANK_CACHE_LOCK:
        _BANK_CACHE["token"] = api_token
        _BANK_CACHE["timestamp"] = now
        _BANK_CACHE["transactions"] = transactions

    return transactions


def get_clean_webapp_url(params: dict = None) -> str:
    base_url = (os.getenv("RENDER_EXTERNAL_URL") or os.getenv("WEBAPP_URL") or DEFAULT_WEBAPP_URL).strip()
    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        base_url = f"https://{base_url}"
    elif base_url.startswith("http://"):
        base_url = "https://" + base_url[7:]
    base_url = base_url.rstrip("/")
    if params:
        query_string = urllib.parse.urlencode(params)
        return f"{base_url}/?{query_string}"
    return f"{base_url}/"

class SecurityHTTPHandler(SimpleHTTPRequestHandler):
    def _send_security_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Telegram-Init-Data")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-XSS-Protection", "1; mode=block")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_security_headers()
        self.end_headers()

    def do_GET(self):
        clean_path = self.path.split("?")[0].rstrip("/")

        if clean_path.startswith("/uploads/"):
            rel_path = clean_path[len("/uploads/"):].lstrip("/")
            file_path = os.path.abspath(os.path.join(UPLOAD_DIR, rel_path))
            upload_root = os.path.abspath(UPLOAD_DIR)

            if not file_path.startswith(upload_root) or not os.path.exists(file_path) or not os.path.isfile(file_path):
                self._send_json_response(404, {"error": "File not found"})
                return

            file_size = os.path.getsize(file_path)
            ext = os.path.splitext(file_path)[1].lower()
            mime = "audio/mpeg" if ext == ".mp3" else ("image/png" if ext == ".png" else "image/jpeg")

            range_header = self.headers.get("Range")
            if range_header and range_header.startswith("bytes="):
                try:
                    ranges = range_header.replace("bytes=", "").split("-")
                    start = int(ranges[0]) if ranges[0] else 0
                    end = int(ranges[1]) if len(ranges) > 1 and ranges[1] else file_size - 1
                    if start >= file_size:
                        self.send_response(416)
                        self.send_header("Content-Range", f"bytes */{file_size}")
                        self.end_headers()
                        return
                    end = min(end, file_size - 1)
                    length = end - start + 1

                    self.send_response(206)
                    self.send_header("Content-Type", mime)
                    self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                    self.send_header("Content-Length", str(length))
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self._send_security_headers()
                    self.end_headers()

                    with open(file_path, "rb") as f:
                        f.seek(start)
                        self.wfile.write(f.read(length))
                    return
                except Exception as e:
                    logger.error(f"Lỗi stream upload: {e}")

            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "public, max-age=86400")
            self._send_security_headers()
            self.end_headers()
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
            return

        if clean_path.startswith("/static/"):
            rel_path = clean_path[len("/static/"):].lstrip("/")
            file_path = os.path.abspath(os.path.join(STATIC_DIR, rel_path))
            static_root = os.path.abspath(STATIC_DIR)

            if not file_path.startswith(static_root) or not os.path.exists(file_path) or not os.path.isfile(file_path):
                self._send_json_response(404, {"error": "Static file not found"})
                return

            ext = os.path.splitext(file_path)[1].lower()
            mime_types = {
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".json": "application/json; charset=utf-8",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".svg": "image/svg+xml",
                ".ico": "image/x-icon",
                ".woff": "font/woff",
                ".woff2": "font/woff2",
                ".ttf": "font/ttf"
            }
            content_type = mime_types.get(ext, mimetypes.guess_type(file_path)[0] or "application/octet-stream")

            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self._send_security_headers()
                self.end_headers()
                self.wfile.write(content)
                return
            except Exception as e:
                logger.error(f"Lỗi đọc static: {e}")
                self._send_json_response(500, {"error": "Internal error reading file"})
                return

        if clean_path == "/health":
            self._send_json_response(200, {"status": "ok"})
            return

        if clean_path == "/api/shop-data":
            store_data = load_server_store_data()
            users = store_data.get("users", {})
            top_depositors = []
            for uid, u in users.items():
                tot_dep = int(u.get("totalDeposit", 0))
                if tot_dep >= 50000:
                    top_depositors.append({
                        "id": uid,
                        "name": u.get("name") or "Khách hàng",
                        "totalDeposit": tot_dep,
                        "role": u.get("role", "customer")
                    })
            top_depositors.sort(key=lambda x: x["totalDeposit"], reverse=True)
            top_depositors = top_depositors[:10]

            sanitized = {
                "shopInfo": store_data.get("shopInfo", {}),
                "bankApi": {
                    "prefix": store_data.get("bankApi", {}).get("prefix", "MIHQUAN")
                },
                "musicUrl": store_data.get("musicUrl", ""),
                "theme": store_data.get("theme", {}),
                "categories": store_data.get("categories", []),
                "accCategories": store_data.get("accCategories", []),
                "products": [
                    {k: v for k, v in p.items() if k != "keys"}
                    for p in store_data.get("products", [])
                ],
                "recentTransactions": store_data.get("recentTransactions", []),
                "topDepositors": top_depositors
            }
            self._send_json_response(200, sanitized)
            return

        if clean_path == "/api/user-profile":
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            init_data = self.headers.get("X-Telegram-Init-Data")
            verified_user = verify_telegram_init_data(init_data) if init_data else None

            if verified_user:
                uid = str(verified_user.get("id"))
            elif query_params.get("preview", ["0"])[0] == "1" or query_params.get("admin", ["0"])[0] == "1":
                uid = query_params.get("uid", ["0"])[0]
            else:
                self._send_json_response(401, {"error": "Unauthorized Telegram Session"})
                return

            store_data = load_server_store_data()
            users = store_data.get("users", {})
            user_data = users.get(uid, {
                "balance": 0,
                "spent": 0,
                "totalDeposit": 0,
                "role": "customer",
                "inventory": [],
                "depositHistory": []
            })
            self._send_json_response(200, user_data)
            return


        if clean_path == "/api/check-security":
            client_ip = self.headers.get("CF-Connecting-IP") or self.headers.get("X-Forwarded-For") or self.client_address[0]
            if "," in client_ip:
                client_ip = client_ip.split(",")[0].strip()

            is_vpn = check_ip_vpn(client_ip)
            self._send_json_response(200, {
                "vpn_detected": is_vpn,
                "ip": client_ip
            })
            return

        if clean_path in ("", "/", "/index.html", "/mihquan-store"):
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            if any(k in query_params for k in ("uid", "avatar", "name", "is_admin")):
                filtered_query = {k: v for k, v in query_params.items() if k not in ("uid", "avatar", "name", "is_admin")}
                redirect_target = "/"
                if filtered_query:
                    redirect_target = f"/?{urllib.parse.urlencode(filtered_query, doseq=True)}"
                self.send_response(302)
                self.send_header("Location", redirect_target)
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                self._send_security_headers()
                self.end_headers()
                return

            if os.path.exists(INDEX_HTML_PATH):
                try:
                    with open(INDEX_HTML_PATH, "rb") as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(content)))
                    self._send_security_headers()
                    self.end_headers()
                    self.wfile.write(content)
                    return
                except Exception as e:
                    logger.error(f"Lỗi gửi index.html: {e}")

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self._send_security_headers()
            self.end_headers()
            self.wfile.write("<h1>Mih Quân - Store Hack Mini App</h1>".encode("utf-8"))
            return

        self._send_json_response(403, {"error": "Access Denied"})

    def do_POST(self):
        clean_path = self.path.split("?")[0].rstrip("/")

        if clean_path == "/api/notify-activity":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                act_type = payload.get("type", "unknown")
                u_id = str(payload.get("user_id", "0"))
                u_name = html.escape(str(payload.get("user_name", "Khách hàng")))
                now_str = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")

                if act_type == "open_app":
                    notify_all_admins(
                        f"{TG_EMOJI['ROCKET']} <b>[HOẠT ĐỘNG] KHÁCH MỞ CỬA HÀNG</b>\n"
                        f"────────────────────────\n"
                        f"• Người dùng: <b>{u_name}</b> (<code>{u_id}</code>)\n"
                        f"• Thời gian: <code>{now_str}</code>"
                    )
                elif act_type == "view_deposit":
                    notify_all_admins(
                        f"{TG_EMOJI['CARD']} <b>[HOẠT ĐỘNG] KHÁCH VÀO TAB NẠP TIỀN</b>\n"
                        f"────────────────────────\n"
                        f"• Người dùng: <b>{u_name}</b> (<code>{u_id}</code>)\n"
                        f"• Đang xem mã VietQR MBBank tự động."
                    )
                self._send_json_response(200, {"success": True})
            except Exception as e:
                self._send_json_response(500, {"success": False, "message": str(e)})
            return

        if clean_path == "/api/purchase":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                init_data = self.headers.get("X-Telegram-Init-Data")
                verified_user = verify_telegram_init_data(init_data) if init_data else None

                # Security: Enforce Telegram authentication to prevent BOLA/IDOR
                if not verified_user:
                    self._send_json_response(401, {
                        "success": False,
                        "message": "Phiên làm việc Telegram không hợp lệ hoặc đã hết hạn! Vui lòng mở lại từ Telegram Bot."
                    })
                    return

                uid = str(verified_user.get("id"))
                prod_id = payload.get("prod_id")
                raw_user_name = verified_user.get("first_name") or str(payload.get("user_name", "Khách hàng"))
                user_name = html.escape(str(raw_user_name)[:50])

                delivered_key = None
                user_record_snapshot = None
                prod_name = ""
                duration_label = ""
                effective_price = 0
                price_type_label = ""
                stock_left = 0

                # Atomic transaction to prevent double spending / race condition
                with store_data_transaction() as current_data:
                    users = current_data.setdefault("users", {})
                    user_record = users.setdefault(uid, {
                        "balance": 0, "spent": 0, "totalDeposit": 0, "role": "customer", "inventory": [], "depositHistory": []
                    })

                    prod = next((p for p in current_data.get("products", []) if p.get("id") == prod_id), None)
                    if not prod:
                        self._send_json_response(400, {"success": False, "message": "Sản phẩm không tồn tại!"})
                        return

                    keys_list = prod.get("keys", [])
                    if prod.get("stock", 0) <= 0 or not keys_list:
                        self._send_json_response(400, {"success": False, "message": "Sản phẩm đã hết hàng trong kho!"})
                        return

                    is_seller = (user_record.get("role") == "seller")
                    seller_price = int(prod.get("sellerPrice") or 0)
                    regular_price = int(prod.get("price", 0))

                    effective_price = regular_price
                    price_type_label = "Giá Khách Lẻ"
                    if is_seller and seller_price > 0:
                        effective_price = seller_price
                        price_type_label = "Giá Seller VIP"

                    if user_record["balance"] < effective_price:
                        self._send_json_response(400, {
                            "success": False,
                            "message": f"Số dư không đủ! Cần {effective_price:,}đ. Vui lòng nạp thêm."
                        })
                        return

                    delivered_key = keys_list.pop(0)
                    prod["stock"] = len(keys_list)
                    stock_left = prod["stock"]

                    user_record["balance"] -= effective_price
                    user_record["spent"] += effective_price

                    duration_label = format_duration(prod.get("duration", "1d"))
                    now_time = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
                    prod_name = html.escape(str(prod.get('name', '')))

                    user_record.setdefault("inventory", []).insert(0, {
                        "productName": f"{prod.get('name')} ({duration_label})",
                        "secretKey": delivered_key,
                        "time": now_time
                    })

                    current_data.setdefault("recentTransactions", []).insert(0, {
                        "name": user_name,
                        "type": "mua",
                        "amount": effective_price,
                        "time": datetime.now().strftime("%H:%M")
                    })
                    current_data["recentTransactions"] = current_data["recentTransactions"][:15]

                    user_record_snapshot = {
                        "balance": user_record["balance"],
                        "spent": user_record["spent"]
                    }

                if uid.isdigit():
                    send_telegram_direct(
                        int(uid),
                        f"{TG_EMOJI['GIFT']} <b>GIAO DỊCH MUA KEY THÀNH CÔNG!</b>\n"
                        f"────────────────────────\n"
                        f"• Sản phẩm: <b>{prod_name}</b>\n"
                        f"• Thời hạn: <b>{duration_label}</b>\n"
                        f"• Mức giá: <b>{effective_price:,} VNĐ</b> ({price_type_label})\n"
                        f"• Số dư còn lại: <b>{user_record_snapshot['balance']:,} VNĐ</b>\n\n"
                        f"{TG_EMOJI['KEY']} <b>MÃ KEY CỦA BẠN:</b>\n"
                        f"<code>{html.escape(delivered_key)}</code>\n\n"
                        f"📌 <i>Mã này được lưu vĩnh viễn trong tin nhắn này.</i>"
                    )

                notify_all_admins(
                    f"{TG_EMOJI['SHOPPING']} <b>[ĐƠN HÀNG MỚI] BÁN KEY THÀNH CÔNG!</b>\n"
                    f"────────────────────────\n"
                    f"• Khách: <b>{user_name}</b> (<code>{uid}</code>)\n"
                    f"• Sản phẩm: <b>{prod_name}</b> ({duration_label})\n"
                    f"• Thu về: <b>{effective_price:,} VNĐ</b> ({price_type_label})\n"
                    f"• Key cấp: <code>{html.escape(delivered_key)}</code>\n"
                    f"• Tồn kho còn lại: <b>{stock_left}</b>"
                )

                self._send_json_response(200, {
                    "success": True,
                    "key": delivered_key,
                    "balance": user_record_snapshot["balance"],
                    "spent": user_record_snapshot["spent"]
                })
            except Exception as e:
                logger.error(f"Lỗi mua hàng: {e}")
                self._send_json_response(500, {"success": False, "message": str(e)})
            return

        if clean_path == "/api/check-deposit":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")

            try:
                data = json.loads(body)
                init_data = self.headers.get("X-Telegram-Init-Data")
                verified_user = verify_telegram_init_data(init_data) if init_data else None

                # Security: Enforce Telegram authentication
                if not verified_user:
                    self._send_json_response(401, {"success": False, "message": "Phiên làm việc Telegram không hợp lệ!"})
                    return

                user_id = str(verified_user.get("id"))
                raw_user_name = verified_user.get("first_name") or str(data.get("user_name", "Khách hàng"))
                user_name = html.escape(str(raw_user_name)[:50])

                store_data = load_server_store_data()
                api_url = store_data.get("bankApi", {}).get("url", "https://thueapibank.vn/historyapimbbank/{token}")
                api_token = store_data.get("bankApi", {}).get("token", "").strip()
                bank_prefix = store_data.get("bankApi", {}).get("prefix", "MIHQUAN").strip().upper()

                min_amount = int(data.get("amount", 1000))
                if min_amount < 1000:
                    min_amount = 1000

                if not api_token:
                    self._send_json_response(200, {"success": False, "message": "Chưa cài đặt BANK_API_TOKEN!"})
                    return

                # Cached bank API request to avoid rate-limiting
                transactions = fetch_bank_transactions(api_url, api_token)

                if not transactions:
                    self._send_json_response(200, {
                        "success": False,
                        "message": "Chưa có biến động số dư nào từ ngân hàng."
                    })
                    return

                matched_transaction = None
                clean_user_id = re.sub(r"[^0-9]", "", user_id).strip()
                now_ts = datetime.now(VN_TZ).timestamp()
                processed_set = set(store_data.get("processedTxCodes", []))

                for item in transactions:
                    if not isinstance(item, dict):
                        continue

                    credit_amt_raw = str(item.get("creditAmount") or item.get("Amount") or "0").replace(",", "").replace(".", "").strip()
                    debit_amt_raw = str(item.get("debitAmount") or "0").replace(",", "").replace(".", "").strip()

                    try:
                        amount_val = int(credit_amt_raw)
                    except ValueError:
                        amount_val = 0

                    is_credit = False
                    if amount_val > 0 and (debit_amt_raw == "0" or not debit_amt_raw):
                        is_credit = True

                    if is_credit and amount_val >= min_amount:
                        tx_ts = get_tx_timestamp(item)
                        # Expand window to 15 minutes (900s) to prevent false negative rejections
                        if tx_ts > 0:
                            time_diff = now_ts - tx_ts
                            if time_diff > 900.0 or time_diff < -180.0:
                                continue

                        desc = (str(item.get("description", "")) + " " + str(item.get("Description", "")) + " " + str(item.get("Remark", ""))).upper()
                        clean_desc = re.sub(r"[^A-Z0-9]", "", desc)

                        if bank_prefix not in clean_desc:
                            continue

                        ref_no = str(item.get("refNo") or item.get("tranId") or "").strip()
                        tx_date = str(item.get("transactionDate") or item.get("postingDate") or "").strip()

                        ref_id = f"{tx_date}_{ref_no}_{amount_val}" if ref_no else f"MB_{hashlib.sha256(desc.encode()).hexdigest()[:16]}_{amount_val}"

                        if ref_id in processed_set:
                            continue

                        if clean_user_id and clean_user_id in clean_desc:
                            matched_transaction = {
                                "tx_id": ref_id,
                                "amount": amount_val,
                                "description": desc,
                                "time": tx_date or datetime.now().strftime("%H:%M:%S")
                            }
                            break

                if matched_transaction:
                    now_str = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
                    new_balance = 0

                    # Atomic transaction update
                    with store_data_transaction() as current_store:
                        cur_processed = set(current_store.setdefault("processedTxCodes", []))
                        if matched_transaction["tx_id"] in cur_processed:
                            # Already processed by another concurrent request
                            self._send_json_response(200, {
                                "success": True,
                                "message": "Giao dịch đã được cập nhật thành công!"
                            })
                            return

                        current_store["processedTxCodes"].append(matched_transaction["tx_id"])
                        users = current_store.setdefault("users", {})
                        user_record = users.setdefault(user_id, {
                            "balance": 0, "spent": 0, "totalDeposit": 0, "role": "customer", "inventory": [], "depositHistory": []
                        })
                        user_record["balance"] += matched_transaction["amount"]
                        user_record["totalDeposit"] += matched_transaction["amount"]
                        new_balance = user_record["balance"]

                        user_record.setdefault("depositHistory", []).insert(0, {
                            "method": "VietQR MBBank Auto 24/7",
                            "amount": matched_transaction["amount"],
                            "status": "Thành công",
                            "time": now_str
                        })

                        current_recent = current_store.setdefault("recentTransactions", [])
                        current_recent.insert(0, {
                            "name": user_name,
                            "type": "nạp",
                            "amount": matched_transaction["amount"],
                            "time": datetime.now().strftime("%H:%M")
                        })
                        current_store["recentTransactions"] = current_recent[:15]

                    if user_id.isdigit():
                        send_telegram_direct(
                            int(user_id),
                            f"{TG_EMOJI['FIRE']} <b>NẠP TIỀN THÀNH CÔNG!</b>\n"
                            f"────────────────────────\n"
                            f"• Số tiền: <b>+{matched_transaction['amount']:,} VNĐ</b>\n"
                            f"• Số dư mới: <b>{new_balance:,} VNĐ</b>\n"
                            f"• Mã GD: <code>{matched_transaction['tx_id']}</code>\n"
                            f"• Thời gian: <code>{now_str}</code>\n\n"
                            f"Số dư đã được cập nhật!"
                        )

                    notify_all_admins(
                        f"{TG_EMOJI['MONEY']} <b>[AUTO BANK THẬT] NẠP THÀNH CÔNG!</b>\n"
                        f"────────────────────────\n"
                        f"• Khách nạp: <b>{user_name}</b> (<code>{user_id}</code>)\n"
                        f"• Thực nhận: <b>+{matched_transaction['amount']:,} VNĐ</b>\n"
                        f"• Mã GD: <code>{matched_transaction['tx_id']}</code>\n"
                        f"• Số dư tài khoản: <b>{new_balance:,} VNĐ</b>"
                    )

                    self._send_json_response(200, {
                        "success": True,
                        "amount": matched_transaction["amount"],
                        "balance": new_balance,
                        "tx_id": matched_transaction["tx_id"],
                        "message": f"Nạp thành công +{matched_transaction['amount']:,}đ!"
                    })
                else:
                    self._send_json_response(200, {
                        "success": False,
                        "message": "Chưa phát hiện biến động số dư ngân hàng hợp lệ."
                    })

            except Exception as e:
                logger.error(f"Lỗi API Bank: {e}")
                self._send_json_response(200, {"success": False, "message": f"Lỗi: {str(e)}"})
            return

        if clean_path == "/api/redeem-code":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                init_data = self.headers.get("X-Telegram-Init-Data")
                verified_user = verify_telegram_init_data(init_data) if init_data else None

                # Security: Enforce Telegram authentication
                if not verified_user:
                    self._send_json_response(401, {"success": False, "message": "Phiên làm việc Telegram không hợp lệ!"})
                    return

                user_id = str(verified_user.get("id"))
                code = str(payload.get("code", "")).strip().upper()
                code_type = payload.get("type", "voucher")
                now_str = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
                resp_msg = ""
                balance_after = 0
                inventory_after = []

                # Atomic transaction
                with store_data_transaction() as current_data:
                    users = current_data.setdefault("users", {})
                    user_record = users.setdefault(user_id, {
                        "balance": 0, "spent": 0, "totalDeposit": 0, "role": "customer", "inventory": [], "depositHistory": []
                    })

                    code_map = current_data.get("vouchers", {}) if code_type == "voucher" else current_data.get("giftcodes", {})

                    if code not in code_map:
                        self._send_json_response(400, {"success": False, "message": f"Mã {code_type.upper()} không tồn tại hoặc đã hết hạn!"})
                        return

                    item = code_map[code]
                    used_by = item.setdefault("usedBy", [])
                    if user_id in used_by:
                        self._send_json_response(400, {"success": False, "message": "Bạn đã sử dụng mã này rồi!"})
                        return

                    used_by.append(user_id)

                    if item.get("type") == "balance":
                        add_amt = int(item.get("amount", 0))
                        user_record["balance"] += add_amt
                        user_record.setdefault("depositHistory", []).insert(0, {
                            "method": f"Mã {code_type.capitalize()}: {code}",
                            "amount": add_amt,
                            "status": "Thành công",
                            "time": now_str
                        })
                        resp_msg = f"Đã áp dụng mã thành công: +{add_amt:,} VNĐ!"
                    elif item.get("type") == "key":
                        p_name = item.get("productName", "Vật Phẩm Giftcode")
                        p_key = item.get("key", "MIHQUAN-VIP-GIFTCODE")
                        user_record.setdefault("inventory", []).insert(0, {
                            "productName": p_name,
                            "secretKey": p_key,
                            "time": now_str
                        })
                        resp_msg = f"Chúc mừng bạn nhận được {p_name}!"
                        if user_id.isdigit():
                            send_telegram_direct(int(user_id), f"{TG_EMOJI['GIFT']} <b>QUÀ TẶNG GIFTCODE:</b>\n• Tên quà: <b>{html.escape(p_name)}</b>\n• Key: <code>{html.escape(p_key)}</code>")

                    balance_after = user_record["balance"]
                    inventory_after = user_record.get("inventory", [])

                notify_all_admins(
                    f"{TG_EMOJI['GIFT']} <b>[KHÁCH SỬ DỤNG {code_type.upper()}]</b>\n"
                    f"────────────────────────\n"
                    f"• Khách: <code>{user_id}</code>\n"
                    f"• Mã: <code>{html.escape(code)}</code>\n"
                    f"• Kết quả: {html.escape(resp_msg)}"
                )

                self._send_json_response(200, {
                    "success": True,
                    "message": resp_msg,
                    "balance": balance_after,
                    "inventory": inventory_after
                })
            except Exception as e:
                self._send_json_response(500, {"success": False, "message": str(e)})
            return


        self._send_json_response(403, {"error": "Access Denied"})

    def _send_json_response(self, code: int, payload: dict):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        pass
