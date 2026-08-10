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

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
if not BOT_TOKEN:
    print("❌ LỖI: TELEGRAM_TOKEN chưa được set! Vui lòng thêm biến môi trường TELEGRAM_TOKEN.")
    sys.exit(1)

ADMIN_ID = int(os.environ.get("ADMIN_ID", "8348411770"))

try:
    bot = telebot.TeleBot(BOT_TOKEN)
    print("✅ Bot Telegram đã được khởi tạo thành công!")
except Exception as e:
    print("❌ Lỗi khởi tạo bot:", e)
    sys.exit(1)

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
    print(f"📩 Nhận lệnh /start từ {message.from_user.id}")
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
    if message.from_user.id != ADMIN_ID: return
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
        bot.infinity_polling(skip_pending=True, timeout=60)
    except Exception as e:
        print(f"❌ Lỗi Bot Telegram: {e}")
        time.sleep(5)

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
                "is_banned": False,
                "confirmed_invite": False
            })
            return jsonify({"success": True, "balance": 0, "coins": 0, "confirmed_invite": False})
        else:
            if username: db.users.update_one({"userId": user_id}, {"$set": {"username": username}})
            return jsonify({
                "success": True, 
                "balance": user.get("balance", 0), 
                "coins": user.get("coins", 0),
                "confirmed_invite": user.get("confirmed_invite", False)
            })
    else:
        ensure_local_files()
        with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
        if user_id not in users:
            users[user_id] = {
                "username": username,
                "balance": 0, 
                "coins": 0, 
                "referred_by": ref_by if (ref_by and ref_by != user_id) else "",
                "is_banned": False,
                "confirmed_invite": False
            }
            with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(users, f, indent=2)
            
        return jsonify({
            "success": True, 
            "balance": users[user_id].get("balance", 0),
            "coins": users[user_id].get("coins", 0),
            "confirmed_invite": users[user_id].get("confirmed_invite", False)
        })

@app.route("/confirm-invite", methods=["POST"])
def confirm_invite():
    data = request.json or {}
    user_id = str(data.get("userId", ""))
    ref_by = str(data.get("refBy", ""))
    
    if not user_id or not ref_by or ref_by == user_id:
        return jsonify({"success": False, "message": "Dữ liệu không hợp lệ!"}), 400
    
    if db is not None:
        user = db.users.find_one({"userId": user_id})
        if not user:
            return jsonify({"success": False, "message": "Không tìm thấy người dùng!"}), 400
        if user.get("confirmed_invite", False):
            return jsonify({"success": False, "message": "Bạn đã xác nhận mời trước đó rồi!"}), 400
        
        # Cộng coin cho người mời
        db.users.update_one({"userId": ref_by}, {"$inc": {"coins": 1}}, upsert=True)
        # Đánh dấu đã xác nhận cho người được mời
        db.users.update_one({"userId": user_id}, {"$set": {"confirmed_invite": True}})
        
        # Lấy thông tin người mời và người được mời
        ref_user = db.users.find_one({"userId": ref_by}) or {}
        new_user = db.users.find_one({"userId": user_id}) or {}
        
        ref_username = ref_user.get("username", ref_by)
        new_username = new_user.get("username", user_id)
        
        # Gửi tin nhắn cho người mời
        try:
            bot.send_message(
                ref_by, 
                f"🎉 **XÁC NHẬN MỜI THÀNH CÔNG!**\n\nBạn đã mời thành công @{new_username} (ID: `{user_id}`).\nBạn đã được cộng **+1 Coin**!",
                parse_mode="Markdown"
            )
        except Exception as e:
            print("Lỗi gửi tin nhắn cho người mời:", e)
        
        # Gửi tin nhắn cho admin
        try:
            bot.send_message(
                ADMIN_ID,
                f"🔔 **THÔNG BÁO MỜI THÀNH CÔNG**\nUser @{ref_username} (ID: `{ref_by}`) đã mời thành công user @{new_username} (ID: `{user_id}`) vào Mini App (đã xác nhận qua câu đố)!",
                parse_mode="Markdown"
            )
        except Exception as e:
            print("Lỗi gửi tin nhắn cho admin:", e)
        
        return jsonify({"success": True, "message": "Cảm ơn bạn đã xác nhận! Người giới thiệu đã nhận được 1 Coin."})
    
    else:
        # Fallback local files
        ensure_local_files()
        with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
        if user_id not in users:
            return jsonify({"success": False, "message": "Không tìm thấy người dùng!"}), 400
        if users[user_id].get("confirmed_invite", False):
            return jsonify({"success": False, "message": "Bạn đã xác nhận mời trước đó rồi!"}), 400
        
        if ref_by in users:
            users[ref_by]["coins"] = users[ref_by].get("coins", 0) + 1
        else:
            users[ref_by] = {"balance": 0, "coins": 1}
        users[user_id]["confirmed_invite"] = True
        
        with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(users, f, indent=2)
        
        ref_username = users[ref_by].get("username", ref_by)
        new_username = users[user_id].get("username", user_id)
        
        try:
            bot.send_message(
                ref_by,
                f"🎉 **XÁC NHẬN MỜI THÀNH CÔNG!**\n\nBạn đã mời thành công @{new_username} (ID: `{user_id}`).\nBạn đã được cộng **+1 Coin**!",
                parse_mode="Markdown"
            )
        except Exception as e:
            print("Lỗi gửi tin nhắn cho người mời:", e)
        
        try:
            bot.send_message(
                ADMIN_ID,
                f"🔔 **THÔNG BÁO MỜI THÀNH CÔNG**\nUser @{ref_username} (ID: `{ref_by}`) đã mời thành công user @{new_username} (ID: `{user_id}`) vào Mini App (đã xác nhận qua câu đố)!",
                parse_mode="Markdown"
            )
        except Exception as e:
            print("Lỗi gửi tin nhắn cho admin:", e)
        
        return jsonify({"success": True, "message": "Cảm ơn bạn đã xác nhận! Người giới thiệu đã nhận được 1 Coin."})

