import telebot
from telebot import types
from flask import Flask
from threading import Thread
import os

# --- [CẤU HÌNH] ---
TOKEN = '8732552211:AAEpggeMdz51o5rREuIhtD22pfJPuJG30yQ'
ADMIN_ID = 7652160174

KHO_ACC = {"lv5": [], "kc": []}
VI_TIEN = {}

bot = telebot.TeleBot(TOKEN)
server = Flask('')

@server.route('/')
def home(): return "Bot Live"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    server.run(host='0.0.0.0', port=port)

# --- [GIAO DIỆN START] ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in VI_TIEN: VI_TIEN[uid] = 0
    
    text = (
        "🔥 CLONE GUN STORE VN\n"
        "📩 Acc Lv5/Kc Giá Rẻ\n"
        "💬 Cskh @guncheatvn\n"
        "🌐 Bot Uytin Tự Động Auto 24/7🛍️"
    )
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 Mua Acc", "👤 Thông Tin")
    markup.add("💳 Nạp Tiền")
    bot.send_message(message.chat.id, text, reply_markup=markup)

# --- [MUA BÁN] ---
@bot.message_handler(func=lambda m: m.text == "🛒 Mua Acc")
def shop(m):
    text = (
        "🔥 CLONE GUN STORE VN\n"
        f"🛒 Lv5 2k/1acc (Còn: {len(KHO_ACC['lv5'])})\n"
        f"🛒 Kc 30k/1acc (Còn: {len(KHO_ACC['kc'])})\n"
        "Auto 100% Uytin Số 1 🛍️"
    )
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("Mua Lv5 🛒", callback_data="buy_lv5"),
           types.InlineKeyboardButton("Mua Kc 🛒", callback_data="buy_kc"))
    bot.send_message(m.chat.id, text, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def ask_qty(c):
    loai = c.data.split("_")[1]
    msg = bot.send_message(c.message.chat.id, f"🔢 Nhập số lượng {loai.upper()} muốn mua:")
    bot.register_next_step_handler(msg, lambda m: finish_buy(m, loai))

def finish_buy(m, loai):
    try:
        qty = int(m.text)
        uid = m.from_user.id
        gia = 2000 if loai == "lv5" else 30000
        if VI_TIEN.get(uid, 0) < qty * gia:
            bot.send_message(m.chat.id, "❌ Không đủ tiền!"); return
        if len(KHO_ACC[loai]) < qty:
            bot.send_message(m.chat.id, "❌ Kho không đủ!"); return
            
        accs = [KHO_ACC[loai].pop(0) for _ in range(qty)]
        VI_TIEN[uid] -= qty * gia
        bot.send_message(m.chat.id, f"✅ Thành công!\n🔑 Acc:\n" + "\n".join(accs))
    except: bot.send_message(m.chat.id, "❌ Lỗi nhập liệu.")

# --- [NẠP TIỀN & DUYỆT] ---
@bot.message_handler(func=lambda m: m.text == "💳 Nạp Tiền")
def request_deposit(message):
    msg = bot.send_message(message.chat.id, "💰 Nhập số tiền bạn muốn nạp:")
    bot.register_next_step_handler(msg, process_deposit_step)

def process_deposit_step(message):
    try:
        amount = int(message.text)
        uid = message.from_user.id
        txt = f"🏦 MB BANK\n💳 STK: 12345678\n💰 Tiền: {amount:,}đ\n📝 Nội dung: NAP {uid}"
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("✅ XÁC NHẬN ĐÃ CHUYỂN", callback_data=f"conf_{uid}_{amount}"))
        bot.send_message(message.chat.id, txt, reply_markup=mk)
    except: bot.send_message(message.chat.id, "❌ Nhập số tiền hợp lệ.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("conf_"))
def customer_confirm(c):
    _, uid, amt = c.data.split("_")
    bot.edit_message_text("✅ Đã gửi yêu cầu! Chờ admin duyệt.", c.message.chat.id, c.message.message_id)
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("✅ Duyệt", callback_data=f"ok_{uid}_{amt}"),
           types.InlineKeyboardButton("❌ Hủy", callback_data=f"no_{uid}"))
    bot.send_message(ADMIN_ID, f"🔔 DUYỆT NẠP\nID: {uid}\nTiền: {amt}đ", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith(("ok_", "no_")))
def admin_action(c):
    data = c.data.split("_")
    uid = int(data[1])
    if data[0] == "ok":
        amt = int(data[2])
        VI_TIEN[uid] = VI_TIEN.get(uid, 0) + amt
        bot.edit_message_text(f"✅ Đã duyệt {amt}đ cho {uid}", c.message.chat.id, c.message.message_id)
        bot.send_message(uid, f"🔔 Nạp thành công {amt:,}đ!")
    else:
        bot.edit_message_text(f"❌ Từ chối ID {uid}", c.message.chat.id, c.message.message_id)
        bot.send_message(uid, "❌ Yêu cầu nạp bị từ chối.")

@bot.message_handler(func=lambda m: m.text == "👤 Thông Tin")
def info(m):
    bot.send_message(m.chat.id, f"🆔 ID: {m.from_user.id}\n💰 Ví: {VI_TIEN.get(m.from_user.id, 0):,}đ")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
