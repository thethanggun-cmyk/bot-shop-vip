import discord
from discord.ext import commands
from discord.ui import Button, View, Select
import os, threading
from flask import Flask

# --- GIỮ RENDER SỐNG ---
app = Flask('')
@app.route('/')
def home(): return "SHOP_BOT_ONLINE"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- CẤU HÌNH BOT ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

class ShopMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Acc FreeFire Lv5", description="Giá: 2.000đ - Kho: 10", emoji="🔥"),
            discord.SelectOption(label="Acc FreeFire KC", description="Giá: 25.000đ - Kho: 0", emoji="💎"),
        ]
        super().__init__(placeholder="Chọn sản phẩm bên dưới để mua...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Bạn đã chọn: **{self.values[0]}**. Vui lòng liên hệ Admin để thanh toán! =))) =)))", ephemeral=True)

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ShopMenu())

    @discord.ui.button(label="Nạp tiền", style=discord.ButtonStyle.green, emoji="💳")
    async def nap_tien(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👉 Nhắn tin cho Admin để nhận số tài khoản nạp tiền! =))) =)))", ephemeral=True)

    @discord.ui.button(label="Số dư", style=discord.ButtonStyle.blurple, emoji="💰")
    async def so_du(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Số dư hiện tại của bạn là: **0đ**. Vui lòng nạp thêm! =))) =)))", ephemeral=True)

@bot.command()
async def setup_shop(ctx):
    embed = discord.Embed(
        title="🛒 HỆ THỐNG BÁN ACC TỰ ĐỘNG",
        description="Chào mừng đến với **Clone Store**!\nChọn sản phẩm bên dưới để mua.",
        color=discord.Color.blue()
    )
    embed.add_field(name="🔹 Hỗ trợ:", value="Auto Bank 24/24\nBảo Hành Uy Tín Tuyệt Đối", inline=False)
    embed.set_footer(text="Cảm ơn bạn đã tin tưởng và ủng hộ!")
    
    await ctx.send(embed=embed, view=ShopView())

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(os.getenv("BOT_TOKEN"))
