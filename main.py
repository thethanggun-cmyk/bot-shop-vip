import os
import json
import time
import threading
import sys
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__, static_folder=".")

# ===== LẤY TOKEN VÀ ADMIN ID =====
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
if not BOT_TOKEN:
    print("❌ LỖI: TELEGRAM_TOKEN chưa được set! Vui lòng thêm biến môi trường TELEGRAM_TOKEN.")
    sys.exit(1)  # Dừng app nếu không có token

ADMIN_ID = int(os.environ.get("ADMIN_ID", "8348411770"))

# Khởi tạo bot
try:
    bot = telebot.TeleBot(BOT_TOKEN)
    print("✅ Bot Telegram đã được khởi tạo thành công!")
except Exception as e:
    print("❌ Lỗi khởi tạo bot:", e)
    sys.exit(1)

# KẾT NỐI MONGODB ATLAS
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

ACC_FILE = "acclv5.txt"
ACC_FREE_FILE = "acclv5_free.txt"
USERS_FILE = "users.json"
DEPOSITS_FILE = "deposits.json"
PURCHASES_FILE = "purchases.json"

def ensure_local_files():
    if not os.path.exists(ACC_FILE): open(ACC_FILE, "w", encoding="utf-8").close()
    if not os.path.exists(ACC_FREE_FILE): open(ACC_FREE_FILE, "w", encoding="utf-8").close()
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump({}, f)
    if not os.path.exists(DEPOSITS_FILE):
        with open(DEPOSITS_FILE, "w", encoding="utf-8") as f: json.dump([], f)
    if not os.path.exists(PURCHASES_FILE):
        with open(PURCHASES_FILE, "w", encoding="utf-8") as f: json.dump([], f)

# ==================== BOT TELEGRAM & LỆNH ADMIN ====================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    print(f"📩 Nhận lệnh /start từ {message.from_user.id}")  # log
    user_id = str(message.chat.id)
    username = message.from_user.username or message.from_user.first_name or "User"

    if db is not None:
        db.users.update_one({"userId": user_id}, {"$set": {"username": username}}, upsert=True)
    else:
        ensure_local_files()
        with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
        if user_id not in users: users[user_id] = {"balance": 0, "coins": 0}
        users[user_id]["username"] = username
        with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(users, f, indent=2)

    args = message.text.split()
    ref_id = args[1] if len(args) > 1 else ""

    web_app_url = f"https://t.me/guncpwstore_bot/gunminiapp?startapp={ref_id}" if ref_id else "https://t.me/guncpwstore_bot/gunminiapp"

    markup = InlineKeyboardMarkup()
    btn = InlineKeyboardButton("🚀 Mở Mini App", url=web_app_url)
    markup.add(btn)
    
    welcome_text = "👋 Chào mừng bạn đến với **Gun Store**!\nBấm vào nút bên dưới để mở Mini App và trải nghiệm nhé!"
    bot.reply_to(message, welcome_text, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['coin'])
def set_coin(message):
    if message.from_user.id != ADMIN_ID:
        print(f"⚠️ User {message.from_user.id} cố gắng dùng lệnh /coin nhưng không phải admin")
        return
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "⚠️ Cú pháp: `/coin <@username_hoặc_ID> <số_coin>`", parse_mode="Markdown")
        return

    target = args[1].replace('@', '').strip()
    try:
        amount = int(args[2])
    except ValueError:
        bot.reply_to(message, "⚠️ Số coin phải là một số nguyên!")
        return

    if db is not None:
        user = db.users.find_one({"$or": [{"userId": target}, {"username": target}]})
        target_id = user["userId"] if user else target
        db.users.update_one({"userId": target_id}, {"$inc": {"coins": amount}}, upsert=True)
        bot.reply_to(message, f"✅ Đã thay đổi **{amount:+} Coin** cho User `{target_id}`!", parse_mode="Markdown")
    else:
        ensure_local_files()
        with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
        target_id = target
        for uid, udata in users.items():
            if udata.get("username") == target:
                target_id = uid
                break
        if target_id not in users: users[target_id] = {"balance": 0, "coins": 0}
        users[target_id]["coins"] = users[target_id].get("coins", 0) + amount
        with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(users, f, indent=2)
        bot.reply_to(message, f"✅ Đã thay đổi **{amount:+} Coin** cho User `{target_id}`!", parse_mode="Markdown")

