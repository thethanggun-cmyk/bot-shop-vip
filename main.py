import discord
from discord.ext import commands
from discord.ui import Button, View, Select, Modal, TextInput
import os, threading, json
from flask import Flask

# --- GIỮ RENDER SỐNG ---
app = Flask('')
@app.route('/')
def home(): return "CLONE_GUN_STORE_MULTI_BUY"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- QUẢN LÝ DỮ LIỆU ---
DATA_FILE = "store_pro.json"
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f: return json.load(f)
    return {"users_balance": {}, "stock": {"kc": [], "lv5": []}}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=4)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- MODAL NHẬP SỐ LƯỢNG MUA ---
class BuyQuantityModal(Modal):
    def __init__(self, loai, gia):
        super().__init__(title=f"MUA ACC {loai.upper()}")
        self.loai = loai
        self.gia = gia
        self.quantity = TextInput(label='Nhập số lượng muốn mua', placeholder='Ví dụ: 5', min_length=1, max_length=3)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            sl = int(self.quantity.value)
        except:
            return await interaction.response.send_message("❌ Vui lòng nhập số nguyên!", ephemeral=True)

        user_id = str(interaction.user.id)
        data = load_data()
        tong_tien = sl * self.gia
        user_bal = data["users_balance"].get(user_id, 0)

        if user_bal < tong_tien:
            return await interaction.response.send_message(f"❌ Thiếu tiền! {sl} acc cần {tong_tien:,}đ, bạn chỉ có {user_bal:,}đ.", ephemeral=True)
        
        if len(data["stock"][self.loai]) < sl:
            return await interaction.response.send_message(f"❌ Kho không đủ! Hiện chỉ còn {len(data['stock'][self.loai])} acc.", ephemeral=True)

        # Bốc acc ra khỏi kho
        acc_list = []
        for _ in range(sl):
            acc_list.append(data["stock"][self.loai].pop(0))
        
        data["users_balance"][user_id] -= tong_tien
        save_data(data)

        # Gửi list acc vào DM
        danh_sach_text = "\n".join([f"• `{a}`" for a in acc_list])
        try:
            await interaction.user.send(f"🎁 **ĐƠN HÀNG CLONE GUN STORE**\nLoại: {self.loai.upper()}\nSố lượng: {sl}\nTổng: {tong_tien:,}đ\n**Danh sách acc:**\n{danh_sach_text}")
            await interaction.response.send_message(f"✅ Đã gửi {sl} acc vào DM cho bạn!", ephemeral=True)
        except:
            await interaction.response.send_message(f"❌ Lỗi gửi DM! Acc của bạn: \n{danh_sach_text}", ephemeral=True)

# --- MENU CHỌN LOẠI ACC ---
class ShopMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Acc FreeFire Lv5", description="Giá: 2.000đ/acc", emoji="🔥", value="lv5|2000"),
            discord.SelectOption(label="Acc FreeFire KC", description="Giá: 25.000đ/acc", emoji="💎", value="kc|25000"),
        ]
        super().__init__(placeholder="📌 Chọn danh mục mua acc...", options=options)

    async def callback(self, interaction: discord.Interaction):
        loai, gia = self.values[0].split("|")
        await interaction.response.send_modal(BuyQuantityModal(loai, int(gia)))

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ShopMenu())
        
    @discord.ui.button(label="Nạp tiền", style=discord.ButtonStyle.success, emoji="💳")
    async def nap(self, interaction, button):
        await interaction.response.send_message("Nhắn tin cho Admin Thế để nạp tiền nhé!", ephemeral=True)

    @discord.ui.button(label="Số dư", style=discord.ButtonStyle.primary, emoji="💰")
    async def so_du(self, interaction, button):
        data = load_data()
        bal = data["users_balance"].get(str(interaction.user.id), 0)
        await interaction.response.send_message(f"💰 Số dư: **{bal:,}đ**", ephemeral=True)

@bot.command()
async def setup_shop(ctx):
    data = load_data()
    embed = discord.Embed(title="🛒 CLONE GUN STORE", description="Hệ thống bán acc tự động 100%", color=discord.Color.red())
    embed.add_field(name="🔥 Kho LV5:", value=f"{len(data['stock']['lv5'])} acc", inline=True)
    embed.add_field(name="💎 Kho KC:", value=f"{len(data['stock']['kc'])} acc", inline=True)
    await ctx.send(embed=embed, view=ShopView())

# --- LỆNH ADMIN (GIỮ NGUYÊN) ---
@bot.command()
@commands.has_permissions(administrator=True)
async def add(ctx, member: discord.Member, amount: int):
    data = load_data()
    uid = str(member.id)
    data["users_balance"][uid] = data["users_balance"].get(uid, 0) + amount
    save_data(data)
    await ctx.send(f"✅ Đã cộng **{amount:,}đ** cho {member.mention}!")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(os.getenv("BOT_TOKEN"))
