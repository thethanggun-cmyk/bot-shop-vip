import os
from flask import Flask, jsonify, request, send_from_file

app = Flask(__name__, static_folder=".")

ACC_FILE = "acclv5.txt"

def ensure_file_exists():
    if not os.path.exists(ACC_FILE):
        open(ACC_FILE, "w", encoding="utf-8").close()

@app.route("/")
def index():
    return send_from_file(".", "index.html")

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
        
        # Đếm lại kho sau khi thêm
        with open(ACC_FILE, "r", encoding="utf-8") as f:
            total = len([line.strip() for line in f if line.strip()])
            
        return jsonify({"success": True, "added_count": len(accounts), "new_stock": total})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
