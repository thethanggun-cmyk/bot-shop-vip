import os
import json
import time
from flask import Flask, jsonify, request, send_from_directory
import telebot

app = Flask(__name__, static_folder=".")

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "ĐIỀN_TOKEN_BOT_CỦA_BẠN")
bot = telebot.TeleBot(BOT_TOKEN)

MONGO_URI = os.environ.get("MONGO_URI", "")
db = None

if MONGO_URI:
    try:
        from pymongo import MongoClient
        client = MongoClient(MONGO_URI)
        db = client["gun_store"]
        print("✅ Kết nối thành công Database MongoDB Cloud!")
    except Exception as e:
        print("❌ Lỗi kết nối MongoDB:", e)

# ================= ROUTE FLASK WEB =================
@app.route("/")
def index():
    if os.path.exists("index.html"):
        return send_from_directory(".", "index.html")
    return "<h3>Lỗi: Không tìm thấy index.html</h3>", 404

@app.route("/get-user-info", methods=["GET"])
def get_user_info():
    user_id = str(request.args.get("userId", ""))
    if not user_id: return jsonify({"success": False, "balance": 0})
    
    if db is not None:
        user = db.users.find_one({"userId": user_id})
        if not user:
            db.users.insert_one({"userId": user_id, "balance": 0})
            return jsonify({"success": True, "balance": 0})
        return jsonify({"success": True, "balance": user.get("balance", 0)})
    return jsonify({"success": True, "balance": 0})

# XỬ LÝ LỆNH NẠP + GIỚI HẠN 5 LẦN / 20 PHÚT
@app.route("/request-deposit", methods=["POST"])
def request_deposit():
    data = request.json or {}
    user_id = str(data.get("userId", ""))
    user_name = data.get("userName", "Gun")
    amount = int(data.get("amount", 0))

    now = time.time()
    twenty_mins_ago = now - 1200  # 20 phút = 1200 giây

    if db is not None:
        # Kiểm tra nếu trong 20 phút qua user tạo >= 5 lệnh nạp
        recent_count = db.deposits.count_documents({
            "userId": user_id,
            "timestamp": {"$gte": twenty_mins_ago}
        })

        if recent_count >= 5:
            return jsonify({
                "success": False, 
                "message": "⚠️ Bạn đã tạo 5 lệnh nạp trong 20 phút! Vui lòng đợi hết 20 phút để tạo tiếp."
            }), 400

        dep_obj = {
            "id": int(now * 1000),
            "userId": user_id,
            "userName": user_name,
            "amount": amount,
            "status": "pending",
            "time": time.strftime("%H:%M - %d/%m/%Y"),
            "timestamp": now
        }
        db.deposits.insert_one(dep_obj)
        return jsonify({"success": True, "message": "Đã gửi yêu cầu nạp tiền!"})

    return jsonify({"success": False, "message": "Lỗi Database!"}), 500

# LẤY LỊCH SỬ NẠP CỦA USER (TỰ XÓA/ẨN CÁC LỆNH WAITING QUÁ 20 PHÚT)
@app.route("/get-deposit-history", methods=["GET"])
def get_deposit_history():
    user_id = str(request.args.get("userId", ""))
    twenty_mins_ago = time.time() - 1200

    if db is not None:
        # Lấy tất cả lệnh đã duyệt HOẶC lệnh pending còn dưới 20 phút
        query = {
            "userId": user_id,
            "$or": [
                {"status": "approved"},
                {"status": "pending", "timestamp": {"$gte": twenty_mins_ago}}
            ]
        }
        items = list(db.deposits.find(query, {"_id": 0}).sort("timestamp", -1))
        return jsonify({"success": True, "deposits": items})

    return jsonify({"success": True, "deposits": []})

# GIỮ NGUYÊN TẤT CẢ CÁC LỆNH NẠP CHO ADMIN (DÙ QUÁ 20 PHÚT VẪN KHÔNG XÓA)
@app.route("/admin/get-deposits", methods=["GET"])
def admin_get_deposits():
    if db is not None:
        items = list(db.deposits.find({"status": "pending"}, {"_id": 0}).sort("timestamp", -1))
        return jsonify({"success": True, "deposits": items})
    return jsonify({"success": True, "deposits": []})

# ADMIN DUYỆT CỘNG TIỀN
@app.route("/admin/approve-deposit", methods=["POST"])
def admin_approve_deposit():
    data = request.json or {}
    dep_id = data.get("depositId")

    if db is not None:
        target = db.deposits.find_one({"id": dep_id})
        if not target or target.get("status") != "pending":
            return jsonify({"success": False, "message": "Không tìm thấy lệnh!"}), 400

        db.deposits.update_one({"id": dep_id}, {"$set": {"status": "approved"}})
        uid = target["userId"]
        amt = target["amount"]
        db.users.update_one({"userId": uid}, {"$inc": {"balance": amt}}, upsert=True)

        return jsonify({"success": True, "message": f"Đã duyệt +{amt:,}đ cho ID {uid}!"})

    return jsonify({"success": False, "message": "Lỗi Database!"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
