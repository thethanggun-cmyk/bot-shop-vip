import discord
from discord.ext import commands
from discord.ui import Button, View, Select, Modal, TextInput
import os, threading, json, random
from flask import Flask

# --- GIỮ RENDER SỐNG ---
app = Flask('')
@app.route('/')
def home(): return "CLONE_STORE_V20_FIX"

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

# --- MODAL MUA ACC (NHẬP TỪ 1 ĐẾN 20) ---
class BuyQuantityModal(Modal):
    def __init__(self, loai, gia):
        super().__init__(title=f"MUA ACC {loai.upper()}")
        self.loai, self.gia = loai, gia
        self.quantity = TextInput(
            label='Số lượng cần mua (Ví dụ: 1-20)', 
            placeholder='Nhập số lượng acc mày muốn...', 
            min_length=1, 
            max_length=2
        )

    async def on_submit(self, interaction: discord.Interaction):
        # PHẢN HỒI NGAY ĐỂ TRÁNH LỖI ĐỎ
        await interaction.response.defer(ephemeral=True)
        
        try:
            sl = int(self.quantity.value)
            if sl <= 0: raise ValueError
        except:
            return await interaction.followup.send("❌ Nhập số lượng là số nguyên dương hộ tao cái! =))) =)))", ephemeral=True)

        data = load_data()
        tong_tien = sl * self.gia
        uid = str(interaction.user.id)
        balance = data["users_balance"].get(uid, 0)

        if balance < tong_tien:
            return await interaction.followup.send(f"❌ Nghèo thế! Thiếu {tong_tien - balance:,}đ nữa mới mua được {sl} acc nhé. =))) =)))", ephemeral=True)
        
        if len(data["stock"][self.loai]) < sl:
            return await interaction.followup.send(f"❌ Kho hiện tại chỉ còn {len(data['stock'][self.loai])} acc, không đủ {sl} cái đâu!", ephemeral=True)

        # XỬ LÝ GIAO HÀNG
        delivered = [data["stock"][self.loai].pop(0) for _ in range(sl)]
        data["users_balance"][uid] -= tong_tien
        save_data(data)

        acc_text = "\n".join([f"• `{a}`" for a in delivered])
        try:
            await interaction.user.send(f"🎁 **ĐƠN HÀNG CLONE STORE**\nLoại: {self.loai.upper()}\nSố lượng: {sl}\nTổng: {tong_tien:,}đ\n----------\n{acc_text}")
            await interaction.followup.send(f"✅ Đã bốc {sl} acc gửi vào DM cho mày rồi đó Thế! Check ngay đi. =))) =)))", ephemeral=True)
        except:
            await interaction.followup.send(f"❌ Bot bị chặn nhắn tin riêng! Acc của mày đây:\n{acc_text}", ephemeral=True)

# --- MENU CHỌN LOẠI ACC ---
class ShopMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Acc FreeFire Lv5", description="Giá: 2.000đ/1 acc", emoji="🔥", value="lv5|2000"),
            discord.SelectOption(label="Acc FreeFire Kim Cương", description="Giá: 25.000đ/1 acc", emoji="💎", value="kc|25000"),
        ]
        super().__init__(placeholder="📌 Chọn loại acc muốn mua...", options=options)

    async def callback(self, interaction: discord.Interaction):
        loai, gia = self.values[0].split("|")
        # Mở bảng nhập số lượng ngay lập tức
        await interaction.response.send_modal(BuyQuantityModal(loai, int(gia)))

# --- VIEW CỦA SHOP ---
class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ShopMenu())

    @discord.ui.button(label="Nạp tiền", style=discord.ButtonStyle.success, emoji="💳")
    async def nap(self, interaction, button):
        # Link nạp tiền PayOS của mày
        await interaction.response.send_message("👉 Link nạp PayOS: https://me.payos.vn/v2/auth/7710092008 \nNhớ nạp xong nhấn 'Tôi đã thanh toán' nhé!", ephemeral=True)

    @discord.ui.button(label="Số dư", style=discord.ButtonStyle.primary, emoji="💰")
    async def so_du(self, interaction, button):
        data = load_data()
        bal = data["users_balance"].get(str(interaction.user.id), 0)
        await interaction.response.send_message(f"💰 Số dư tài khoản: **{bal:,} VNĐ**", ephemeral=True)

@bot.command()
async def setup_shop(ctx):
    data = load_data()
    embed = discord.Embed(title="🛒 SHOP ACC CLONE TỰ ĐỘNG", description="Hệ thống bốc acc siêu tốc 24/7!", color=0x2b2d31)
    embed.add_field(name="🔥 Kho LV5:", value=f"{len(data['stock']['lv5'])} acc", inline=True)
    embed.add_field(name="💎 Kho KC:", value=f"{len(data['stock']['kc'])} acc", inline=True)
    embed.set_footer(text="Chọn danh mục bên dưới để bắt đầu mua hàng")
    await ctx.send(embed=embed, view=ShopView())

# --- LỆNH ADMIN ---
@bot.command()
@commands.has_permissions(administrator=True)
async def nhap(ctx, loai: str, *, accs: str):
    if loai not in ['kc', 'lv5']: return await ctx.send("Dùng: !nhap kc hoặc !nhap lv5")
    data = load_data()
    list_acc = [a.strip() for a in accs.split(",") if a.strip()]
    data["stock"][loai].extend(list_acc)
    save_data(data)
    await ctx.send(f"✅ Đã thêm {len(list_acc)} acc vào kho {loai.upper()} thành công!")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(os.getenv("BOT_TOKEN"))
