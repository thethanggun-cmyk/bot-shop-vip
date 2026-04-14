import telebot
from telebot import types
from flask import Flask
from threading import Thread
import os
from pymongo import MongoClient

# --- [CẤU HÌNH] ---
TOKEN = '8732552211:AAEpggeMdz51o5rREuIhtD22pfJPuJG30yQ'
ADMIN_ID = 7652160174
# THAY LINK MONGODB THẬT CỦA BẠN VÀO ĐÂY
MONGO_URI = "mongodb+srv://user:pass@cluster.xxx.mongodb.net/?retryWrites=true&w=majority"

try:
    client = MongoClient(MONGO_URI)
    db = client['CloneGunStore']
    users_col = db['users']
    stock_col = db['stock']
except Exception as e:
    print(f"Lỗi kết nối DB: {e}")

bot = telebot.TeleBot(TOKEN)
app = Flask('')

@app.route('/')
def home(): return "Bot is Online!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

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

@bot.message_handler(commands=['start'])
def start(message):
    u = get_user_data(message.from_user)
    mention = f"[{message.from_user.first_name}](tg://user?id={message.from_user.id})"
    text = (
        f"🔥 **CLONE GUN STORE VN**\n👋 Chào {mention}!\n\n"
        "📩 **Acc Lv5/Kc Giá Rẻ**\n💬 **Cskh** @guncheatvn\n"
        "🌐 **Bot** : @clonegunstorevn_bot **Auto 24/7** 🛍️\n"
        f"💰 **Số dư:** `{u['balance']:,}đ`"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 Mua Acc Lv5/Kc", "💳 Nạp Tiền")
    markup.add("👤 Thông Tin/Số Dư", "📦 Đơn Hàng")
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['admin'])
def admin(message):
    if message.from_user.id != ADMIN_ID: return
    u_count = users_col.count_documents({})
    bot.send_message(ADMIN_ID, f"📊 **ADMIN PANEL**\n👤 Khách: {u_count}\n📦 Dùng `/add lv5 acc1,acc2` hoặc `/setmoney ID tiền`", parse_mode="Markdown")

@bot.message_handler(commands=['users'])
def users(message):
    if message.from_user.id != ADMIN_ID: return
    all_u = users_col.find()
    txt = "📋 **DANH SÁCH KHÁCH:**\n"
    for i, u in enumerate(all_u, 1):
        txt += f"{i}. {u['username']} (`{u['user_id']}`)\n"
    bot.send_message(ADMIN_ID, txt, parse_mode="Markdown")

@bot.message_handler(commands=['add'])
def add(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, loai, items = message.text.split(' ', 2)
        danh_sach = items.split(',')
        for a in danh_sach:
            if a.strip(): stock_col.insert_one({"type": loai.lower(), "content": a.strip()})
        bot.send_message(ADMIN_ID, f"✅ Đã nạp xong vào kho {loai}!")
    except: bot.send_message(ADMIN_ID, "Sai cú pháp!")

@bot.message_handler(commands=['setmoney'])
def setmoney(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, uid, money = message.text.split(' ')
        users_col.update_one({"user_id": int(uid)}, {"$set": {"balance": int(money)}}, upsert=True)
        bot.send_message(ADMIN_ID, f"✅ Đã nạp {money} cho {uid}")
        bot.send_message(int(uid), f"🔔 Bạn đã được cộng {int(money):,}đ!")
    except: pass

@bot.message_handler(func=lambda m: True)
def handle(m):
    if m.text == "🛒 Mua Acc Lv5/Kc":
        c5, ck = stock_col.count_documents({"type":"lv5"}), stock_col.count_documents({"type":"kc"})
        txt = f"🔥 **MUA ACC**\n🛒 Lv5 (2k): {c5}\n🛒 Kc (30k): {ck}"
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("Mua Lv5", callback_data="b_lv5"), types.InlineKeyboardButton("Mua Kc", callback_data="b_kc"))
        bot.send_message(m.chat.id, txt, reply_markup=mk, parse_mode="Markdown")
    elif m.text == "💳 Nạp Tiền":
        bot.send_message(m.chat.id, "💳 Nhập số tiền muốn nạp:")
        bot.register_next_step_handler(m, lambda ms: bot.send_message(ms.chat.id, f"🏛 MB Bank\nSTK: `12345678` (Tên bạn)\nND: `NAP {ms.from_user.id}`", 
            reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("XÁC NHẬN", callback_data=f"dep_{ms.text}")), parse_mode="Markdown"))
    elif m.text == "👤 Thông Tin/Số Dư":
        u = get_user_data(m.from_user)
        bot.send_message(m.chat.id, f"👤: {m.from_user.first_name}\n🆔: `{u['user_id']}`\n💰: {u['balance']:,}đ", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    if c.data.startswith("b_"):
        l = "lv5" if "lv5" in c.data else "kc"
        p = 2000 if l == "lv5" else 30000
        u = get_user_data(c.from_user)
        item = stock_col.find_one({"type": l})
        if not item: bot.answer_callback_query(c.id, "Hết hàng!"); return
        if u['balance'] < p: bot.send_message(c.message.chat.id, "❌ Không đủ tiền!"); return
        stock_col.delete_one({"_id": item["_id"]})
        users_col.update_one({"user_id": c.from_user.id}, {"$inc": {"balance": -p}})
        bot.send_message(c.message.chat.id, f"✅ **THÀNH CÔNG!**\n🔑 Acc: `{item['content']}`", parse_mode="Markdown")
    elif c.data.startswith("dep_"):
        bot.send_message(ADMIN_ID, f"🔔 Khách báo nạp {c.data.split('_')[1]}đ. Duyệt: `/setmoney {c.from_user.id} {c.data.split('_')[1]}`")
        bot.edit_message_text("✅ Đã gửi yêu cầu!", c.message.chat.id, c.message.message_id)

if __name__ == "__main__":
    Thread(target=run).start()
    bot.infinity_polling()
