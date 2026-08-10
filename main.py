import os
import json
import time
import threading
from flask import Flask, jsonify, request, send_from_directory
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__, static_folder=".")

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "ĐIỀN_TOKEN_BOT_CỦA_BẠN_VÀO_ĐÂY")
bot = telebot.TeleBot(BOT_TOKEN)

ACC_FILE = "acclv5.txt"
USERS_FILE = "users.json"
DEPOSITS_FILE = "deposits.json"

# CÁC HÀM XỬ LÝ DỮ LIỆU
def ensure_files():
    if not os.path.exists(ACC_FILE):
        open(ACC_FILE, "w", encoding="utf-8").close()
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump({}, f)
    if not os.path.exists(DEPOSITS_FILE):
        with open(DEPOSITS_FILE, "w", encoding="utf-8") as f: json.dump([], f)

def get_users():
    ensure_files()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def get_deposits():
    ensure_files()
    try:
        with open(DEPOSITS_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return []

def save_deposits(data):
    with open(DEPOSITS_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

# ==================== BOT TELEGRAM ====================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    btn = InlineKeyboardButton("🚀 Mở Mini App", url="https://t.me/thethanggun_bot/webapp")
    markup.add(btn)
    
    welcome_text = "👋 Chào mừng bạn đến với **Gun Store**!\nBấm vào nút bên dưới để mở Mini App và mua acc nhé!"
    bot.reply_to(message, welcome_text, parse_mode="Markdown", reply_markup=markup)

def run_bot():
    try:
        print("Bot Telegram đang lắng nghe tin nhắn...")
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print("Lỗi Bot Telegram:", e)

threading.Thread(target=run_bot, daemon=True).start()

# ==================== API FLASK ====================
@app.route("/")
def index():
    if os.path.exists("index.html"):
        return send_from_directory(".", "index.html")
    return "<h3>Lỗi: Không tìm thấy file index.html!</h3>", 404

# API LẤY THÔNG TIN USER (SỐ DƯ)
@app.route("/get-user-info", methods=["GET"])
def get_user_info():
    user_id = str(request.args.get("userId", ""))
    if not user_id: return jsonify({"success": False, "balance": 0})
    
    users = get_users()
    if user_id not in users:
        users[user_id] = {"balance": 0}
        save_users(users)
        
    return jsonify({"success": True, "balance": users[user_id].get("balance", 0)})

# API LẤY KHO ACC
@app.route("/get-stock", methods=["GET"])
def get_stock():
    ensure_files()
    try:
        with open(ACC_FILE, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        return jsonify({"success": True, "stock": len(lines)})
    except Exception as e:
        return jsonify({"success": False, "stock": 0, "error": str(e)})

# API ADD ACC (ADMIN)
@app.route("/acclv5", methods=["POST"])
def add_acc():
    ensure_files()
    data = request.json or {}
    accounts = data.get("accounts", [])
    
    if not accounts:
        return jsonify({"success": False, "message": "Không có dữ liệu acc gửi lên"}), 400
    
    try:
        with open(ACC_FILE, "a", encoding="utf-8") as f:
            for acc in accounts:
                if str(acc).strip():
                    f.write(str(acc).strip() + "\n")
        
        with open(ACC_FILE, "r", encoding="utf-8") as f:
            total = len([line.strip() for line in f if line.strip()])
            
        return jsonify({"success": True, "added_count": len(accounts), "new_stock": total})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# API MUA ACC (XUẤT N ACC & TRỪ SỐ DƯ)
@app.route("/buy-acc", methods=["POST"])
def buy_acc():
    ensure_files()
    data = request.json or {}
    user_id = str(data.get("userId", ""))
    qty = int(data.get("quantity", 1))
    price_per_item = 1600
    total_price = qty * price_per_item

    users = get_users()
    user_balance = users.get(user_id, {}).get("balance", 0)

    # 1. Kiểm tra số dư
    if user_balance < total_price:
        return jsonify({"success": False, "message": f"Số dư không đủ! Bạn cần {total_price:,}đ nhưng hiện tại chỉ có {user_balance:,}đ."}), 400

    # 2. Kiểm tra kho acc
    try:
        with open(ACC_FILE, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        if len(lines) < qty:
            return jsonify({"success": False, "message": f"Kho không đủ tài khoản! Chỉ còn {len(lines)} acc."}), 400

        # Rút N tài khoản
        bought_accounts = [lines.pop(0) for _ in range(qty)]

        # Cập nhật lại kho
        with open(ACC_FILE, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")

        # Trừ số dư user
        users[user_id]["balance"] -= total_price
        save_users(users)

        return jsonify({
            "success": True, 
            "accounts": bought_accounts, 
            "new_balance": users[user_id]["balance"],
            "remaining_stock": len(lines)
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# API GỬI YÊU CẦU NẠP TIỀN
@app.route("/request-deposit", methods=["POST"])
def request_deposit():
    data = request.json or {}
    user_id = str(data.get("userId", ""))
    user_name = data.get("userName", "Gun")
    amount = int(data.get("amount", 0))

    if not user_id or amount <= 0:
        return jsonify({"success": False, "message": "Thông tin nạp không hợp lệ!"}), 400

    deposits = get_deposits()
    dep_obj = {
        "id": int(time.time() * 1000),
        "userId": user_id,
        "userName": user_name,
        "amount": amount,
        "status": "pending",
        "time": time.strftime("%H:%M - %d/%m/%Y")
    }
    deposits.insert(0, dep_obj)
    save_deposits(deposits)

    return jsonify({"success": True, "message": "Đã gửi yêu cầu nạp tiền tới Admin!"})

# API ADMIN: LẤY DANH SÁCH YÊU CẦU NẠP
@app.route("/admin/get-deposits", methods=["GET"])
def admin_get_deposits():
    deposits = get_deposits()
    return jsonify({"success": True, "deposits": deposits})

# API ADMIN: DUYỆT NẠP TIỀN
@app.route("/admin/approve-deposit", methods=["POST"])
def admin_approve_deposit():
    data = request.json or {}
    dep_id = data.get("depositId")

    deposits = get_deposits()
    target = None
    for item in deposits:
        if item["id"] == dep_id:
            target = item
            break

    if not target or target["status"] != "pending":
        return jsonify({"success": False, "message": "Yêu cầu không tồn tại hoặc đã duyệt!"}), 400

    target["status"] = "approved"
    save_deposits(deposits)

    # Cộng tiền cho User
    users = get_users()
    uid = target["userId"]
    if uid not in users: users[uid] = {"balance": 0}
    users[uid]["balance"] += target["amount"]
    save_users(users)

    return jsonify({"success": True, "message": f"Đã duyệt thành công {target['amount']:,}đ cho ID {uid}!"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