# ==================== CÁC API KHÁC (giữ nguyên) ====================
@app.route("/get-stock", methods=["GET"])
def get_stock():
    acc_type = request.args.get("type", "vip")
    col_name = "accounts_free" if acc_type == "free" else "accounts"
    
    if db is not None:
        count = db[col_name].count_documents({})
        return jsonify({"success": True, "stock": count})
    else:
        ensure_local_files()
        file_path = ACC_FREE_FILE if acc_type == "free" else ACC_FILE
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        return jsonify({"success": True, "stock": len(lines)})

@app.route("/acclv5", methods=["POST"])
def add_acc():
    data = request.json or {}
    accounts = data.get("accounts", [])
    acc_type = data.get("type", "vip")
    
    if not accounts: return jsonify({"success": False, "message": "Không có acc"}), 400
    
    clean_accs = [str(a).strip() for a in accounts if str(a).strip()]
    col_name = "accounts_free" if acc_type == "free" else "accounts"
    file_path = ACC_FREE_FILE if acc_type == "free" else ACC_FILE

    if db is not None:
        docs = [{"acc": a} for a in clean_accs]
        if docs: db[col_name].insert_many(docs)
        total = db[col_name].count_documents({})
        return jsonify({"success": True, "added_count": len(clean_accs), "new_stock": total})
    else:
        ensure_local_files()
        with open(file_path, "a", encoding="utf-8") as f:
            for a in clean_accs: f.write(a + "\n")
        with open(file_path, "r", encoding="utf-8") as f:
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
            "time": time_str,
            "type": "vip"
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

        with open(PURCHASES_FILE, "r", encoding="utf-8") as f: purchases = json.load(f)
        time_str = time.strftime("%H:%M - %d/%m/%Y")
        purchases.insert(0, {"userId": user_id, "accs": "\n".join(bought_accs), "count": len(bought_accs), "time": time_str, "type": "vip"})
        with open(PURCHASES_FILE, "w", encoding="utf-8") as f: json.dump(purchases, f, indent=2)

        return jsonify({"success": True, "accounts": bought_accs, "new_balance": users[user_id]["balance"]})

