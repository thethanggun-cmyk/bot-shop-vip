import telebot
from telebot import types
from flask import Flask
from threading import Thread
import os

# --- [CẤU HÌNH] ---
TOKEN = '8732552211:AAEpggeMdz51o5rREuIhtD22pfJPuJG30yQ'
ADMIN_ID = 7652160174

# --- [KHO HÀNG THẬT - TỰ ĐỘNG CẬP NHẬT] ---
KHO_ACC = {
    "lv5": [
        "acc_lv5_01|pass123",
        "acc_lv5_02|pass456"
    ],
    "kc": [
        "acc_kc_01|pass789",
        "acc_kc_02|pass000"
    ]
}
VI_TIEN = {}

bot = telebot.TeleBot(TOKEN)
server = Flask('')

@server.route('/')
def home():
    return "Bot is Online!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    server.run(host='0.0.0.0', port=port)

# --- [GIAO DIỆN CHÍNH] ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in VI_TIEN: VI_TIEN[uid] = 0
    
    text = (
        "🔥 **CLONE GUN STORE VN**\n"
        "📩 **Acc Lv5/Kc Giá Rẻ**\n"
        "💬 **Cskh** @guncheatvn\n\n"
        "🌐 **Bot :** @clonegunstorevn_bot **Uytin Tự Động Auto 24/7**🛍️\n"
        "--------------------------\n"
        f"💰 **Số dư của bạn:** `{VI_TIEN[uid]:,}đ`"
    )
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 Mua Acc", "👤 Thông Tin")
    markup.add("💳 Nạp Tiền")
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

# --- [MENU MUA HÀNG - CÓ HIỆN TỒN KHO] ---
@bot.message_handler(func=lambda m: m.text == "🛒 Mua Acc")
def show_shop(m):
    # Lấy số lượng thực tế từ kho
    count_lv5 = len(KHO_ACC["lv5"])
    count_kc = len(KHO_ACC["kc"])
    
    text = (
        "🔥 **CLONE GUN STORE VN**\n"
        f"🛒 **Lv5 2k/1acc (Còn: {count_lv5})**\n"
        f"🛒 **Kc 30k/1acc (Còn: {count_kc})**\n"
        "**Auto 100% Uytin Số 1** 🛍️"
    )
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("Mua Lv5 🛒", callback_data="ask_lv5"),
           types.InlineKeyboardButton("Mua Kc 🛒", callback_data="ask_kc"))
    bot.send_message(m.chat.id, text, reply_markup=mk, parse_mode="Markdown")

# --- [XỬ LÝ NHẬP SỐ LƯỢNG] ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("ask_"))
def ask_quantity(c):
    loai = "lv5" if "lv5" in c.data else "kc"
    msg = bot.send_message(c.message.chat.id, f"🔢 **Vui lòng nhập số lượng Acc {loai.upper()} muốn mua:**")
    bot.register_next_step_handler(msg, lambda m: process_buy_quantity(m, loai))

def process_buy_quantity(message, loai):
    try:
        soluong = int(message.text)
        if soluong <= 0:
            bot.send_message(message.chat.id, "❌ Số lượng phải lớn hơn 0!")
            return
        
        uid = message.from_user.id
        gia_mot_acc = 2000 if loai == "lv5" else 30000
        tong_tien = soluong * gia_mot_acc
        
        if VI_TIEN.get(uid, 0) < tong_tien:
            bot.send_message(message.chat.id, f"❌ Không đủ tiền! Cần `{tong_tien:,}đ`."); return
        
        if len(KHO_ACC[loai]) < soluong:
            bot.send_message(message.chat.id, f"❌ Kho không đủ! Chỉ còn `{len(KHO_ACC[loai])}` acc."); return
        
        # Lấy acc và trừ tiền
        acc_da_mua = [KHO_ACC[loai].pop(0) for _ in range(soluong)]
        VI_TIEN[uid] -= tong_tien
        
        res = f"✅ **THÀNH CÔNG {soluong} ACC {loai.upper()}**\n\n🔑 **List acc:**\n`" + "\n".join(acc_da_mua) + "`"
        bot.send_message(message.chat.id, res, parse_mode="Markdown")
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Vui lòng nhập con số cụ thể!")

# --- [QUY TRÌNH NẠP TIỀN] ---
@bot.message_handler(func=lambda m: m.text == "💳 Nạp Tiền")
def request_deposit(message):
    msg = bot.send_message(message.chat.id, "💰 **Nhập số tiền bạn muốn nạp:**")
    bot.register_next_step_handler(msg, process_deposit_step)

def process_deposit_step(message):
    try:
        amount = int(message.text)
        uid = message.from_user.id
        bank_text = (
            f"🏦 **NGÂN HÀNG MB BANK**\n"
            f"💳 **STK:** `12345678`\n"
            f"💰 **Số tiền:** `{amount:,}đ`\n"
            f"📝 **Nội dung:** `NAP {uid}`\n"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ XÁC NHẬN ĐÃ CHUYỂN", callback_data=f"confirm_dep_{amount}"))
        bot.send_message(message.chat.id, bank_text, reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "❌ Lỗi! Vui lòng nhập số tiền bằng số.")

# --- [CALLBACK XỬ LÝ NÚT BẤM] ---
@bot.callback_query_handler(func=lambda c: True)
def handle_callback(c):
    if c.data.startswith("confirm_dep_"):
        amount = c.data.split("_")[2]
        bot.edit_message_text("✅ **Yêu cầu đã gửi!** Vui lòng đợi Admin duyệt.", c.message.chat.id, c.message.message_id)
        bot.send_message(ADMIN_ID, f"🔔 **NẠP TIỀN:** ID `{c.from_user.id}` nạp `{amount}đ`.\nLệnh: `/setmoney {c.from_user.id} {amount}`")

# --- [LỆNH THÔNG TIN & ADMIN] ---
@bot.message_handler(func=lambda m: m.text == "👤 Thông Tin")
def info(m):
    uid = m.from_user.id
    bot.send_message(m.chat.id, f"🆔 **ID:** `{uid}`\n💰 **Ví:** `{VI_TIEN.get(uid, 0):,}đ`", parse_mode="Markdown")

@bot.message_handler(commands=['setmoney'])
def set_money(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, target_id, amount = message.text.split()
        VI_TIEN[int(target_id)] = int(amount)
        bot.send_message(ADMIN_ID, f"✅ Đã đặt {amount}đ cho {target_id}")
        bot.send_message(int(target_id), f"🔔 **Tài khoản được cộng {int(amount):,}đ!**")
    except: pass

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
