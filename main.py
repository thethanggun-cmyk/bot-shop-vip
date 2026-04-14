import telebot
from telebot import types
from flask import Flask
from threading import Thread
import os
from pymongo import MongoClient

# --- [CẤU HÌNH HỆ THỐNG] ---
TOKEN = '8732552211:AAEpggeMdz51o5rREuIhtD22pfJPuJG30yQ'
ADMIN_ID = 7652160174
# THAY LINK MONGODB CỦA BẠN VÀO ĐÂY
MONGO_URI = "mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority"

# Kết nối Database
client = MongoClient(MONGO_URI)
db = client['CloneGunStore']
users_col = db['users']   # Lưu: user_id, username, balance
stock_col = db['stock']   # Lưu: type, content

bot = telebot.TeleBot(TOKEN)
app = Flask('')

@app.route('/')
def home(): return "Bot is Online!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- [HÀM HỖ TRỢ NGƯỜI DÙNG] ---
def get_user_data(user):
    user_id = user.id
    username = f"@{user.username}" if user.username else "Không có"
    data = users_col.find_one({"user_id": user_id})
    if not data:
        new_user = {"user_id": user_id, "username": username, "balance": 0}
        users_col.insert_one(new_user)
        return new_user
    else:
        # Cập nhật username mới nhất nếu khách có thay đổi
        users_col.update_one({"user_id": user_id}, {"$set": {"username": username}})
        return data

# --- [MENU CHÍNH] ---
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 Mua Acc Lv5/Kc", "💳 Nạp Tiền")
    markup.add("👤 Thông Tin/Số Dư", "📦 Đơn Hàng")
    return markup

# --- [XỬ LÝ LỆNH /START] ---
@bot.message_handler(commands=['start'])
def start(message):
    user_data = get_user_data(message.from_user)
    user_name = message.from_user.first_name
    user_mention = f"[{user_name}](tg://user?id={message.from_user.id})"
    
    text = (
        f"🔥 **CLONE GUN STORE VN**\n"
        f"👋 Chào mừng {user_mention} đã quay trở lại!\n\n"
        "📩 **Acc Lv5/Kc Giá Rẻ**\n"
        "💬 **Cskh** @guncheatvn\n\n"
        "🌐 **Bot** : @clonegunstorevn_bot **Uytin Tự Động Auto 24/7** 🛍️\n"
        f"💰 **Số dư của bạn:** `{user_data['balance']:,}đ`"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard(), parse_mode="Markdown")

# --- [QUẢN LÝ ADMIN] ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    total_u = users_col.count_documents({})
    c_lv5 = stock_col.count_documents({"type": "lv5"})
    c_kc = stock_col.count_documents({"type": "kc"})
    txt = (
        "📊 **BẢNG ĐIỀU KHIỂN ADMIN**\n\n"
        f"👤 Tổng khách: `{total_u}`\n"
        f"📦 Kho Lv5: `{c_lv5}`\n"
        f"📦 Kho Kc: `{c_kc}`\n\n"
        "Sử dụng: `/users`, `/add [loại] [acc1,acc2]`, `/setmoney [ID] [tiền]`"
    )
    bot.send_message(ADMIN_ID, txt, parse_mode="Markdown")

@bot.message_handler(commands=['users'])
def list_users(message):
    if message.from_user.id != ADMIN_ID: return
    all_u = users_col.find()
    txt = "📋 **DANH SÁCH KHÁCH HÀNG:**\n"
    for i, u in enumerate(all_u, 1):
        txt += f"{i}. {u['username']} (ID: `{u['user_id']}`)\n"
    bot.send_message(ADMIN_ID, txt, parse_mode="Markdown")

