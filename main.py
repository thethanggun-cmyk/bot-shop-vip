import discord
from discord.ext import commands
from discord.ui import Button, View, Select
import os, threading, json, random
from flask import Flask

# --- GIỮ RENDER SỐNG ---
app = Flask('')
@app.route('/')
def home(): return "CLONE_STORE_FIX_MUA_1"

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

# --- XỬ LÝ MUA 1 ACC TRỰC TIẾP ---
class ShopMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Mua 1 Acc FF Lv5", description="Giá: 2.000đ", emoji="🔥", value="lv5|2000"),
            discord.SelectOption(label="Mua 1 Acc FF Kim Cương", description="Giá: 25.000đ", emoji="💎", value="kc|25000"),
        ]
        super().__init__(placeholder="🛒 Chọn loại acc để mua ngay...", options=options)

    async def callback(self, interaction: discord.Interaction):
        # Báo Discord đang xử lý để tránh lỗi đỏ
        await interaction.response.defer(ephemeral=True)
        
        loai, gia = self.values[0].split("|")
        gia = int(gia)
        
        data = load_data()
        uid = str(interaction.user.id)
        balance = data.get("users_balance", {}).get(uid, 0)

        if balance < gia:
            return await interaction.followup.send(f"❌ Bạn không đủ tiền. Cần {gia:,} VNĐ.", ephemeral=True)
        
        if len(data["stock"][loai]) < 1:
            return await interaction.followup.send(f"❌ Kho đã hết loại acc này.", ephemeral=True)

        # Bốc đúng 1 acc
        acc = data["stock"][loai].pop(0)
        data["users_balance"][uid] -= gia
        save_data(data)

        try:
            await interaction.user.send(f"🎁 **HÀNG CỦA BẠN:**\n• `{acc}`")
            await interaction.followup.send(f"✅ Đã mua thành công 1 acc. Check DM nhé.", ephemeral=True)
        except:
            await interaction.followup.send(f"❌ Hãy mở DM để nhận hàng. Acc của bạn: `{acc}`", ephemeral=True)

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
        bal = data.get("users_balance", {}).get(str(interaction.user.id), 0)
        await interaction.response.send_message(f"💰 Số dư của bạn: **{bal:,} VNĐ**", ephemeral=True)

@bot.command()
async def setup_shop(ctx):
    data = load_data()
    embed = discord.Embed(title="🛒 SHOP ACC TỰ ĐỘNG", color=0x00ff00)
    embed.add_field(name="🔥 Kho LV5:", value=f"{len(data['stock']['lv5'])} acc", inline=True)
    embed.add_field(name="💎 Kho KC:", value=f"{len(data['stock']['kc'])} acc", inline=True)
    await ctx.send(embed=embed, view=ShopView())

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(os.getenv("BOT_TOKEN"))
