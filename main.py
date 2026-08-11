import logging
import os
import json
import time
import asyncio
from datetime import date, datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ---- Logging ----
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---- Biến môi trường ----
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN chưa được set!")

MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI chưa được set!")

ADMIN_ID = int(os.environ.get("ADMIN_ID", "8348411770"))
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "@guncpw")

# ---- Kết nối MongoDB ----
from pymongo import MongoClient, ASCENDING, DESCENDING

client = MongoClient(MONGO_URI)
db = client["gun_store"]  # tên database cũ

# Tạo index
db.users.create_index([("userId", ASCENDING)], unique=True)
db.accounts.create_index([("_id", ASCENDING)])
db.accounts_free.create_index([("_id", ASCENDING)])
db.purchases.create_index([("userId", ASCENDING), ("timestamp", DESCENDING)])
db.deposits.create_index([("userId", ASCENDING), ("timestamp", DESCENDING)])
db.invite_history.create_index([("raw_time", DESCENDING)])

# ---- Các hàm xử lý database ----
def get_user(user_id):
    uid = str(user_id)
    user = db.users.find_one({"userId": uid})
    if not user:
        user = {
            "userId": uid,
            "username": None,
            "balance": 0,
            "coins": 0,
            "total_recharge": 0,
            "referred_by": None,
            "verified": False,
            "free_acc_count": 0,
            "last_free_date": None
        }
        db.users.insert_one(user)
    return user

def update_user(user_id, update_data):
    db.users.update_one({"userId": str(user_id)}, {"$set": update_data}, upsert=True)

def inc_user(user_id, field, amount):
    db.users.update_one({"userId": str(user_id)}, {"$inc": {field: amount}}, upsert=True)

def get_stock(acc_type):
    col = db["accounts"] if acc_type in ["7day", "24h"] else db["accounts_free"]
    return list(col.find({"type": acc_type}))

def add_to_stock(acc_type, acc_list):
    col = db["accounts"] if acc_type in ["7day", "24h"] else db["accounts_free"]
    docs = [{"type": acc_type, "acc": a} for a in acc_list if a]
    if docs:
        col.insert_many(docs)
    return len(docs)

def remove_from_stock(acc_type, qty):
    col = db["accounts"] if acc_type in ["7day", "24h"] else db["accounts_free"]
    docs = list(col.find({"type": acc_type}).limit(qty))
    if len(docs) < qty:
        return False, []
    ids = [d["_id"] for d in docs]
    col.delete_many({"_id": {"$in": ids}})
    return True, [d["acc"] for d in docs]

def get_all_user_ids():
    return [u["userId"] for u in db.users.find({}, {"userId": 1})]

def create_deposit_request(user_id, amount):
    dep_id = f"{int(time.time())}_{user_id}"
    doc = {
        "depositId": dep_id,
        "userId": str(user_id),
        "amount": amount,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "timestamp": time.time()
    }
    db.deposits.insert_one(doc)
    return dep_id

def get_deposit(dep_id):
    return db.deposits.find_one({"depositId": dep_id})

def approve_deposit(dep_id):
    dep = db.deposits.find_one({"depositId": dep_id})
    if not dep or dep["status"] != "pending":
        return False
    db.deposits.update_one({"depositId": dep_id}, {"$set": {"status": "approved"}})
    uid = dep["userId"]
    amount = dep["amount"]
    inc_user(uid, "balance", amount)
    inc_user(uid, "total_recharge", amount)
    return True

def can_get_free_acc(user_id):
    uid = str(user_id)
    user = get_user(uid)
    today = date.today().isoformat()
    if user.get("last_free_date") != today:
        return True, 0
    used = user.get("free_acc_count", 0)
    return used < 3, used

def record_free_acc(user_id, qty):
    uid = str(user_id)
    user = get_user(uid)
    today = date.today().isoformat()
    if user.get("last_free_date") != today:
        db.users.update_one({"userId": uid}, {"$set": {"free_acc_count": qty, "last_free_date": today}})
    else:
        db.users.update_one({"userId": uid}, {"$inc": {"free_acc_count": qty}})

