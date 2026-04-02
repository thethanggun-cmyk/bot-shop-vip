import discord
from discord.ext import commands
from discord.ui import Button, View, Select, Modal, TextInput
import os, threading, json
from flask import Flask

# --- GIỮ RENDER SỐNG ---
app = Flask('')
@app.route('/')
def home(): return "CLONE_GUN_STORE_AUTO_DELIVERY"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- CẤU HÌNH HỆ THỐNG ---
DATA_FILE = "store_data.json"
ID_PHONG_ADMIN = 123456789012345678 # <--- THAY ID PHÒNG ADMIN VÀO ĐÂY

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f: return json.load(f)
    return {"users": {}, "stock": {"kc": [], "lv5": []}}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=4)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- MENU MUA HÀNG ---
class ShopMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Mua Acc FreeFire Lv5", description="Dùng lượt kho LV5", emoji="🔥", value="lv5"),
            discord.SelectOption(label="Mua Acc FreeFire KC", description="Dùng lượt kho KC", emoji="💎", value="kc"),
        ]
        super().__init__(placeholder="Chọn loại acc muốn lấy...", options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        data = load_data()
        user_bal = data["users"].get(user_id, {"kc": 0, "lv5": 0})
        loai = self.values[0]

        if user_bal[loai] >= 1:
            if len(data["stock"][loai]) > 0:
                # Lấy acc đầu tiên trong kho ra
                acc_info = data["stock"][loai].pop(0)
                user_bal[loai] -= 1
                data["users"][user_id] = user_bal
                save_data(data)
                
                # Gửi acc vào DM cho khách
                try:
                    await interaction.user.send(f"🎁 **ĐƠN HÀNG TỪ CLONE GUN STORE**\nLoại: {loai.upper()}\nThông tin: `{acc_info}`\nCảm ơn bạn đã ủng hộ!")
                    await interaction.response.send_message(f"✅ Đã gửi acc vào DM cho bạn! Số lượt {loai.upper()} còn lại: {user_bal[loai]}", ephemeral=True)
                except:
                    await interaction.response.send_message(f"❌ Không thể gửi DM! Hãy mở chặn tin nhắn từ người lạ. Acc của bạn: `{acc_info}`", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Hiện tại kho {loai.upper()} đang hết hàng, báo Admin Thế nhập thêm nhé!", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Bạn không đủ lượt {loai.upper()}. Hãy nạp thêm!", ephemeral=True)

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ShopMenu())

    @discord.ui.button(label="Nạp tiền", style=discord.ButtonStyle.green, emoji="💳")
    async def nap(self, interaction, button):
        # (Giữ nguyên phần Modal nạp tiền như cũ cho mày)
        await interaction.response.send_message("Nhập tiền dự kiến rồi báo Admin check bank nhé!", ephemeral=True)

    @discord.ui.button(label="Số dư kho", style=discord.ButtonStyle.blurple, emoji="📦")
    async def storage(self, interaction, button):
        data = load_data()
        bal = data["users"].get(str(interaction.user.id), {"kc": 0, "lv5": 0})
        await interaction.response.send_message(f"📦 **Kho của bạn:**\n- KC: `{bal['kc']}` lượt\n- LV5: `{bal['lv5']}` lượt", ephemeral=True)

# --- LỆNH ADMIN: ADD ACC VÀ CỘNG LƯỢT ---
@bot.command()
@commands.has_permissions(administrator=True)
async def addkc(ctx, member: discord.Member, *, acc_list: str):
    data = load_data()
    accs = [a.strip() for a in acc_list.split(",") if a.strip()]
    count = len(accs)
    
    # Thêm acc vào kho chung
    data["stock"]["kc"].extend(accs)
    # Cộng lượt cho khách
    uid = str(member.id)
    user_bal = data["users"].get(uid, {"kc": 0, "lv5": 0})
    user_bal["kc"] += count
    data["users"][uid] = user_bal
    
    save_data(data)
    await ctx.send(f"✅ Đã thêm **{count}** acc KC vào kho và cộng **{count}** lượt cho {member.mention}!")

@bot.command()
@commands.has_permissions(administrator=True)
async def addlv5(ctx, member: discord.Member, *, acc_list: str):
    data = load_data()
    accs = [a.strip() for a in acc_list.split(",") if a.strip()]
    count = len(accs)
    
    data["stock"]["lv5"].extend(accs)
    uid = str(member.id)
    user_bal = data["users"].get(uid, {"kc": 0, "lv5": 0})
    user_bal["lv5"] += count
    data["users"][uid] = user_bal
    
    save_data(data)
    await ctx.send(f"✅ Đã thêm **{count}** acc LV5 vào kho và cộng **{count}** lượt cho {member.mention}!")

@bot.command()
async def setup_shop(ctx):
    embed = discord.Embed(title="🛒 CLONE GUN STORE", description="Hệ thống tự động 100%", color=discord.Color.red())
    await ctx.send(embed=embed, view=ShopView())

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(os.getenv("BOT_TOKEN"))
