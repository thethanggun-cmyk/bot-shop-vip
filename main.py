import discord
from discord.ext import commands
from discord.ui import Button, View, Select, Modal, TextInput
import os, threading, json, random
from flask import Flask

# --- GIỮ RENDER SỐNG ---
app = Flask('')
@app.route('/')
def home(): return "CLONE_GUN_STORE_STABLE_FIX"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- CẤU HÌNH ---
ID_ADMIN_DMS = 1480239176329859195
DATA_FILE = "store_database.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"users_balance": {}, "stock": {"kc": [], "lv5": []}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- MODAL MUA ACC ---
class BuyQuantityModal(Modal):
    def __init__(self, loai, gia):
        super().__init__(title=f"MUA ACC {loai.upper()}")
        self.loai, self.gia = loai, gia
        self.quantity = TextInput(label='Số lượng mua', placeholder='Ví dụ: 1', min_length=1)

    async def on_submit(self, interaction: discord.Interaction):
        # Discord cần biết bot đang xử lý để không hiện lỗi đỏ
        await interaction.response.defer(ephemeral=True)
        try:
            sl = int(self.quantity.value)
            if sl <= 0: raise ValueError
        except:
            return await interaction.followup.send("❌ Vui lòng nhập số nguyên dương!", ephemeral=True)

        data = load_data()
        tong = sl * self.gia
        uid = str(interaction.user.id)
        balance = data["users_balance"].get(uid, 0)

        if balance < tong:
            return await interaction.followup.send(f"❌ Thiếu tiền! Cần {tong:,} VNĐ.", ephemeral=True)
        if len(data["stock"][self.loai]) < sl:
            return await interaction.followup.send(f"❌ Kho không đủ hàng!", ephemeral=True)

        acc_list = [data["stock"][self.loai].pop(0) for _ in range(sl)]
        data["users_balance"][uid] -= tong
        save_data(data)

        acc_text = "\n".join([f"• `{a}`" for a in acc_list])
        try:
            await interaction.user.send(f"🎁 **ĐƠN HÀNG CLONE STORE:**\n{acc_text}")
            await interaction.followup.send(f"✅ Đã mua {sl} acc thành công!", ephemeral=True)
        except:
            await interaction.followup.send(f"❌ Hãy mở DM để nhận acc nhé:\n{acc_text}", ephemeral=True)

# --- SELECT MENU FIX LỖI ---
class ShopMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Acc FreeFire Lv5", description="Giá: 2.000đ", emoji="🔥", value="lv5|2000"),
            discord.SelectOption(label="Acc FreeFire KC", description="Giá: 25.000đ", emoji="💎", value="kc|25000"),
        ]
        super().__init__(placeholder="📌 Chọn danh mục mua acc...", options=options)

    async def callback(self, interaction: discord.Interaction):
        # QUAN TRỌNG: Phải gọi Modal ngay lập tức ở đây
        loai, gia = self.values[0].split("|")
        await interaction.response.send_modal(BuyQuantityModal(loai, int(gia)))

# --- GIAO DIỆN CHÍNH ---
class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ShopMenu())

    @discord.ui.button(label="Nạp tiền", style=discord.ButtonStyle.success, emoji="💳")
    async def nap(self, interaction, button):
        from __main__ import NapTienModal # Tránh lỗi import vòng lặp
        await interaction.response.send_modal(NapTienModal())

    @discord.ui.button(label="Số dư", style=discord.ButtonStyle.primary, emoji="💰")
    async def so_du(self, interaction, button):
        data = load_data()
        bal = data["users_balance"].get(str(interaction.user.id), 0)
        await interaction.response.send_message(f"💰 Số dư: **{bal:,} VNĐ**", ephemeral=True)

# --- MODAL NẠP TIỀN (Giữ nguyên logic cũ) ---
class NapTienModal(Modal, title='NẠP TIỀN QUA PAYOS'):
    amount = TextInput(label='Số tiền nạp (Tối thiểu 5,000đ)', placeholder='Ví dụ: 20000', min_length=4)
    async def on_submit(self, interaction: discord.Interaction):
        so_tien = int(self.amount.value)
        order_id = random.randint(100000, 999999)
        # (Phần xử lý nạp tiền gửi DM cho admin giữ nguyên như cũ Thế nhé...)
        await interaction.response.send_message("Lệnh Nạp Đang Được Xử Lí 💵", ephemeral=True)

@bot.command()
async def setup_shop(ctx):
    data = load_data()
    embed = discord.Embed(title="🛒 HỆ THỐNG BÁN ACC TỰ ĐỘNG", description="Chào mừng đến với **Clone Store**!", color=0x2b2d31)
    embed.add_field(name="🔥 Kho LV5:", value=f"{len(data['stock']['lv5'])} acc", inline=True)
    embed.add_field(name="💎 Kho KC:", value=f"{len(data['stock']['kc'])} acc", inline=True)
    await ctx.send(embed=embed, view=ShopView())

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(os.getenv("BOT_TOKEN"))