# ---- Bàn phím ----
ADMIN_KEYBOARD = [
    ["Mua Acc Lv5", "Mời Bạn Bè"],
    ["Acc Free Lv5", "Số Dư"],
    ["Hỗ Trợ", "Nạp Tiền"],
    ["Admin"],
]
USER_KEYBOARD = [
    ["Mua Acc Lv5", "Mời Bạn Bè"],
    ["Acc Free Lv5", "Số Dư"],
    ["Hỗ Trợ", "Nạp Tiền"],
]

# ---- Bot handlers ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    uid = str(user_id)

    # Tạo user nếu chưa có
    user_data = get_user(uid)

    # Xử lý link mời
    if context.args and context.args[0].startswith("invite_"):
        referrer_id_str = context.args[0].replace("invite_", "")
        try:
            referrer_id = int(referrer_id_str)
        except ValueError:
            referrer_id = None

        if referrer_id and referrer_id != user_id:
            if user_data.get("verified"):
                await update.message.reply_text("✅ Bạn đã được xác minh trước đó.")
            else:
                context.user_data["awaiting_verification"] = True
                context.user_data["referrer_id"] = referrer_id
                await update.message.reply_text(
                    "🔐 **XÁC MINH NGƯỜI GIỚI THIỆU**\n\n"
                    "Vui lòng trả lời câu hỏi sau:\n"
                    "**9 + 9 + 9 = ?**\n\n"
                    "(Nhập số)",
                    parse_mode="Markdown"
                )
                return
        else:
            await update.message.reply_text("⚠️ Link mời không hợp lệ hoặc bạn tự mời chính mình.")

    keyboard = ADMIN_KEYBOARD if user_id == ADMIN_ID else USER_KEYBOARD
    await update.message.reply_text(
        f"Chào {user.first_name}! Vui lòng chọn chức năng:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ---- Lệnh Admin ----
async def addlv5_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bạn không có quyền.")
        return
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Add Lv5 7Day", callback_data="admin_add_7day")],
        [InlineKeyboardButton("Add Lv5 24H-72H", callback_data="admin_add_24h")],
        [InlineKeyboardButton("Add Free Lv5", callback_data="admin_add_free")],
    ])
    await update.message.reply_text(
        "📦 **THÊM ACC VÀO KHO**\n\n"
        "1. Add Lv5 7Day - Định dạng tk:mk\n"
        "2. Add Lv5 24H-72H - Định dạng tk:mk\n"
        "3. Add Free Lv5 - Định dạng tk:mk\n\n"
        "👇 Chọn loại acc:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def thongbao_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bạn không có quyền.")
        return
    if not context.args:
        await update.message.reply_text("❌ Vui lòng nhập nội dung.\nVí dụ: `/thongbao Hôm nay có khuyến mãi!`")
        return
    content = " ".join(context.args)
    users = get_all_user_ids()
    if not users:
        await update.message.reply_text("❌ Chưa có người dùng nào.")
        return

    await update.message.reply_text(f"⏳ Đang gửi đến {len(users)} người...")
    ok = 0
    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=f"📢 **THÔNG BÁO**\n\n{content}", parse_mode="Markdown")
            ok += 1
        except Exception:
            pass
        await asyncio.sleep(0.1)
    await update.message.reply_text(f"✅ Đã gửi thành công: {ok}/{len(users)}.")

async def user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bạn không có quyền.")
        return
    users = get_all_user_ids()
    if not users:
        await update.message.reply_text("❌ Chưa có user nào.")
        return

    chunk_size = 15
    chunks = [users[i:i+chunk_size] for i in range(0, len(users), chunk_size)]
    await update.message.reply_text(f"📋 **TỔNG SỐ USER:** {len(users)}")

    for idx, chunk in enumerate(chunks, 1):
        msg = f"📋 **Nhóm {idx}/{len(chunks)}**\n\n"
        for uid in chunk:
            u = get_user(uid)
            try:
                chat = await context.bot.get_chat(int(uid))
                uname = f"@{chat.username}" if chat.username else "không có"
            except:
                uname = "không có"
            msg += f"• {uname} | ID: {uid} | 💰 {u.get('balance',0):,} VND | 🪙 {u.get('coins',0)} Coin\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
        if idx < len(chunks):
            await asyncio.sleep(2)
    await update.message.reply_text("✅ Đã gửi toàn bộ.")

