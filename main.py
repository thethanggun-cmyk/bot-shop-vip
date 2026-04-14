import telebot
from telebot import types
from flask import Flask
from threading import Thread
import os

# --- [CẤU HÌNH] ---
TOKEN = '8732552211:AAEpggeMdz51o5rREuIhtD22pfJPuJG30yQ'
ADMIN_ID = 7652160174

# --- [DỮ LIỆU TẠM THỜI] ---
# Lưu ý: Toàn bộ dữ liệu dưới đây sẽ biến mất khi bot restart
KHO_HANG = {
    "lv5": ["acc_lv5_01|pass123", "acc_lv5_02|pass456"],
    "kc": ["acc_kc_01|pass789", "acc_kc_02|pass000"]
}

# Lưu số dư khách trong bộ nhớ RAM
VI_TIEN = {}

bot = telebot.TeleBot(TOKEN)
app = Flask('')

@app.route('/')
def home(): return "Bot is Online (No DB mode)"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- [LOGIC BOT] ---
def get_balance(uid):
    return VI_TIEN.get(uid, 0)

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in VI_TIEN: VI_TIEN[uid] = 0 # Mặc định 0đ
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 Mua Acc", "👤 Thông Tin")
    markup.add("💳 Nạp Tiền")
    
    bot.send_message(message.chat.id, 
        f"🔥 **CLONE GUN STORE**\n💰 Số dư: `{VI_TIEN[uid]:,}đ`", 
        reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_msg(m):
    uid = m.from_user.id
    if uid not in VI_TIEN: VI_TIEN[uid] = 0

    if m.text == "🛒 Mua Acc":
        txt = (f"🔥 **KHO HÀNG**\n"
               f"🛒 Lv5 (2k): {len(KHO_HANG['lv5'])}\n"
               f"🛒 Kc (30k): {len(KHO_HANG['kc'])}")
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("Mua Lv5", callback_data="buy_lv5"),
               types.InlineKeyboardButton("Mua Kc", callback_data="buy_kc"))
        bot.send_message(m.chat.id, txt, reply_markup=mk, parse_mode="Markdown")

    elif m.text == "👤 Thông Tin":
        bot.send_message(m.chat.id, f"🆔 ID: `{uid}`\n💰 Ví: {VI_TIEN[uid]:,}đ", parse_mode="Markdown")

    elif m.text == "💳 Nạp Tiền":
        bot.send_message(m.chat.id, f"🏦 MB BANK\nSTK: `12345678`\nND: `NAP {uid}`\n*(Dùng lệnh /setmoney {uid} [số tiền] để cộng)*")

# --- [LỆNH ADMIN] ---
@bot.message_handler(commands=['setmoney'])
def set_money(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, target_id, amount = message.text.split()
        VI_TIEN[int(target_id)] = int(amount)
        bot.send_message(ADMIN_ID, f"✅ Đã đặt {amount}đ cho {target_id}")
    except: bot.send_message(ADMIN_ID, "Cú pháp: `/setmoney ID tiền`")

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def handle_buy(c):
    uid = c.from_user.id
    loai = "lv5" if "lv5" in c.data else "kc"
    gia = 2000 if loai == "lv5" else 30000
    
    if VI_TIEN.get(uid, 0) < gia:
        bot.answer_callback_query(c.id, "❌ Không đủ tiền!"); return
    if not KHO_HANG[loai]:
        bot.answer_callback_query(c.id, "❌ Hết hàng!"); return

    # Bán acc
    acc = KHO_HANG[loai].pop(0)
    VI_TIEN[uid] -= gia
    bot.send_message(c.message.chat.id, f"✅ Thành công!\n🔑 Acc: `{acc}`", parse_mode="Markdown")

if __name__ == "__main__":
    Thread(target=run).start()
    bot.infinity_polling()
