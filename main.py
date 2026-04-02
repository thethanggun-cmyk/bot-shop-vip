import discord
from discord.ext import commands
from discord.ui import Button, View, Select, Modal, TextInput
import os, threading, json, random
from flask import Flask

# --- GIỮ RENDER SỐNG ---
app = Flask('')
@app.route('/')
def home(): return "CLONE_STORE_ULTRA_SPEED"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- CẤU HÌNH ---
ID_ADMIN_DMS = 1480239176329859195 # ID của mày
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

# --- MODAL MUA HÀNG (FIX TIMEOUT) ---
class BuyQuantityModal(Modal):
    def __init__(self, loai, gia):
        super().__init__(title=f"MUA ACC {loai.upper()}")
        self.loai, self.gia = loai, gia
        self.quantity = TextInput(label='Số lượng mua (1-20)', placeholder='Ví dụ: 5', min_length=1, max_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        # THẦN CHÚ: Báo Discord "Tao đang làm" ngay lập tức để không hiện chữ đỏ
        await interaction.response.defer(ephemeral=True)
        
        try:
            sl = int(self.quantity.value)
            if sl <= 0: raise ValueError
        except:
            return await interaction.followup.send("❌ Nhập số lượng là số nguyên dương.", ephemeral=True)

        data = load_data()
        tong = sl * self.gia
        uid = str(interaction.user.id)
        balance = data.get("users_balance", {}).get(uid, 0)

        if balance < tong:
            return await interaction.followup.send(f"❌ Thiếu {tong - balance:,}đ.", ephemeral=True)
        if len(data["stock"][self.loai]) < sl:
            return await interaction.followup.send(f"❌ Kho không đủ {sl} acc.", ephemeral=True)

        # Trừ tiền và bốc acc
        acc_list = [data["stock"][self.loai].pop(0) for _ in range(sl)]
        data["users_balance"][uid] -= tong
        save_data(data)

        acc_text = "\n".join([f"• `{a}`" for a in acc_list])
        try:
            await interaction.user.send(f"🎁 **HÀNG CỦA BẠN:**\n{acc_text}")
            await interaction.followup.send(f"✅ Đã gửi {sl} acc vào DM.", ephemeral=True)
        except:
            await interaction.followup.send(f"❌ Mở DM để nhận hàng nhé:\n{acc_text}", ephemeral=True)

# --- MENU VỚI PHẢN HỒI TỨC THÌ ---
class ShopMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Acc FF Lv5", description="2.000đ/acc", emoji="🔥", value="lv5|2000"),
            discord.SelectOption(label="Acc FF Kim Cương", description="25.000đ/acc", emoji="💎", value="kc|25000"),
        ]
        super().__init__(placeholder="📌 Chọn loại acc muốn mua...", options=options)

    async def callback(self, interaction: discord.Interaction):
        loai, gia = self.values[0].split("|")
        # Gửi bảng nhập số lượng ngay giây đầu tiên
        await interaction.response.send_modal(BuyQuantityModal(loai, int(gia)))

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ShopMenu())

    @discord.ui.button(label="Nạp tiền", style=discord.ButtonStyle.success, emoji="💳")
    async def nap(self, interaction, button):
        await interaction.response.send_message("👉 Link nạp: https://me.payos.vn/v2/auth/7710092008", ephemeral=True)

    @discord.ui.button(label="Số dư", style=discord.ButtonStyle.primary, emoji="💰")
    async def so_du(self, interaction, button):
        data = load_data()
        bal = data["users_balance"].get(str(interaction.user.id), 0)
        await interaction.response.send_message(f"💰 Số dư: **{bal:,} VNĐ**", ephemeral=True)

@bot.command()
async def setup_shop(ctx):
    data = load_data()
    embed = discord.Embed(title="🛒 SHOP ACC TỰ ĐỘNG", color=0x2b2d31)
    embed.add_field(name="🔥 Kho LV5:", value=f"{len(data['stock']['lv5'])} acc", inline=True)
    embed.add_field(name="💎 Kho KC:", value=f"{len(data['stock']['kc'])} acc", inline=True)
    await ctx.send(embed=embed, view=ShopView())

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(os.getenv("BOT_TOKEN"))
