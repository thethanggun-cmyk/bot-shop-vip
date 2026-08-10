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

# KẾT NỐI MONGODB ATLAS (LƯU DỮ LIỆU VĨNH VIỄN TRÊN CLOUD)
MONGO_URI = os.environ.get("MONGO_URI", "")
db = None

if MONGO_URI:
    try:
        from pymongo import MongoClient
        client = MongoClient(MONGO_URI)
        db = client["gun_store"]
        print("✅ Đã kết nối thành công tới Database MongoDB Cloud!")
    except Exception as e:
        print("❌ Lỗi kết nối MongoDB:", e)

# TỆP TẠM DỰ PHÒNG NẾU CHƯA CÓ MONGO_URI
ACC_FILE = "acclv5.txt"
USERS_FILE = "users.json"
DEPOSITS_FILE = "deposits.json"
PURCHASES_FILE = "purchases.json"

def ensure_local_files():
    if not os.path.exists(ACC_FILE): open(ACC_FILE, "w", encoding="utf-8").close()
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump({}, f)
    if not os.path.exists(DEPOSITS_FILE):
        with open(DEPOSITS_FILE, "w", encoding="utf-8") as f: json.dump([], f)
    if not os.path.exists(PURCHASES_FILE):
        with open(PURCHASES_FILE, "w", encoding="utf-8") as f: json.dump([], f)

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

# ==================== ROUTE PHÁT NHẠC MP3 & TRANG CHỦ ====================
@app.route("/")
def index():
    if os.path.exists("index.html"):
        return send_from_directory(".", "index.html")
    return "<h3>Lỗi: Không tìm thấy file index.html!</h3>", 404

# Route phát file nhạc music.mp3
@app.route("/music.mp3")
def serve_music():
    if os.path.exists("music.mp3"):
        return send_from_directory(".", "music.mp3")
    return "No music file found", 404

# ==================== API XỬ LÝ DỮ LIỆU VĨNH VIỄN ====================

@app.route("/get-user-info", methods=["GET"])
def get_user_info():
    user_id = str(request.args.get("userId", ""))
    if not user_id: return jsonify({"success": False, "balance": 0})
    
    if db is not None:
        user = db.users.find_one({"userId": user_id})
        if not user:
            db.users.insert_one({"userId": user_id, "balance": 0})
            return jsonify({"success": True, "balance": 0})
        return jsonify({"success": True, "balance": user.get("balance", 0)})
    else:
        ensure_local_files()
        with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
        if user_id not in users:
            users[user_id] = {"balance": 0}
            with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(users, f, indent=2)
        return jsonify({"success": True, "balance": users[user_id].get("balance", 0)})

