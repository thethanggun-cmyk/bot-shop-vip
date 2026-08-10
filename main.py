import os
import threading
from flask import Flask, jsonify, request, send_from_directory
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__, static_folder=".")

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "ĐIỀN_TOKEN_BOT_CỦA_BẠN_VÀO_ĐÂY")
bot = telebot.TeleBot(BOT_TOKEN)

ACC_FILE = "acclv5.txt"

def ensure_file_exists():
    if not os.path.exists(ACC_FILE):
        open(ACC_FILE, "w", encoding="utf-8").close()

# ==================== BOT TELEGRAM ====================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Tạo nút bấm chuyển hướng tới Mini App
    markup = InlineKeyboardMarkup()
    btn = InlineKeyboardButton("🚀 Mở Mini App", url="https://t.me/thethanggun_bot/webapp")
    markup.add(btn)
    
    welcome_text = "👋 Chào mừng bạn đến với **Gun Store**!\nBấm vào nút bên dưới để mở Mini App và mua acc nhé!"
    bot.reply_to(message, welcome_text, parse_mode="Markdown", reply_markup=markup)

def run_bot():
    try:
        print("Bot Telegram đang lắng nghe tin nhắn...")
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print("Lỗi Bot Telegram:", e)

threading.Thread(target=run_bot, daemon=True).start()

# ==================== API FLASK ====================
@app.route("/")
def index():
    if os.path.exists("index.html"):
        return send_from_directory(".", "index.html")
    return "<h3>Lỗi: Không tìm thấy file index.html!</h3>", 404

@app.route("/get-stock", methods=["GET"])
def get_stock():
    ensure_file_exists()
    try:
        with open(ACC_FILE, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        return jsonify({"success": True, "stock": len(lines)})
    except Exception as e:
        return jsonify({"success": False, "stock": 0, "error": str(e)})

@app.route("/acclv5", methods=["POST"])
def add_acc():
    ensure_file_exists()
    data = request.json or {}
    accounts = data.get("accounts", [])
    
    if not accounts:
        return jsonify({"success": False, "message": "Không có dữ liệu acc gửi lên"}), 400
    
    try:
        with open(ACC_FILE, "a", encoding="utf-8") as f:
            for acc in accounts:
                if str(acc).strip():
                    f.write(str(acc).strip() + "\n")
        
        with open(ACC_FILE, "r", encoding="utf-8") as f:
            total = len([line.strip() for line in f if line.strip()])
            
        return jsonify({"success": True, "added_count": len(accounts), "new_stock": total})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/buy-acc", methods=["POST"])
def buy_acc():
    ensure_file_exists()
    try:
        with open(ACC_FILE, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        if not lines:
            return jsonify({"success": False, "message": "Sản phẩm đã hết hàng!"}), 400

        bought_acc = lines.pop(0)

        with open(ACC_FILE, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")

        return jsonify({"success": True, "account": bought_acc, "remaining_stock": len(lines)})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