@app.route("/redeem-free-acc", methods=["POST"])
def redeem_free_acc():
    data = request.json or {}
    user_id = str(data.get("userId", ""))
    qty = int(data.get("quantity", 1))
    cost_per_acc = 5
    total_coins_needed = qty * cost_per_acc

    today_str = datetime.now().strftime("%d/%m/%Y")

    if db is not None:
        user = db.users.find_one({"userId": user_id}) or {}
        
        if user.get("is_banned", False):
            return jsonify({"success": False, "message": "🚫 Tài khoản của bạn đã bị cấm đổi Acc Free Lv5!"}), 403

        today_redeemed = db.purchases.find({
            "userId": user_id,
            "type": "free",
            "date": today_str
        })
        already_redeemed_count = sum([p.get("count", 1) for p in today_redeemed])

        if already_redeemed_count + qty > 3:
            remains = max(0, 3 - already_redeemed_count)
            return jsonify({
                "success": False, 
                "message": f"⚠️ Mỗi tài khoản chỉ được đổi tối đa 3 Acc Free / ngày!\nHôm nay bạn đã đổi {already_redeemed_count}/3 acc (Còn lại: {remains} acc)."
            }), 400

        user_coins = user.get("coins", 0)

        if user_coins < total_coins_needed:
            return jsonify({"success": False, "message": f"Bạn không đủ Coin! Cần {total_coins_needed} Coin (Hiện có: {user_coins} Coin)."}), 400

        acc_docs = list(db.accounts_free.find().limit(qty))
        if len(acc_docs) < qty:
            return jsonify({"success": False, "message": f"Kho Acc Free chỉ còn {len(acc_docs)} acc."}), 400

        bought_accs = [doc["acc"] for doc in acc_docs]
        ids_to_delete = [doc["_id"] for doc in acc_docs]
        db.accounts_free.delete_many({"_id": {"$in": ids_to_delete}})

        new_coins = user_coins - total_coins_needed
        db.users.update_one({"userId": user_id}, {"$set": {"coins": new_coins}})

        time_str = time.strftime("%H:%M - %d/%m/%Y")
        db.purchases.insert_one({
            "userId": user_id,
            "accs": "\n".join(bought_accs),
            "count": len(bought_accs),
            "time": time_str + " (Đổi bằng Coin)",
            "type": "free",
            "date": today_str
        })

        return jsonify({"success": True, "accounts": bought_accs, "new_coins": new_coins})
    else:
        ensure_local_files()
        with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
        u = users.get(user_id, {})
        
        if u.get("is_banned", False):
            return jsonify({"success": False, "message": "🚫 Tài khoản của bạn đã bị cấm đổi Acc Free Lv5!"}), 403

        with open(PURCHASES_FILE, "r", encoding="utf-8") as f: purchases = json.load(f)
        already_redeemed_count = sum([
            p.get("count", 1) for p in purchases 
            if p.get("userId") == user_id and p.get("type") == "free" and p.get("date") == today_str
        ])

        if already_redeemed_count + qty > 3:
            remains = max(0, 3 - already_redeemed_count)
            return jsonify({
                "success": False, 
                "message": f"⚠️ Mỗi tài khoản chỉ được đổi tối đa 3 Acc Free / ngày!\nHôm nay bạn đã đổi {already_redeemed_count}/3 acc (Còn lại: {remains} acc)."
            }), 400

        user_coins = u.get("coins", 0)

        if user_coins < total_coins_needed:
            return jsonify({"success": False, "message": f"Không đủ Coin! Cần {total_coins_needed} Coin (Hiện có: {user_coins} Coin)."}), 400

        with open(ACC_FREE_FILE, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        if len(lines) < qty:
            return jsonify({"success": False, "message": f"Kho chỉ còn {len(lines)} acc."}), 400

        bought_accs = [lines.pop(0) for _ in range(qty)]

        with open(ACC_FREE_FILE, "w", encoding="utf-8") as f:
            for l in lines: f.write(l + "\n")

        users[user_id]["coins"] -= total_coins_needed
        with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(users, f, indent=2)

        time_str = time.strftime("%H:%M - %d/%m/%Y")
        purchases.insert(0, {
            "userId": user_id, 
            "accs": "\n".join(bought_accs), 
            "count": len(bought_accs), 
            "time": time_str + " (Đổi bằng Coin)",
            "type": "free",
            "date": today_str
        })
        with open(PURCHASES_FILE, "w", encoding="utf-8") as f: json.dump(purchases, f, indent=2)

        return jsonify({"success": True, "accounts": bought_accs, "new_coins": users[user_id]["coins"]})

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

    now = time.time()
    twenty_mins_ago = now - 1200

    if db is not None:
        recent_count = db.deposits.count_documents({
            "userId": user_id,
            "timestamp": {"$gte": twenty_mins_ago}
        })

        if recent_count >= 5:
            return jsonify({
                "success": False, 
                "message": "⚠️ Bạn đã tạo quá 5 lệnh nạp trong 20 phút! Vui lòng chờ hết thời gian để tạo lại."
            }), 400

        dep_obj = {
            "id": int(now * 1000),
            "userId": user_id,
            "userName": user_name,
            "amount": amount,
            "status": "pending",
            "time": time.strftime("%H:%M - %d/%m/%Y"),
            "timestamp": now
        }
        db.deposits.insert_one(dep_obj)
        return jsonify({"success": True, "message": "Đã gửi yêu cầu nạp tiền!"})
    else:
        ensure_local_files()
        with open(DEPOSITS_FILE, "r", encoding="utf-8") as f: deposits = json.load(f)
        recent_count = len([d for d in deposits if str(d.get("userId")) == user_id and d.get("timestamp", 0) >= twenty_mins_ago])
        
        if recent_count >= 5:
            return jsonify({
                "success": False,
                "message": "⚠️ Bạn đã tạo quá 5 lệnh nạp trong 20 phút! Vui lòng chờ thêm."
            }), 400

        dep_obj = {
            "id": int(now * 1000),
            "userId": user_id,
            "userName": user_name,
            "amount": amount,
            "status": "pending",
            "time": time.strftime("%H:%M - %d/%m/%Y"),
            "timestamp": now
        }
        deposits.insert(0, dep_obj)
        with open(DEPOSITS_FILE, "w", encoding="utf-8") as f: json.dump(deposits, f, indent=2)
        return jsonify({"success": True, "message": "Đã gửi yêu cầu nạp tiền!"})

@app.route("/get-deposit-history", methods=["GET"])
def get_deposit_history():
    user_id = str(request.args.get("userId", ""))
    twenty_mins_ago = time.time() - 1200

    if db is not None:
        query = {
            "userId": user_id,
            "$or": [
                {"status": "approved"},
                {"status": "pending", "timestamp": {"$gte": twenty_mins_ago}}
            ]
        }
        items = list(db.deposits.find(query, {"_id": 0}).sort("timestamp", -1))
        return jsonify({"success": True, "deposits": items})
    else:
        ensure_local_files()
        with open(DEPOSITS_FILE, "r", encoding="utf-8") as f: deposits = json.load(f)
        filtered = [
            d for d in deposits 
            if str(d.get("userId")) == user_id and (d.get("status") == "approved" or (d.get("status") == "pending" and d.get("timestamp", 0) >= twenty_mins_ago))
        ]
        return jsonify({"success": True, "deposits": filtered})

@app.route("/admin/get-deposits", methods=["GET"])
def admin_get_deposits():
    if db is not None:
        items = list(db.deposits.find({"status": "pending"}, {"_id": 0}).sort("timestamp", -1))
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

@app.route("/is-admin", methods=["GET"])
def is_admin():
    user_id = request.args.get("userId", "")
    return jsonify({"isAdmin": str(user_id) == str(ADMIN_ID)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