@app.route("/get-stock", methods=["GET"])
def get_stock():
    if db is not None:
        count = db.accounts.count_documents({})
        return jsonify({"success": True, "stock": count})
    else:
        ensure_local_files()
        with open(ACC_FILE, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        return jsonify({"success": True, "stock": len(lines)})

@app.route("/acclv5", methods=["POST"])
def add_acc():
    data = request.json or {}
    accounts = data.get("accounts", [])
    if not accounts: return jsonify({"success": False, "message": "Không có acc"}), 400
    
    clean_accs = [str(a).strip() for a in accounts if str(a).strip()]

    if db is not None:
        docs = [{"acc": a} for a in clean_accs]
        if docs: db.accounts.insert_many(docs)
        total = db.accounts.count_documents({})
        return jsonify({"success": True, "added_count": len(clean_accs), "new_stock": total})
    else:
        ensure_local_files()
        with open(ACC_FILE, "a", encoding="utf-8") as f:
            for a in clean_accs: f.write(a + "\n")
        with open(ACC_FILE, "r", encoding="utf-8") as f:
            total = len([l.strip() for l in f if l.strip()])
        return jsonify({"success": True, "added_count": len(clean_accs), "new_stock": total})

@app.route("/buy-acc", methods=["POST"])
def buy_acc():
    data = request.json or {}
    user_id = str(data.get("userId", ""))
    qty = int(data.get("quantity", 1))
    price_per_item = 1600
    total_price = qty * price_per_item

    if db is not None:
        user = db.users.find_one({"userId": user_id}) or {"balance": 0}
        if user.get("balance", 0) < total_price:
            return jsonify({"success": False, "message": f"Số dư không đủ! Cần {total_price:,}đ."}), 400

        acc_docs = list(db.accounts.find().limit(qty))
        if len(acc_docs) < qty:
            return jsonify({"success": False, "message": f"Kho không đủ acc! Còn {len(acc_docs)} acc."}), 400

        bought_accs = [doc["acc"] for doc in acc_docs]
        ids_to_delete = [doc["_id"] for doc in acc_docs]
        db.accounts.delete_many({"_id": {"$in": ids_to_delete}})

        new_bal = user.get("balance", 0) - total_price
        db.users.update_one({"userId": user_id}, {"$set": {"balance": new_bal}}, upsert=True)

        time_str = time.strftime("%H:%M - %d/%m/%Y")
        db.purchases.insert_one({
            "userId": user_id,
            "accs": "\n".join(bought_accs),
            "count": len(bought_accs),
            "time": time_str
        })

        return jsonify({"success": True, "accounts": bought_accs, "new_balance": new_bal})
    else:
        ensure_local_files()
        with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
        user_bal = users.get(user_id, {}).get("balance", 0)

        if user_bal < total_price:
            return jsonify({"success": False, "message": f"Số dư không đủ! Cần {total_price:,}đ."}), 400

        with open(ACC_FILE, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        if len(lines) < qty:
            return jsonify({"success": False, "message": f"Kho chỉ còn {len(lines)} acc."}), 400

        bought_accs = [lines.pop(0) for _ in range(qty)]

        with open(ACC_FILE, "w", encoding="utf-8") as f:
            for l in lines: f.write(l + "\n")

        users[user_id]["balance"] -= total_price
        with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(users, f, indent=2)

        # Lưu Lịch sử Mua Local
        with open(PURCHASES_FILE, "r", encoding="utf-8") as f: purchases = json.load(f)
        time_str = time.strftime("%H:%M - %d/%m/%Y")
        purchases.insert(0, {"userId": user_id, "accs": "\n".join(bought_accs), "count": len(bought_accs), "time": time_str})
        with open(PURCHASES_FILE, "w", encoding="utf-8") as f: json.dump(purchases, f, indent=2)

        return jsonify({"success": True, "accounts": bought_accs, "new_balance": users[user_id]["balance"]})

@app.route("/get-purchases", methods=["GET"])
def get_purchases():
    user_id = str(request.args.get("userId", ""))
    if db is not None:
        items = list(db.purchases.find({"userId": user_id}, {"_id": 0}).sort("_id", -1))
        return jsonify({"success": True, "purchases": items})
    else:
        ensure_local_files()
        with open(PURCHASES_FILE, "r", encoding="utf-8") as f: purchases = json.load(f)
        user_items = [p for p in purchases if p.get("userId") == user_id]
        return jsonify({"success": True, "purchases": user_items})

@app.route("/request-deposit", methods=["POST"])
def request_deposit():
    data = request.json or {}
    user_id = str(data.get("userId", ""))
    user_name = data.get("userName", "Gun")
    amount = int(data.get("amount", 0))

    dep_obj = {
        "id": int(time.time() * 1000),
        "userId": user_id,
        "userName": user_name,
        "amount": amount,
        "status": "pending",
        "time": time.strftime("%H:%M - %d/%m/%Y")
    }

    if db is not None:
        db.deposits.insert_one(dep_obj)
    else:
        ensure_local_files()
        with open(DEPOSITS_FILE, "r", encoding="utf-8") as f: deposits = json.load(f)
        deposits.insert(0, dep_obj)
        with open(DEPOSITS_FILE, "w", encoding="utf-8") as f: json.dump(deposits, f, indent=2)

    return jsonify({"success": True, "message": "Đã gửi yêu cầu nạp tiền!"})

@app.route("/admin/get-deposits", methods=["GET"])
def admin_get_deposits():
    if db is not None:
        items = list(db.deposits.find({"status": "pending"}, {"_id": 0}).sort("_id", -1))
        return jsonify({"success": True, "deposits": items})
    else:
        ensure_local_files()
        with open(DEPOSITS_FILE, "r", encoding="utf-8") as f: deposits = json.load(f)
        pending = [d for d in deposits if d.get("status") == "pending"]
        return jsonify({"success": True, "deposits": pending})

@app.route("/admin/approve-deposit", methods=["POST"])
def admin_approve_deposit():
    data = request.json or {}
    dep_id = data.get("depositId")

    if db is not None:
        target = db.deposits.find_one({"id": dep_id})
        if not target or target.get("status") != "pending":
            return jsonify({"success": False, "message": "Không tìm thấy yêu cầu!"}), 400

        db.deposits.update_one({"id": dep_id}, {"$set": {"status": "approved"}})
        uid = target["userId"]
        amt = target["amount"]
        db.users.update_one({"userId": uid}, {"$inc": {"balance": amt}}, upsert=True)
        return jsonify({"success": True, "message": f"Đã duyệt cộng {amt:,}đ cho ID {uid}!"})
    else:
        ensure_local_files()
        with open(DEPOSITS_FILE, "r", encoding="utf-8") as f: deposits = json.load(f)
        target = None
        for d in deposits:
            if d.get("id") == dep_id:
                target = d
                break
        if not target or target.get("status") != "pending":
            return jsonify({"success": False, "message": "Không tìm thấy!"}), 400

        target["status"] = "approved"
        with open(DEPOSITS_FILE, "w", encoding="utf-8") as f: json.dump(deposits, f, indent=2)

        with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
        uid = target["userId"]
        if uid not in users: users[uid] = {"balance": 0}
        users[uid]["balance"] += target["amount"]
        with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(users, f, indent=2)

        return jsonify({"success": True, "message": f"Đã duyệt cộng {target['amount']:,}đ cho ID {uid}!"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
