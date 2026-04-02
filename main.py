import discord
from discord.ext import commands
from discord.ui import Button, View, Select, Modal, TextInput
import os, threading, json, random
from flask import Flask

# --- GIỮ RENDER SỐNG ---
app = Flask('')
@app.route('/')
def home(): return "CLONE_STORE_NO_HOLDER_NAME"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- CẤU HÌNH ---
ID_ADMIN_DMS = 1480239176329859195
DATA_FILE = "store_database.json"
TEN_NGAN_HANG = "MB BANK" 
STK = "0356133246" 

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

# --- VIEW DUYỆT TRONG DM CỦA ADMIN ---
class AdminApproveView(discord.ui.View):
    def __init__(self, user_id, amount, order_id):
        super().__init__(timeout=None)
        self.user_id, self.amount, self.order_id = user_id, amount, order_id

    @discord.ui.button(label="Duyệt (Cộng tiền)", style=discord.ButtonStyle.success, emoji="✅")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        uid = str(self.user_id)
        data["users_balance"][uid] = data["users_balance"].get(uid, 0) + self.amount
        save_data(data)
        await interaction.response.edit_message(content=f"✅ **ĐÃ DUYỆT:** Cộng {self.amount:,}đ cho <@{self.user_id}>", embed=None, view=None)
        try:
            user = await bot.fetch_user(self.user_id)
            await user.send(f"✅ **THÀNH CÔNG:** Admin đã duyệt đơn `{self.order_id}`. Bạn được cộng **{self.amount:,} VNĐ**!")
        except: pass

    @discord.ui.button(label="Từ chối", style=discord.ButtonStyle.danger, emoji="✖️")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=f"❌ **ĐÃ TỪ CHỐI:** Đơn của <@{self.user_id}>", embed=None, view=None)

# --- MODAL NẠP TIỀN (ĐÃ BỎ TÊN CHỦ TK) ---
class NapTienModal(Modal, title='THÔNG TIN CHUYỂN KHOẢN'):
    amount = TextInput(label='Số tiền muốn nạp', placeholder='Ví dụ: 50000', min_length=4)
    async def on_submit(self, interaction: discord.Interaction):
        so_tien = int(self.amount.value)
        order_id = f"NAP{random.randint(100000, 999999)}"
        
        embed = discord.Embed(title="🏦 THÔNG TIN THANH TOÁN", color=0x5865f2)
        embed.add_field(name="🏦 Ngân hàng:", value=f"**{TEN_NGAN_HANG}**", inline=True)
        embed.add_field(name="💳 Số tài khoản:", value=f"`{STK}`", inline=False)
        embed.add_field(name="💰 Số tiền:", value=f"**{so_tien:,} VNĐ**", inline=True)
        embed.add_field(name="📝 Nội dung chuyển khoản:", value=f"`{order_id}`", inline=False)
        embed.set_footer(text="Vui lòng chuyển đúng nội dung để được duyệt nhanh nhất!")
        
        view = View()
        btn = Button(label="Tôi đã thanh toán", style=discord.ButtonStyle.success, emoji="✅")
        async def confirm_callback(inter):
            try:
                admin = await bot.fetch_user(ID_ADMIN_DMS)
                em_ad = discord.Embed(title="🔔 YÊU CẦU NẠP MỚI", color=discord.Color.yellow())
                em_ad.add_field(name="Khách:", value=f"<@{interaction.user.id}>", inline=True)
                em_ad.add_field(name="Tiền:", value=f"**{so_tien:,}đ**", inline=True)
                em_ad.add_field(name="Nội dung:", value=f"`{order_id}`", inline=False)
                await admin.send(embed=em_ad, view=AdminApproveView(interaction.user.id, so_tien, order_id))
            except: pass
            await inter.response.send_message("Lệnh nạp đã gửi đến Admin, vui lòng chờ duyệt!", ephemeral=True)
            
        btn.callback = confirm_callback
        view.add_item(btn)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# --- PHẦN MUA 1 ACC ---
class ShopMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Mua 1 Acc FF Lv5", description="Giá: 2.000đ", emoji="🔥", value="lv5|2000"),
            discord.SelectOption(label="Mua 1 Acc FF Kim Cương", description="Giá: 25.000đ", emoji="💎", value="kc|25000"),
        ]
        super().__init__(placeholder="📌 Chọn loại acc để mua ngay...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        loai, gia = self.values[0].split("|")
        gia = int(gia)
        data = load_data()
        uid = str(interaction.user.id)
        balance = data.get("users_balance", {}).get(uid, 0)

        if balance < gia:
            return await interaction.followup.send(f"❌ Bạn không đủ tiền để mua acc này.", ephemeral=True)
        if len(data["stock"][loai]) < 1:
            return await interaction.followup.send(f"❌ Kho hiện tại đã hết hàng.", ephemeral=True)

        acc = data["stock"][loai].pop(0)
        data["users_balance"][uid] -= gia
        save_data(data)

        try:
            await interaction.user.send(f"🎁 **HÀNG CỦA BẠN:**\n• `{acc}`")
            await interaction.followup.send(f"✅ Đã mua thành công 1 acc. Check DM nhé.", ephemeral=True)
        except:
            await interaction.followup.send(f"❌ Hãy mở DM nhận hàng. Acc của bạn: `{acc}`", ephemeral=True)

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ShopMenu())

    @discord.ui.button(label="Nạp tiền", style=discord.ButtonStyle.success, emoji="💳")
    async def nap(self, interaction, button):
        await interaction.response.send_modal(NapTienModal())

    @discord.ui.button(label="Số dư", style=discord.ButtonStyle.primary, emoji="💰")
    async def so_du(self, interaction, button):
        data = load_data()
        bal = data.get("users_balance", {}).get(str(interaction.user.id), 0)
        await interaction.response.send_message(f"💰 Số dư: **{bal:,} VNĐ**", ephemeral=True)

@bot.command()
async def setup_shop(ctx):
    data = load_data()
    embed = discord.Embed(title="🛒 SHOP ACC TỰ ĐỘNG", color=0x2b2d31)
    embed.add_field(name="🔥 Kho LV5:", value=f"{len(data['stock']['lv5'])} acc", inline=True)
    embed.add_field(name="💎 Kho KC:", value=f"{len(data['stock']['kc'])} acc", inline=True)
    await ctx.send(embed=embed, view=ShopView())

@bot.command()
@commands.has_permissions(administrator=True)
async def nhap(ctx, loai: str, *, accs: str):
    data = load_data()
    list_acc = [a.strip() for a in accs.split(",") if a.strip()]
    data["stock"][loai].extend(list_acc)
    save_data(data)
    await ctx.send(f"✅ Đã thêm {len(list_acc)} acc vào kho {loai}.")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(os.getenv("BOT_TOKEN"))
