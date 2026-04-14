import telebot
from telebot import types
from flask import Flask
from threading import Thread
import os

# --- [CẤU HÌNH] ---
TOKEN = '8732552211:AAEpggeMdz51o5rREuIhtD22pfJPuJG30yQ'
ADMIN_ID = 7652160174

# --- [KHO HÀNG & VÍ] ---
KHO_ACC = {
    "lv5": [],
    "kc": []
}
VI_TIEN = {}

bot = telebot.TeleBot(TOKEN)
server = Flask('')

@server.route('/')
def home(): return "Bot is Online!"

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
        "🌐 **Bot :** @clonegunstorevn_bot **Uytin Tự Động Auto 24/7**🛍️"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 Mua Acc", "👤 Thông Tin")
    markup.add("💳 Nạp Tiền")
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

# --- [QUY TRÌNH NẠP TIỀN] ---
@bot.message_handler(func=lambda m: m.text == "💳 Nạp Tiền")
def request_deposit(message):
    msg = bot.send_message(message.chat.id, "💰 **Vui lòng nhập số tiền bạn muốn nạp:**")
    bot.register_next_step_handler(msg, process_deposit_step)

def process_deposit_step(message):
    try:
        amount = int(message.text)
        uid = message.from_user.id
        txt = f"🏦 **MB BANK**\n💳 **STK:** `12345678`\n💰 **Số tiền:** `{amount:,}đ`\n📝 **Nội dung:** `NAP {uid}`"
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("✅ XÁC NHẬN ĐÃ CHUYỂN", callback_data=f"confirm_dep_{uid}_{amount}"))
        bot.send_message(message.chat.id, txt, reply_markup=mk, parse_mode="Markdown")
    except: bot.send_message(message.chat.id, "❌ Vui lòng nhập số tiền hợp lệ.")

# --- [XỬ LÝ CALLBACK (MUA HÀNG & DUYỆT NẠP)] ---
@bot.callback_query_handler(func=lambda c: True)
def handle_callback(c):
    # 1. Khách nhấn xác nhận đã chuyển tiền
    if c.data.startswith("confirm_dep_"):
        _, _, uid, amount = c.data.split("_")
        bot.edit_message_text("✅ **Yêu cầu đã gửi!** Vui lòng đợi Admin duyệt.", c.message.chat.id, c.message.message_id)
        
        # Gửi nút Duyệt cho Admin
        admin_mk = types.InlineKeyboardMarkup()
        admin_mk.add(
            types.InlineKeyboardButton("✅ Duyệt", callback_data=f"admin_accept_{uid}_{amount}"),
            types.InlineKeyboardButton("❌ Hủy", callback_data=f"admin_decline_{uid}")
        )
        bot.send_message(ADMIN_ID, f"🔔 **YÊU CẦU NẠP TIỀN**\n👤 Khách: {c.from_user.first_name}\n🆔 ID: `{uid}`\n💰 Tiền: `{amount}đ`", reply_markup=admin_mk, parse_mode="Markdown")

    # 2. Admin nhấn Duyệt
    elif c.data.startswith("admin_accept_"):
        _, _, uid, amount = c.data.split("_")
        uid = int(uid)
        amount = int(amount)
        VI_TIEN[uid] = VI_TIEN.get(uid, 0) + amount
        
        bot.edit_message_text(f"✅ Đã duyệt {amount}đ cho ID {uid}", c.message.chat.id, c.message.message_id)
        bot.send_message(uid, f"🔔 **Nạp tiền thành công!** Bạn đã được cộng `{amount:,}đ` vào tài khoản.")

    # 3. Admin nhấn Hủy
    elif c.data.startswith("admin_decline_"):
        uid = int(c.data.split("_")[2])
        bot.edit_message_text(f"❌ Đã từ chối yêu cầu của ID {uid}", c.message.chat.id, c.message.message_id)
        bot.send_message(uid, "❌ **Yêu cầu nạp tiền của bạn bị từ chối.** Vui lòng liên hệ Admin @guncheatvn để kiểm tra.")

    # 4. Xử lý mua hàng
    elif c.data.startswith("ask_"):
        loai = "lv5" if "lv5" in c.data else "kc"
        msg = bot.send_message(c.message.chat.id, f"🔢 **Nhập số lượng Acc {loai.upper()} muốn mua:**")
        bot.register_next_step_handler(msg, lambda m: process_buy_quantity(m, loai))

def process_buy_quantity(message, loai):
    try:
        soluong = int(message.text)
        uid = message.from_user.id
        gia = 2000 if loai == "lv5" else 30000
        tong = soluong * gia
        if VI_TIEN.get(uid, 0) < tong:
            bot.send_message(message.chat.id, "❌ Bạn không đủ tiền!"); return
        if len(KHO_ACC[loai]) < soluong:
            bot.send_message(message.chat.id, f"❌ Kho hàng không đủ!"); return
            
        acc_lay = [KHO_ACC[loai].pop(0) for _ in range(soluong)]
        VI_TIEN[uid] -= tong
        bot.send_message(message.chat.id, f"✅ **Thành công!**\n🔑 Acc:\n`" + "\n".join(acc_lay) + "`", parse_mode="Markdown")
    except: bot.send_message(message.chat.id, "❌ Lỗi nhập liệu.")

# --- [CÁC LỆNH CÒN LẠI] ---
@bot.message_handler(func=lambda m: m.text == "🛒 Mua Acc")
def shop(m):
    text = f"🔥 **CLONE GUN STORE VN**\n🛒 **Lv5 2k/1acc (Còn: {len(KHO_ACC['lv5'])})**\n🛒 **Kc 30k/1acc (Còn: {len(KHO_ACC['kc'])})**\n**Auto 100% Uytin Số 1** 🛍️"
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("Mua Lv5 🛒", callback_data="ask_lv5"), types.InlineKeyboardButton("Mua Kc 🛒", callback_data="ask_kc"))
    bot.send_message(m.chat.id, text, reply_markup=mk, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 Thông Tin")
def info(m):
    bot.send_message(m.chat.id, f"🆔 **ID:** `{m.from_user.id}`\n💰 **Ví:** `{VI_TIEN.get(m.from_user.id, 0):,}đ`", parse_mode="Markdown")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