@bot.message_handler(commands=['user'])
def list_users(message):
    if message.from_user.id != ADMIN_ID: return

    if db is not None:
        users_list = list(db.users.find({}, {"_id": 0}))
    else:
        ensure_local_files()
        with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
        users_list = [{"userId": k, **v} for k, v in users.items()]

    if not users_list:
        bot.reply_to(message, "📂 Chưa có người dùng nào trên hệ thống.")
        return

    msg = f"📊 **DANH SÁCH NGƯỜI DÙNG ({len(users_list)} Users)**:\n\n"
    for idx, u in enumerate(users_list, start=1):
        uname = f"@{u.get('username')}" if u.get('username') else "Không có"
        uid = u.get("userId", "N/A")
        bal = u.get("balance", 0)
        coins = u.get("coins", 0)
        msg += f"{idx}. **User**: {uname}\n   ├ **ID**: `{uid}`\n   ├ **Số dư**: {bal:,}đ\n   └ **Coin**: {coins} 🪙\n\n"

    if len(msg) > 4000:
        for chunk in [msg[i:i+4000] for i in range(0, len(msg), 4000)]:
            bot.send_message(message.chat.id, chunk, parse_mode="Markdown")
    else:
        bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(commands=['thongbao'])
def broadcast_message(message):
    if message.from_user.id != ADMIN_ID: return
    content = message.text.replace('/thongbao', '').strip()
    if not content:
        bot.reply_to(message, "⚠️ Cú pháp: `/thongbao <nội dung thông báo>`", parse_mode="Markdown")
        return

    users_list = []
    if db is not None:
        users_list = [u["userId"] for u in db.users.find({}, {"userId": 1})]
    else:
        ensure_local_files()
        with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
        users_list = list(users.keys())

    success_count = 0
    for uid in set(users_list):
        try:
            bot.send_message(uid, f"📢 **THÔNG BÁO TỪ ADMIN**\n\n{content}", parse_mode="Markdown")
            success_count += 1
            time.sleep(0.05)
        except Exception:
            pass

    bot.reply_to(message, f"✅ Đã gửi thông báo thành công tới {success_count} người dùng!")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Cú pháp: `/ban <ID_hoặc_@username>`", parse_mode="Markdown")
        return

    target = args[1].replace('@', '').strip()
    if db is not None:
        user = db.users.find_one({"$or": [{"userId": target}, {"username": target}]})
        target_id = user["userId"] if user else target
        db.users.update_one({"userId": target_id}, {"$set": {"is_banned": True}}, upsert=True)
        bot.reply_to(message, f"🚫 Đã cấm `{target_id}` đổi Acc Free Lv5!")
    else:
        ensure_local_files()
        with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
        users[target] = users.get(target, {})
        users[target]["is_banned"] = True
        with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(users, f, indent=2)
        bot.reply_to(message, f"🚫 Đã cấm `{target}` đổi Acc Free Lv5!")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Cú pháp: `/unban <ID_hoặc_@username>`", parse_mode="Markdown")
        return

    target = args[1].replace('@', '').strip()
    if db is not None:
        user = db.users.find_one({"$or": [{"userId": target}, {"username": target}]})
        target_id = user["userId"] if user else target
        db.users.update_one({"userId": target_id}, {"$set": {"is_banned": False}})
        bot.reply_to(message, f"✅ Đã gỡ cấm cho `{target_id}`!")
    else:
        ensure_local_files()
        with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
        if target in users: users[target]["is_banned"] = False
        with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(users, f, indent=2)
        bot.reply_to(message, f"✅ Đã gỡ cấm cho `{target}`!")

def run_bot():
    try:
        print("🤖 Bot Telegram đang lắng nghe tin nhắn...")
        # Sử dụng polling với skip_pending=True để bỏ qua tin nhắn cũ
        bot.infinity_polling(skip_pending=True, timeout=60)
    except Exception as e:
        print(f"❌ Lỗi Bot Telegram: {e}")
        # Nếu bot bị lỗi, thử khởi động lại sau 5 giây
        time.sleep(5)
        # Có thể gọi lại hàm này để thử lại, nhưng để đơn giản thì in ra và dừng
        # Bạn có thể thêm cơ chế restart nếu muốn

# Chạy bot trong luồng riêng
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

# ==================== ROUTE STATIC FILES ====================
@app.route("/")
def index():
    if os.path.exists("index.html"): return send_from_directory(".", "index.html")
    return "<h3>Lỗi: Không tìm thấy file index.html!</h3>", 404

@app.route("/music.mp3")
def serve_music():
    if os.path.exists("music.mp3"): return send_from_directory(".", "music.mp3")
    return "No music file found", 404

