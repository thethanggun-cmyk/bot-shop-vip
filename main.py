import telebot
from telebot import types
from flask import Flask
from threading import Thread
import os
from pymongo import MongoClient

# --- [CẤU HÌNH] ---
TOKEN = '8732552211:AAEpggeMdz51o5rREuIhtD22pfJPuJG30yQ'
ADMIN_ID = 7652160174
# THAY LINK MONGODB CỦA BẠN (Mật khẩu chỉ gồm chữ và số)
MONGO_URI = "mongodb+srv://user:pass@cluster.xxx.mongodb.net/?retryWrites=true&w=majority"

# Kết nối MongoDB
client = MongoClient(MONGO_URI)
db = client['CloneGunStore']
users_col = db['users']
stock_col = db['stock']

bot = telebot.TeleBot(TOKEN)
server = Flask('')

@server.route('/')
def home():
    return "Bot Railway đang chạy!"

def run_flask():
    # Railway sẽ dùng PORT 8080 bạn đã cài ở tab Variables
    port = int(os.environ.get("PORT", 8080))
    server.run(host='0.0.0.0', port=port)

# --- [HÀM LẤY DỮ LIỆU] ---
def get_user_data(user):
    uid = user.id
    uname = f"@{user.username}" if user.username else "Không có"
    data = users_col.find_one({"user_id": uid})
    if not data:
        new_u = {"user_id": uid, "username": uname, "balance": 0}
        users_col.insert_one(new_u)
        return new_u
    users_col.update_one({"user_id": uid}, {"$set": {"username": uname}})
    return data

# --- [GIAO DIỆN START] ---
@bot.message_handler(commands=['start'])
def start(message):
    u = get_user_data(message.from_user)
    mention = f"[{message.from_user.first_name}](tg://user?id={message.from_user.id})"
    text = (
        f"🔥 **CLONE GUN STORE VN**\n"
        f"👋 Chào mừng {mention}!\n\n"
        "📩 **Acc Lv5/Kc Giá Rẻ**\n"
        "💬 **Cskh** @guncheatvn\n\n"
        f"💰 **Số dư của bạn:** `{u['balance']:,}đ`"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 Mua Acc Lv5/Kc", "💳 Nạp Tiền")
    markup.add("👤 Thông Tin/Số Dư", "📦 Đơn Hàng")
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

# --- [LỆNH ADMIN] ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    u_count = users_col.count_documents({})
    c_lv5 = stock_col.count_documents({"type": "lv5"})
    c_kc = stock_col.count_documents({"type": "kc"})
    txt = (
        "📊 **ADMIN PANEL**\n\n"
        f"👤 Khách: `{u_count}`\n"
        f"📦 Kho Lv5: `{c_lv5}`\n"
        f"📦 Kho Kc: `{c_kc}`\n\n"
        "Lệnh: `/users`, `/add [loại] [acc1,acc2]`, `/setmoney [ID] [tiền]`"
    )
    bot.send_message(ADMIN_ID, txt, parse_mode="Markdown")

@bot.message_handler(commands=['users'])
def list_users(message):
    if message.from_user.id != ADMIN_ID: return
    all_u = users_col.find()
    txt = "📋 **DANH SÁCH KHÁCH:**\n"
    for i, u in enumerate(all_u, 1):
        txt += f"{i}. {u['username']} (ID: `{u['user_id']}`)\n"
    bot.send_message(ADMIN_ID, txt, parse_mode="Markdown")

@bot.message_handler(commands=['add'])
def add_stock(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, loai, items = message.text.split(' ', 2)
        danh_sach = items.split(',')
        added = 0
        for a in danh_sach:
            if a.strip():
                stock_col.insert_one({"type": loai.lower(), "content": a.strip()})
                added += 1
        bot.send_message(ADMIN_ID, f"✅ Đã nạp {added} acc vào kho {loai}!")
    except: bot.send_message(ADMIN_ID, "⚠️ Cú pháp: `/add lv5 acc1,acc2`")

@bot.message_handler(commands=['setmoney'])
def set_money(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, uid, amount = message.text.split(' ')
        users_col.update_one({"user_id": int(uid)}, {"$set": {"balance": int(amount)}}, upsert=True)
        bot.send_message(ADMIN_ID, f"✅ Đã cộng {amount}đ cho ID {uid}")
        bot.send_message(int(uid), f"🔔 Bạn đã được cộng {int(amount):,}đ vào tài khoản!")
    except: pass

# --- [XỬ LÝ TIN NHẮN] ---
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if message.text == "🛒 Mua Acc Lv5/Kc":
        c5 = stock_col.count_documents({"type":"lv5"})
        ck = stock_col.count_documents({"type":"kc"})
        txt = f"🔥 **MUA ACC**\n🛒 Lv5 (2k): {c5}\n🛒 Kc (30k): {ck}"
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("Mua Lv5 🛒", callback_data="b_lv5"), types.InlineKeyboardButton("Mua Kc 🛒", callback_data="b_kc"))
        bot.send_message(message.chat.id, txt, reply_markup=mk, parse_mode="Markdown")
    
    elif message.text == "💳 Nạp Tiền":
        msg = bot.send_message(message.chat.id, "💳 **Nhập số tiền muốn nạp (Ví dụ: 50000):**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_deposit)

    elif message.text == "👤 Thông Tin/Số Dư":
        u = get_user_data(message.from_user)
        bot.send_message(message.chat.id, f"👤: {message.from_user.first_name}\n🆔: `{u['user_id']}`\n💰: {u['balance']:,}đ", parse_mode="Markdown")

def process_deposit(m):
    try:
        bank_txt = f"🏦 **MB Bank**\nSTK: `12345678` (Tên bạn)\nND: `NAP {m.from_user.id}`\n\n*Chuyển xong nhấn xác nhận!*"
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ XÁC NHẬN", callback_data=f"dep_{m.text}"))
        bot.send_message(m.chat.id, bank_txt, reply_markup=markup, parse_mode="Markdown")
    except: pass

@bot.callback_query_handler(func=lambda call: True)
def cb_handler(call):
    if call.data.startswith("b_"):
        l = "lv5" if "lv5" in call.data else "kc"
        p = 2000 if l == "lv5" else 30000
        u = get_user_data(call.from_user)
        
        item = stock_col.find_one({"type": l})
        if not item:
            bot.answer_callback_query(call.id, "❌ Hết hàng!"); return
        if u['balance'] < p:
            bot.send_message(call.message.chat.id, "❌ Số dư không đủ!"); return

        stock_col.delete_one({"_id": item["_id"]})
        users_col.update_one({"user_id": call.from_user.id}, {"$inc": {"balance": -p}})
        bot.send_message(call.message.chat.id, f"✅ **THÀNH CÔNG!**\n🔑 Acc: `{item['content']}`", parse_mode="Markdown")
        
    elif call.data.startswith("dep_"):
        bot.send_message(ADMIN_ID, f"🔔 Khách báo nạp {call.data.split('_')[1]}đ. Duyệt: `/setmoney {call.from_user.id} {call.data.split('_')[1]}`")
        bot.edit_message_text("✅ Đã gửi yêu cầu nạp!", call.message.chat.id, call.message.message_id)

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    bot.infinity_polling()