async def coin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bạn không có quyền.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("❌ /coin @user <số coin>\nVí dụ: /coin 123456 5")
        return
    target = context.args[0]
    try:
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Số coin phải là số nguyên.")
        return

    target_id = None
    if target.startswith("@"):
        username = target[1:].lower()
        for uid in get_all_user_ids():
            try:
                chat = await context.bot.get_chat(int(uid))
                if chat.username and chat.username.lower() == username:
                    target_id = int(uid)
                    break
            except:
                continue
        if not target_id:
            await update.message.reply_text(f"❌ Không tìm thấy {target}.")
            return
    else:
        try:
            target_id = int(target)
        except ValueError:
            await update.message.reply_text("❌ ID không hợp lệ.")
            return

    current = get_user(target_id).get("coins", 0)
    new = current + amount
    if new < 0:
        await update.message.reply_text("❌ Số coin không thể âm.")
        return
    update_user(target_id, {"coins": new})
    action = "cộng" if amount >= 0 else "trừ"
    await update.message.reply_text(f"✅ Đã {action} {abs(amount)} coin cho {target_id}. Hiện: {new}")

async def tien_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bạn không có quyền.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("❌ /tien @user <số tiền>")
        return
    target = context.args[0]
    try:
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Số tiền phải là số nguyên.")
        return

    target_id = None
    if target.startswith("@"):
        username = target[1:].lower()
        for uid in get_all_user_ids():
            try:
                chat = await context.bot.get_chat(int(uid))
                if chat.username and chat.username.lower() == username:
                    target_id = int(uid)
                    break
            except:
                continue
        if not target_id:
            await update.message.reply_text(f"❌ Không tìm thấy {target}.")
            return
    else:
        try:
            target_id = int(target)
        except ValueError:
            await update.message.reply_text("❌ ID không hợp lệ.")
            return

    current = get_user(target_id).get("balance", 0)
    new = current + amount
    if new < 0:
        await update.message.reply_text("❌ Số tiền không thể âm.")
        return
    update_user(target_id, {"balance": new})
    action = "cộng" if amount >= 0 else "trừ"
    await update.message.reply_text(f"✅ Đã {action} {abs(amount):,} VND cho {target_id}. Hiện: {new:,} VND")