@app.route("/video.mp4")
def serve_video():
    if os.path.exists("video.mp4"): return send_from_directory(".", "video.mp4")
    return "No video file found", 404

# ==================== API USER & XỬ LÝ CỘNG COIN GIỚI THIỆU ====================
@app.route("/get-user-info", methods=["GET"])
def get_user_info():
    user_id = str(request.args.get("userId", ""))
    username = str(request.args.get("userName", ""))
    ref_by = str(request.args.get("refBy", ""))
    
    print(f"🔍 get-user-info: userId={user_id}, refBy={ref_by}")

    if not user_id: return jsonify({"success": False, "balance": 0, "coins": 0})
    
    if db is not None:
        user = db.users.find_one({"userId": user_id})
        if not user:
            db.users.insert_one({
                "userId": user_id, 
                "username": username,
                "balance": 0, 
                "coins": 0, 
                "referred_by": ref_by if (ref_by and ref_by != user_id) else "",
                "is_banned": False
            })
            
            if ref_by and ref_by != user_id:
                db.users.update_one({"userId": ref_by}, {"$inc": {"coins": 1}}, upsert=True)
                ref_user = db.users.find_one({"userId": ref_by}) or {}
                ref_tag = f"@{ref_user.get('username')}" if ref_user.get('username') else f"`{ref_by}`"
                new_user_tag = f"@{username}" if username else f"`{user_id}`"

                try:
                    bot.send_message(ref_by, "🎉 **XÁC NHẬN MỜI THÀNH CÔNG!**\n\nBạn vừa mời thành công 1 người dùng mới và nhận được **+1 Coin**!", parse_mode="Markdown")
                    bot.send_message(ADMIN_ID, f"🔔 **THÔNG BÁO MỜI THÀNH CÔNG**\nUser {ref_tag} đã mời thành công người dùng {new_user_tag} vào Mini App!", parse_mode="Markdown")
                except Exception as e:
                    print("Lỗi gửi tin nhắn thông báo:", e)

            return jsonify({"success": True, "balance": 0, "coins": 0})
        else:
            if username: db.users.update_one({"userId": user_id}, {"$set": {"username": username}})
            return jsonify({"success": True, "balance": user.get("balance", 0), "coins": user.get("coins", 0)})
    else:
        ensure_local_files()
        with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
        if user_id not in users:
            users[user_id] = {
                "username": username,
                "balance": 0, 
                "coins": 0, 
                "referred_by": ref_by if (ref_by and ref_by != user_id) else "",
                "is_banned": False
            }
            
            if ref_by and ref_by in users and ref_by != user_id:
                users[ref_by]["coins"] = users[ref_by].get("coins", 0) + 1
                ref_uname = users[ref_by].get("username")
                ref_tag = f"@{ref_uname}" if ref_uname else f"`{ref_by}`"
                new_user_tag = f"@{username}" if username else f"`{user_id}`"

                try:
                    bot.send_message(ref_by, "🎉 **XÁC NHẬN MỜI THÀNH CÔNG!**\n\nBạn vừa mời thành công 1 người dùng mới và nhận được **+1 Coin**!", parse_mode="Markdown")
                    bot.send_message(ADMIN_ID, f"🔔 **THÔNG BÁO MỜI THÀNH CÔNG**\nUser {ref_tag} đã mời thành công người dùng {new_user_tag} vào Mini App!", parse_mode="Markdown")
                except Exception as e:
                    print("Lỗi gửi tin nhắn thông báo:", e)

            with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(users, f, indent=2)
            
        return jsonify({
            "success": True, 
            "balance": users[user_id].get("balance", 0),
            "coins": users[user_id].get("coins", 0)
        })

# ==================== CÁC API CÒN LẠI (GIỮ NGUYÊN) ====================
# ... (giữ nguyên các route /get-stock, /acclv5, /buy-acc, /redeem-free-acc, /get-purchases, /request-deposit, /get-deposit-history, /admin/get-deposits, /admin/approve-deposit, /is-admin)

# LƯU Ý: PHẦN API TỪ /get-stock ĐẾN /is-admin VẪN GIỮ NGUYÊN NHƯ BẢN CŨ (KHÔNG THAY ĐỔI)

# ==================== API KIỂM TRA ADMIN ====================
@app.route("/is-admin", methods=["GET"])
def is_admin():
    user_id = request.args.get("userId", "")
    return jsonify({"isAdmin": str(user_id) == str(ADMIN_ID)})

# ==================== CHẠY APP ====================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
