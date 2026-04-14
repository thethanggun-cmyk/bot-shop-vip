import telebot
from telebot import types
from flask import Flask
from threading import Thread
import os

# --- [CẤU HÌNH] ---
TOKEN = '8732552211:AAEpggeMdz51o5rREuIhtD22pfJPuJG30yQ'
ADMIN_ID = 7652160174

# --- [DỮ LIỆU] ---
KHO_ACC = {"lv5": [], "kc": []}
USERS_DATA = {} 

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
    uname = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    if uid not in USERS_DATA:
        USERS_DATA[uid] = {"name": uname, "money": 0}
    else:
        USERS_DATA[uid]["name"] = uname

    text = (
        "🔥 CLONE GUN STORE VN\n"
        "📩 Acc Lv5/Kc Giá Rẻ\n"
        "💬 Cskh @guncheatvn\n"
        "🌐 Bot Uytin Tự Động Auto 24/7🛍️"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 Mua Acc", "👤 Thông Tin")
    markup.add("💳 Nạp Tiền")
    if uid == ADMIN_ID: markup.add("⚙️ Quản Lý Admin")
    bot.send_message(message.chat.id, text, reply_markup=markup)

# --- [QUY TRÌNH NẠP TIỀN - CẬP NHẬT MBV BANK] ---
@bot.message_handler(func=lambda m: m.text == "💳 Nạp Tiền")
def request_deposit(message):
    msg = bot.send_message(message.chat.id, "💰 Nhập số tiền muốn nạp:")
    bot.register_next_step_handler(msg, process_deposit_step)

def process_deposit_step(message):
    try:
        amount = int(message.text)
        uid = message.from_user.id
        stk = "04312345" # Số tài khoản của bạn
        bank_id = "mbbank" # Vẫn giữ mbbank để hệ thống VietQR tạo mã đúng ngân hàng MB
        noi_dung = f"NAP{uid}"
        
        qr_link = f"https://img.vietqr.io/image/{bank_id}-{stk}-compact2.png?amount={amount}&addInfo={noi_dung}"
        
        txt = (
            f"🏦 **MBV BANK**\n"
            f"💳 **STK:** `{stk}`\n"
            f"💰 **Tiền:** `{amount:,}đ`\n"
            f"📝 **ND:** `{noi_dung}`\n"
            f"🏧 **Link Qr:** [Nhấn để lấy mã QR]({qr_link})"
        )
        
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("✅ XÁC NHẬN ĐÃ CHUYỂN", callback_data=f"conf_{uid}_{amount}"))
        bot.send_message(message.chat.id, txt, reply_markup=mk, parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "❌ Lỗi! Nhập số tiền hợp lệ.")

# --- [XỬ LÝ ADMIN & THỐNG KÊ] ---
@bot.message_handler(func=lambda m: m.text == "⚙️ Quản Lý Admin")
def admin_panel(m):
    if m.from_user.id != ADMIN_ID: return
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("📊 Thống Kê All User", callback_data="admin_stats"))
    mk.add(types.InlineKeyboardButton("📦 Xem Kho Acc", callback_data="admin_check_kho"))
    bot.send_message(m.chat.id, "🛠 **BẢNG ĐIỀU KHIỂN ADMIN**", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_"))
def handle_admin_callback(c):
    if c.from_user.id != ADMIN_ID: return
    if c.data == "admin_stats":
        report = "📊 **DANH SÁCH NGƯỜI DÙNG**\n----------------------------\n"
        for idx, (uid, info) in enumerate(USERS_DATA.items(), 1):
            report += f"{idx}. {info['name']} (`{uid}`) | Ví: {info['money']:,}đ\n"
        report += f"----------------------------\nTổng: {len(USERS_DATA)} người."
        bot.send_message(ADMIN_ID, report, parse_mode="Markdown")
    elif c.data == "admin_check_kho":
        bot.send_message(ADMIN_ID, f"📦 **KHO HÀNG**\n🛒 Lv5: {len(KHO_ACC['lv5'])}\n🛒 Kc: {len(KHO_ACC['kc'])}")

# --- [XỬ LÝ DUYỆT NẠP] ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("conf_"))
def customer_confirm(c):
    _, uid, amt = c.data.split("_")
    bot.edit_message_text("✅ Đã gửi yêu cầu! Chờ admin.", c.message.chat.id, c.message.message_id)
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
        if uid in USERS_DATA:
            USERS_DATA[uid]["money"] += amt
            bot.edit_message_text(f"✅ Đã duyệt {amt}đ cho {uid}", c.message.chat.id, c.message.message_id)
            bot.send_message(uid, f"🔔 Nạp thành công {amt:,}đ!")
    else:
        bot.edit_message_text(f"❌ Từ chối ID {uid}", c.message.chat.id, c.message.message_id)
        bot.send_message(uid, "❌ Yêu cầu bị từ chối.")

# --- [MUA BÁN & THÔNG TIN] ---
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
        if USERS_DATA[uid]["money"] < qty * gia:
            bot.send_message(m.chat.id, "❌ Không đủ tiền!"); return
        if len(KHO_ACC[loai]) < qty:
            bot.send_message(m.chat.id, "❌ Kho không đủ!"); return
        accs = [KHO_ACC[loai].pop(0) for _ in range(qty)]
        USERS_DATA[uid]["money"] -= qty * gia
        bot.send_message(m.chat.id, f"✅ Thành công!\n🔑 Acc:\n" + "\n".join(accs))
    except: bot.send_message(m.chat.id, "❌ Lỗi nhập liệu.")

@bot.message_handler(func=lambda m: m.text == "👤 Thông Tin")
def info(m):
    uid = m.from_user.id
    money = USERS_DATA.get(uid, {"money": 0})["money"]
    bot.send_message(m.chat.id, f"🆔 ID: {uid}\n💰 Ví: {money:,}đ")

@bot.message_handler(commands=['addlv5', 'addkc'])
def add_acc_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    cmd = message.text.split(maxsplit=1)
    if len(cmd) < 2: return
    loai = "lv5" if "addlv5" in cmd[0] else "kc"
    KHO_ACC[loai].append(cmd[1])
    bot.reply_to(message, f"✅ Đã thêm acc {loai.upper()}!")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