# ---- Callback ----
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("admin_add_"):
        if user_id != ADMIN_ID:
            await query.edit_message_text("⛔ Không có quyền.")
            return
        acc_type = data.replace("admin_add_", "")
        context.user_data["admin_adding"] = acc_type
        await query.edit_message_text(
            f"✏️ Nhập danh sách acc cho loại **{acc_type.upper()}**\n"
            "Mỗi dòng 1 acc, định dạng `tk:mk`\n"
            "Nhập `node` hoặc `/cancel` để hủy.",
            parse_mode="Markdown"
        )
        return

    if data.startswith("admin_approve_"):
        if user_id != ADMIN_ID:
            await query.edit_message_text("⛔ Không có quyền.")
            return
        dep_id = data.replace("admin_approve_", "")
        if approve_deposit(dep_id):
            dep = get_deposit(dep_id)
            uid = dep["userId"]
            amount = dep["amount"]
            await query.edit_message_text(f"✅ Đã duyệt lệnh {dep_id}.")
            try:
                await context.bot.send_message(
                    chat_id=int(uid),
                    text=f"🎉 **Đơn nạp đã được duyệt!**\nSố tiền: {amount:,} VND\nCảm ơn bạn.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Không gửi được cho user {uid}: {e}")
        else:
            await query.edit_message_text("❌ Lỗi khi duyệt (lệnh không tồn tại hoặc đã duyệt).")
        return

    if data.startswith("confirm_deposit_"):
        dep_id = data.replace("confirm_deposit_", "")
        dep = get_deposit(dep_id)
        if not dep or dep["status"] != "pending":
            await query.edit_message_text("❌ Lệnh nạp không tồn tại hoặc đã được xử lý.")
            return
        admin_text = (
            f"💳 **YÊU CẦU NẠP TIỀN**\n"
            f"• Người dùng: ID {dep['userId']}\n"
            f"• Số tiền: {dep['amount']:,} VND\n"
            f"• Mã lệnh: {dep_id}\n"
            "👇 Nhấn nút để duyệt."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Duyệt", callback_data=f"admin_approve_{dep_id}")]
        ])
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, reply_markup=keyboard, parse_mode="Markdown")
        await query.edit_message_text(
            f"✅ Đã gửi yêu cầu duyệt cho admin.\n"
            f"Vui lòng chờ admin xử lý (thường vài phút).\n"
            f"Liên hệ admin nếu quá lâu: {ADMIN_USERNAME}"
        )
        return

    if data == "buy_7day" or data == "buy_24h":
        acc_type = "7day" if data == "buy_7day" else "24h"
        price = 1500 if acc_type == "7day" else 1000
        name = "Acc Lv5 | 7 Day" if acc_type == "7day" else "Acc Lv5 | 24H-72H"
        stock = len(get_stock(acc_type))
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("1", callback_data=f"qty_{acc_type}_1"),
             InlineKeyboardButton("3", callback_data=f"qty_{acc_type}_3"),
             InlineKeyboardButton("5", callback_data=f"qty_{acc_type}_5")],
            [InlineKeyboardButton("10", callback_data=f"qty_{acc_type}_10")],
            [InlineKeyboardButton("Nhập số lượng khác", callback_data=f"qty_{acc_type}_custom")],
            [InlineKeyboardButton("⬅ Quay lại", callback_data="back_to_buy")]
        ])
        await query.edit_message_text(
            f"⚡ **{name}**\n"
            f"💰 Giá: {price}đ/acc\n"
            f"📦 Tồn kho: {stock} acc\n\n"
            "👇 Chọn số lượng:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        return

    if data == "back_to_buy":
        stock_7 = len(get_stock("7day"))
        stock_24 = len(get_stock("24h"))
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Acc Lv5 7Day | 1.500đ", callback_data="buy_7day")],
            [InlineKeyboardButton("Acc Lv5 24H-72H | 1.000đ", callback_data="buy_24h")]
        ])
        await query.edit_message_text(
            "🛒 **KHU VỰC MUA ACC**\n"
            f"⚡ 7Day: {stock_7} acc\n"
            f"🎲 24H-72H: {stock_24} acc\n\n"
            "👇 Chọn loại:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        return

    if data.startswith("qty_7day_") or data.startswith("qty_24h_"):
        parts = data.split("_")
        acc_type = parts[1]
        qty_str = parts[2]
        if qty_str == "custom":
            context.user_data["awaiting_custom_qty"] = True
            context.user_data["acc_type"] = acc_type
            await query.edit_message_text("✏️ Nhập số lượng (ví dụ: 2):\nGửi /cancel để hủy.")
            return
        qty = int(qty_str)
        await process_purchase(query, user_id, acc_type, qty)
        return

    if data == "buy_free":
        stock = len(get_stock("free"))
        coins = get_user(user_id).get("coins", 0)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("1", callback_data="free_qty_1"),
             InlineKeyboardButton("3", callback_data="free_qty_3")],
            [InlineKeyboardButton("Nhập số lượng", callback_data="free_qty_custom")],
            [InlineKeyboardButton("⬅ Quay lại", callback_data="back_to_buy")]
        ])
        await query.edit_message_text(
            f"⚡ **Acc Free Lv5**\n"
            f"💰 1 acc = 5 Coin\n"
            f"📦 Tồn kho: {stock} acc\n"
            f"🪙 Số coin: {coins}\n\n"
            "⚠️ Tối đa 3 acc/ngày\n\n"
            "👇 Chọn số lượng:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        return

    if data.startswith("free_qty_"):
        qty_str = data.split("_")[-1]
        if qty_str == "custom":
            context.user_data["awaiting_free_custom"] = True
            await query.edit_message_text("✏️ Nhập số lượng (tối đa 3):\nGửi /cancel để hủy.")
            return
        qty = int(qty_str)
        await process_free_purchase(query, user_id, qty)
        return

    await query.edit_message_text("❌ Lựa chọn không hợp lệ.")

# ---- Xử lý mua Acc Lv5 ----
async def process_purchase(query, user_id, acc_type, qty):
    price = 1500 if acc_type == "7day" else 1000
    total = price * qty
    user = get_user(user_id)
    if user["balance"] < total:
        await query.edit_message_text(
            f"❌ Số dư không đủ!\nCần: {total:,} VND, có: {user['balance']:,} VND",
            parse_mode="Markdown"
        )
        return
    stock = get_stock(acc_type)
    if len(stock) < qty:
        await query.edit_message_text(f"❌ Không đủ acc! Còn {len(stock)} acc.", parse_mode="Markdown")
        return
    inc_user(user_id, "balance", -total)
    success, accs = remove_from_stock(acc_type, qty)
    if not success:
        await query.edit_message_text("❌ Lỗi khi lấy acc, vui lòng thử lại.")
        return
    await query.edit_message_text(
        f"✅ **Mua thành công!**\n"
        f"Số lượng: {qty}\n"
        f"Tổng: {total:,} VND\n"
        f"Số dư còn: {user['balance']-total:,} VND\n\n"
        f"📋 **Danh sách acc:**\n" + "\n".join(accs),
        parse_mode="Markdown"
    )

# ---- Xử lý mua Acc Free ----
async def process_free_purchase(query, user_id, qty):
    user = get_user(user_id)
    can_get, used = can_get_free_acc(user_id)
    if not can_get:
        await query.edit_message_text(f"❌ Hôm nay bạn đã lấy {used} acc (tối đa 3).", parse_mode="Markdown")
        return
    remaining = 3 - used
    if qty > remaining:
        await query.edit_message_text(f"❌ Bạn chỉ có thể lấy thêm {remaining} acc hôm nay.", parse_mode="Markdown")
        return
    total_coin = qty * 5
    if user["coins"] < total_coin:
        await query.edit_message_text(f"❌ Không đủ coin! Cần {total_coin}, có {user['coins']}", parse_mode="Markdown")
        return
    stock = get_stock("free")
    if len(stock) < qty:
        await query.edit_message_text(f"❌ Không đủ acc free! Còn {len(stock)}", parse_mode="Markdown")
        return
    inc_user(user_id, "coins", -total_coin)
    success, accs = remove_from_stock("free", qty)
    if not success:
        await query.edit_message_text("❌ Lỗi lấy acc, thử lại.")
        return
    record_free_acc(user_id, qty)
    await query.edit_message_text(
        f"✅ **Đổi Acc Free thành công!**\n"
        f"Số lượng: {qty}\n"
        f"Coin đã dùng: {total_coin}\n"
        f"Coin còn: {user['coins']-total_coin}\n\n"
        f"📋 **Acc:**\n" + "\n".join(accs),
        parse_mode="Markdown"
    )

# ---- Xử lý tin nhắn ----
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    text = update.message.text

    if text in ["/cancel", "node"]:
        for key in ["awaiting_verification", "awaiting_custom_qty", "awaiting_free_custom", "admin_adding", "awaiting_recharge"]:
            if context.user_data.get(key):
                context.user_data.pop(key)
                await update.message.reply_text("✅ Đã hủy thao tác.")
                return
        await update.message.reply_text("Không có thao tác nào để hủy.")
        return

    if context.user_data.get("awaiting_verification"):
        if not text.isdigit():
            await update.message.reply_text("❌ Vui lòng nhập số.")
            return
        if int(text) == 27:
            referrer_id = context.user_data.pop("referrer_id")
            uid = str(user_id)
            db.users.update_one({"userId": uid}, {"$set": {"verified": True, "referred_by": str(referrer_id)}})
            inc_user(referrer_id, "coins", 1)
            await update.message.reply_text("✅ Xác minh thành công! Người mời nhận +1 coin.")
            context.user_data.pop("awaiting_verification")
        else:
            await update.message.reply_text("❌ Sai rồi! Thử lại hoặc gửi /cancel.")
        return

    if context.user_data.get("awaiting_custom_qty"):
        if not text.isdigit():
            await update.message.reply_text("❌ Nhập số nguyên dương.")
            return
        qty = int(text)
        if qty <= 0:
            await update.message.reply_text("❌ Số lượng > 0.")
            return
        acc_type = context.user_data.pop("acc_type")
        context.user_data.pop("awaiting_custom_qty")
        class FakeQuery:
            def __init__(self, msg): self.message = msg
            async def edit_message_text(self, text, **kwargs):
                await self.message.reply_text(text, **kwargs)
        await process_purchase(FakeQuery(update.message), user_id, acc_type, qty)
        return

    if context.user_data.get("awaiting_free_custom"):
        if not text.isdigit():
            await update.message.reply_text("❌ Nhập số nguyên dương.")
            return
        qty = int(text)
        if qty <= 0:
            await update.message.reply_text("❌ Số lượng > 0.")
            return
        context.user_data.pop("awaiting_free_custom")
        class FakeQuery:
            def __init__(self, msg): self.message = msg
            async def edit_message_text(self, text, **kwargs):
                await self.message.reply_text(text, **kwargs)
        await process_free_purchase(FakeQuery(update.message), user_id, qty)
        return

    if context.user_data.get("admin_adding"):
        if user_id != ADMIN_ID:
            await update.message.reply_text("⛔ Không có quyền.")
            return
        acc_type = context.user_data["admin_adding"]
        acc_list = [line.strip() for line in text.splitlines() if line.strip()]
        if not acc_list:
            await update.message.reply_text("❌ Danh sách trống.")
            return
        valid = all(":" in acc for acc in acc_list)
        if not valid:
            await update.message.reply_text("❌ Định dạng phải là tk:mk. Thử lại.")
            return
        added = add_to_stock(acc_type, acc_list)
        await update.message.reply_text(f"✅ Đã thêm {added} acc vào loại {acc_type.upper()}.")
        context.user_data.pop("admin_adding")
        return

    if context.user_data.get("awaiting_recharge"):
        try:
            amount = int(text.replace(",", "").strip())
            if amount < 2000:
                await update.message.reply_text("❌ Tối thiểu 2.000 VND. Nhập lại hoặc /cancel.")
                return
            if amount <= 0:
                raise ValueError
            dep_id = create_deposit_request(user_id, amount)
            desc = f"GunStore{user_id}"
            qr_url = f"https://qr.sepay.vn/img?acc=0794663195&bank=MB&amount={amount}&des={desc}"

            caption = (
                f"💳 **NẠP TIỀN**\n"
                f"🏦 STK: 0794663195\n"
                f"🏛️ Ngân hàng: MB Bank\n"
                f"📝 Nội dung: `{desc}`\n"
                f"💰 Số tiền: {amount:,} VND\n\n"
                "⚠️ **Phải ghi đúng nội dung chuyển khoản!**\n\n"
                "✅ Sau khi chuyển, bấm nút bên dưới để xác nhận."
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Xác nhận đã chuyển tiền", callback_data=f"confirm_deposit_{dep_id}")]
            ])
            await update.message.reply_photo(photo=qr_url, caption=caption, parse_mode="Markdown", reply_markup=keyboard)
            context.user_data.pop("awaiting_recharge")
        except ValueError:
            await update.message.reply_text("❌ Số tiền không hợp lệ. Nhập số nguyên dương.")
        return

    if text == "Mua Acc Lv5":
        stock_7 = len(get_stock("7day"))
        stock_24 = len(get_stock("24h"))
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Acc Lv5 7Day | 1.500đ", callback_data="buy_7day")],
            [InlineKeyboardButton("Acc Lv5 24H-72H | 1.000đ", callback_data="buy_24h")]
        ])
        await update.message.reply_text(
            f"🛒 **KHU VỰC MUA ACC**\n"
            f"⚡ 7Day: {stock_7} acc\n"
            f"🎲 24H-72H: {stock_24} acc\n\n"
            "👇 Chọn loại:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        return

    elif text == "Mời Bạn Bè":
        bot_username = context.bot.username
        link = f"https://t.me/{bot_username}?start=invite_{user_id}"
        await update.message.reply_text(
            f"🔗 **Link mời của bạn:**\n{link}\n\n"
            "Gửi cho bạn bè, họ trả lời đúng câu hỏi bạn nhận 1 coin.",
            parse_mode="Markdown"
        )
        return

    elif text == "Acc Free Lv5":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("1", callback_data="free_qty_1"),
             InlineKeyboardButton("3", callback_data="free_qty_3")],
            [InlineKeyboardButton("Nhập số lượng", callback_data="free_qty_custom")],
            [InlineKeyboardButton("⬅ Quay lại", callback_data="back_to_buy")]
        ])
        coins = get_user(user_id).get("coins", 0)
        stock = len(get_stock("free"))
        await update.message.reply_text(
            f"⚡ **Acc Free Lv5**\n"
            f"💰 1 acc = 5 Coin\n"
            f"📦 Tồn kho: {stock}\n"
            f"🪙 Số coin: {coins}\n\n"
            "⚠️ Tối đa 3 acc/ngày\n\n"
            "👇 Chọn số lượng:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        return

    elif text == "Admin":
        if user_id == ADMIN_ID:
            await update.message.reply_text(
                "👑 **Admin Panel**\n"
                "/addlv5 - Thêm acc\n"
                "/thongbao - Gửi thông báo\n"
                "/user - Danh sách user\n"
                "/coin - Cộng/trừ coin\n"
                "/tien - Cộng/trừ tiền"
            )
        else:
            await update.message.reply_text("⛔ Bạn không có quyền.")
        return

    elif text == "Số Dư":
        user_data = get_user(user_id)
        await update.message.reply_text(
            f"👤 **Tên:** {user.first_name}\n"
            f"🆔 **ID:** {user_id}\n"
            f"💰 **Số dư:** {user_data['balance']:,} VND\n"
            f"🪙 **Coin:** {user_data['coins']}\n"
            f"📊 **Tổng nạp:** {user_data['total_recharge']:,} VND",
            parse_mode="Markdown"
        )
        return

    elif text == "Hỗ Trợ":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Chat Admin", url="https://t.me/guncpw")]
        ])
        await update.message.reply_text("📞 Liên hệ admin để được hỗ trợ.", reply_markup=keyboard)
        return

    elif text == "Nạp Tiền":
        context.user_data["awaiting_recharge"] = True
        await update.message.reply_text(
            "💳 **NẠP TIỀN**\n"
            "Nhập số tiền (VND), tối thiểu 2.000 VND.\n"
            "Ví dụ: `20000`\n"
            "Gửi /cancel để hủy.",
            parse_mode="Markdown"
        )
        return

    else:
        await update.message.reply_text("Vui lòng chọn chức năng từ bàn phím.")

# ---- Main ----
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addlv5", addlv5_command))
    application.add_handler(CommandHandler("thongbao", thongbao_command))
    application.add_handler(CommandHandler("user", user_command))
    application.add_handler(CommandHandler("coin", coin_command))
    application.add_handler(CommandHandler("tien", tien_command))

    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == "__main__":
    main()