@bot.message_handler(commands=['add'])
def add_to_stock(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, loai, items = message.text.split(' ', 2)
        danh_sach = items.split(',')
        added = 0
        for acc in danh_sach:
            if acc.strip():
                stock_col.insert_one({"type": loai.lower(), "content": acc.strip()})
                added += 1
        bot.send_message(ADMIN_ID, f"✅ Đã nạp {added} acc {loai}. Tổng kho: {stock_col.count_documents({'type': loai.lower()})}")
    except:
        bot.send_message(ADMIN_ID, "⚠️ Cú pháp: `/add lv5 acc1,acc2`")

@bot.message_handler(commands=['setmoney'])
def set_money(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, uid, amount = message.text.split(' ')
        users_col.update_one({"user_id": int(uid)}, {"$set": {"balance": int(amount)}}, upsert=True)
        bot.send_message(ADMIN_ID, f"✅ Đã đặt số dư {amount}đ cho ID {uid}")
        bot.send_message(int(uid), f"🔔 Tài khoản bạn đã được cộng {int(amount):,}đ!")
    except: pass

# --- [XỬ LÝ TIN NHẮN VÀ MUA HÀNG] ---
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if message.text == "🛒 Mua Acc Lv5/Kc":
        c_lv5 = stock_col.count_documents({"type": "lv5"})
        c_kc = stock_col.count_documents({"type": "kc"})
        buy_text = (
            "🔥 **CLONE GUN STORE VN**\n"
            f"🛒 **Lv5 2k/1acc** (Còn: {c_lv5})\n"
            f"🛒 **Kc 30k/1acc** (Còn: {c_kc})\n\n"
            "**Auto 100% Uytin Số 1 🛍️**"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Mua Acc Lv5 🛒", callback_data="buy_lv5"))
        markup.add(types.InlineKeyboardButton("Mua Acc Kc 🛒", callback_data="buy_kc"))
        bot.send_message(message.chat.id, buy_text, reply_markup=markup, parse_mode="Markdown")
    
    elif message.text == "💳 Nạp Tiền":
        msg = bot.send_message(message.chat.id, "💳 **Nhập số tiền muốn nạp (Ví dụ: 50000):**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_deposit)

    elif message.text == "👤 Thông Tin/Số Dư":
        u = get_user_data(message.from_user)
        bot.send_message(message.chat.id, f"👤 **Tên:** {message.from_user.first_name}\n🆔 **ID:** `{u['user_id']}`\n💰 **Số dư:** `{u['balance']:,}đ`", parse_mode="Markdown")

def process_deposit(message):
    try:
        amount = int(message.text)
        bank_txt = f"🏦 **THÔNG TIN NẠP TIỀN**\n\n💰 Tiền: **{amount:,}đ**\n🏛 Bank: **MBV BANK**\n💳 STK: `04312345`\n📝 Nội dung: `NAP {message.from_user.id}`\n\n*Chuyển xong nhấn nút dưới!*"
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ ĐÃ NẠP XONG", callback_data=f"confirm_{amount}"))
        bot.send_message(message.chat.id, bank_txt, reply_markup=markup, parse_mode="Markdown")
    except: bot.send_message(message.chat.id, "❌ Nhập số tiền sai!")

@bot.callback_query_handler(func=lambda call: True)
def callback_handle(call):
    if call.data.startswith("buy_"):
        loai = "lv5" if "lv5" in call.data else "kc"
        price = 2000 if loai == "lv5" else 30000
        u = get_user_data(call.from_user)
        
        item = stock_col.find_one({"type": loai})
        if not item:
            bot.answer_callback_query(call.id, "❌ Hết hàng!")
            return
        if u['balance'] < price:
            bot.send_message(call.message.chat.id, "❌ **Số dư không đủ!** Vui lòng nạp tiền.")
            return

        stock_col.delete_one({"_id": item["_id"]})
        users_col.update_one({"user_id": call.from_user.id}, {"$inc": {"balance": -price}})
        bot.send_message(call.message.chat.id, f"✅ **MUA THÀNH CÔNG!**\n📦 Loại: {loai.upper()}\n🔑 Acc: `{item['content']}`", parse_mode="Markdown")
        bot.send_message(ADMIN_ID, f"🛒 Khách {call.from_user.first_name} vừa mua 1 acc {loai}")

    elif call.data.startswith("confirm_"):
        amount = call.data.split("_")[1]
        bot.send_message(ADMIN_ID, f"🔔 **KHÁCH BÁO NẠP:**\nID: `{call.from_user.id}`\nTiền: {amount}đ\nDuyệt: `/setmoney {call.from_user.id} {amount}`")
        bot.edit_message_text("✅ Đã gửi yêu cầu cho Admin!", call.message.chat.id, call.message.message_id)

if __name__ == "__main__":
    t = Thread(target=run)
    t.start()
    bot.infinity_polling()
