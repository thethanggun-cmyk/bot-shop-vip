import discord
from discord.ext import commands
from discord.ui import Button, View, Select, Modal, TextInput
import os, threading, json
from flask import Flask

# --- GIỮ RENDER SỐNG ---
app = Flask('')
@app.route('/')
def home(): return "CLONE_GUN_STORE_WAREHOUSE"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- QUẢN LÝ DỮ LIỆU (Tiền và Kho Acc) ---
DATA_FILE = "store_pro.json"
ID_PHONG_ADMIN = 123456789012345678 # <--- THAY ID PHÒNG ADMIN CỦA MÀY

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f: return json.load(f)
    return {"users_balance": {}, "stock": {"kc": [], "lv5": []}}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=4)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- MENU CHỌN MUA (TỰ ĐỘNG BỐC ACC TRONG KHO) ---
class ShopMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Acc FreeFire Lv5", description="Giá: 2.000đ", emoji="🔥", value="lv5|2000"),
            discord.SelectOption(label="Acc FreeFire KC", description="Giá: 25.000đ", emoji="💎", value="kc|25000"),
        ]
        super().__init__(placeholder="📌 Chọn danh mục mua acc...", options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        data = load_data()
        loai, gia = self.values[0].split("|")
        gia = int(gia)
        
        user_balance = data["users_balance"].get(user_id, 0)

        if user_balance >= gia:
            if len(data["stock"][loai]) > 0:
                # Bốc acc đầu hàng đợi
                acc_lay_duoc = data["stock"][loai].pop(0)
                data["users_balance"][user_id] -= gia
                save_data(data)
                
                try:
                    await interaction.user.send(f"🎁 **ĐƠN HÀNG TỪ CLONE GUN STORE**\nLoại: {loai.upper()}\nAcc: `{acc_lay_duoc}`\nSố dư còn lại: {data['users_balance'][user_id]:,}đ")
                    await interaction.response.send_message(f"✅ Đã mua thành công! Acc đã được gửi vào DM của bạn.", ephemeral=True)
                except:
                    await interaction.response.send_message(f"❌ Hãy mở DM (tin nhắn riêng) để bot gửi acc! Acc của bạn là: `{acc_lay_duoc}`", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Kho {loai.upper()} hiện đang hết hàng!", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Bạn không đủ tiền! Cần thêm {gia - user_balance:,}đ.", ephemeral=True)

# --- GIAO DIỆN NẠP TIỀN & SỐ DƯ ---
class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ShopMenu())

    @discord.ui.button(label="Nạp tiền", style=discord.ButtonStyle.success, emoji="💳")
    async def nap(self, interaction, button):
        # Hiển thị STK nạp tiền (Như các bản trước)
        embed = discord.Embed(title="💳 NẠP TIỀN QUA BANK", description="Chuyển khoản theo thông tin bên dưới", color=0x00ff00)
        embed.add_field(name="🏦 MB BANK", value="`7710092008`", inline=False)
        embed.add_field(name="📝 Nội dung:", value=f"`NAP {interaction.user.id}`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Số dư", style=discord.ButtonStyle.primary, emoji="💰")
    async def so_du(self, interaction, button):
        data = load_data()
        bal = data["users_balance"].get(str(interaction.user.id), 0)
        await interaction.response.send_message(f"💰 Số dư của bạn: **{bal:,}đ**", ephemeral=True)

# --- LỆNH ADMIN NHẬP KHO (Dán 1 đống acc vào đây) ---
@bot.command()
@commands.has_permissions(administrator=True)
async def nhap_kc(ctx, *, danh_sach_acc: str):
    data = load_data()
    accs = [a.strip() for a in danh_sach_acc.split(",") if a.strip()]
    data["stock"]["kc"].extend(accs)
    save_data(data)
    await ctx.send(f"✅ Đã nhập thêm **{len(accs)}** acc vào kho Kim Cương!")

@bot.command()
@commands.has_permissions(administrator=True)
async def nhap_lv5(ctx, *, danh_sach_acc: str):
    data = load_data()
    accs = [a.strip() for a in danh_sach_acc.split(",") if a.strip()]
    data["stock"]["lv5"].extend(accs)
    save_data(data)
    await ctx.send(f"✅ Đã nhập thêm **{len(accs)}** acc vào kho Level 5!")

@bot.command()
@commands.has_permissions(administrator=True)
async def add(ctx, member: discord.Member, amount: int):
    data = load_data()
    uid = str(member.id)
    data["users_balance"][uid] = data["users_balance"].get(uid, 0) + amount
    save_data(data)
    await ctx.send(f"✅ Đã nạp **{amount:,}đ** cho {member.mention}!")

@bot.command()
async def setup_shop(ctx):
    data = load_data()
    embed = discord.Embed(title="🛒 CLONE GUN STORE", description="Hệ thống tự động bốc acc từ kho", color=discord.Color.red())
    embed.add_field(name="🔥 Kho LV5:", value=f"{len(data['stock']['lv5'])} acc", inline=True)
    embed.add_field(name="💎 Kho KC:", value=f"{len(data['stock']['kc'])} acc", inline=True)
    await ctx.send(embed=embed, view=ShopView())

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(os.getenv("BOT_TOKEN"))
