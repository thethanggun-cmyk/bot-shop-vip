import discord
from discord.ext import commands
from discord.ui import Button, View, Select, Modal, TextInput
import os, threading, json, random
from flask import Flask

# --- GIỮ RENDER SỐNG ---
app = Flask('')
@app.route('/')
def home(): return "CLONE_GUN_STORE_DM_APPROVE"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- CẤU HÌNH ---
ID_ADMIN_DMS = 1480239176329859195  # ID của mày đã dán ở đây
DATA_FILE = "store_pro.json"

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
        self.user_id = user_id
        self.amount = amount
        self.order_id = order_id

    @discord.ui.button(label="Duyệt (Cộng tiền)", style=discord.ButtonStyle.success, emoji="✅")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        uid = str(self.user_id)
        data["users_balance"][uid] = data["users_balance"].get(uid, 0) + self.amount
        save_data(data)

        await interaction.response.edit_message(content=f"✅ **ĐÃ DUYỆT:** Đã cộng {self.amount:,} VNĐ cho khách <@{self.user_id}>", embed=None, view=None)
        
        try:
            khach = await bot.fetch_user(self.user_id)
            await khach.send(f"✅ **THÀNH CÔNG:** Admin đã duyệt hóa đơn `{self.order_id}`. Bạn đã được cộng **{self.amount:,} VNĐ**!")
        except: pass

    @discord.ui.button(label="Từ chối", style=discord.ButtonStyle.danger, emoji="✖️")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=f"❌ **ĐÃ TỪ CHỐI:** Đơn nạp của khách <@{self.user_id}>", embed=None, view=None)

# --- MODAL NẠP TIỀN CHO KHÁCH ---
class NapTienModal(Modal, title='NẠP TIỀN QUA PAYOS'):
    amount = TextInput(label='Số tiền cần nạp (Tối thiểu 5,000đ)', placeholder='Ví dụ: 20000', min_length=4)

    async def on_submit(self, interaction: discord.Interaction):
        so_tien = int(self.amount.value)
        order_id = random.randint(100000, 999999)
        
        embed = discord.Embed(title="💳 Nạp tiền PayOS", color=0x5865f2)
        embed.add_field(name="💰 Số tiền:", value=f"**{so_tien:,} VNĐ**", inline=False)
        embed.add_field(name="🆔 Order:", value=f"`{order_id}`", inline=False)
        embed.add_field(name="⏳ Trạng thái:", value="🟡 Chờ thanh toán", inline=False)
        embed.add_field(name="🔗 Link thanh toán:", value=f"[Nhấn vào đây để thanh toán](https://me.payos.vn/v2/auth/7710092008)", inline=False)
        
        view = View()
        btn = Button(label="Tôi đã thanh toán", style=discord.ButtonStyle.success, emoji="✅")
        
        async def confirm_callback(inter):
            try:
                admin_user = await bot.fetch_user(ID_ADMIN_DMS)
                embed_ad = discord.Embed(title="🔔 CÓ YÊU CẦU NẠP TIỀN", color=discord.Color.yellow())
                embed_ad.add_field(name="Khách:", value=f"<@{interaction.user.id}>", inline=True)
                embed_ad.add_field(name="Số tiền:", value=f"**{so_tien:,}đ**", inline=True)
                embed_ad.add_field(name="Mã đơn:", value=f"`{order_id}`", inline=False)
                await admin_user.send(embed=embed_ad, view=AdminApproveView(interaction.user.id, so_tien, order_id))
            except: print("Lỗi gửi DM Admin")
            
            await inter.response.send_message("Lệnh Nạp Đang Được Xử Lí 💵", ephemeral=True)
            
        btn.callback = confirm_callback
        view.add_item(btn)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# --- PHẦN MUA ACC & GIAO DIỆN CHÍNH ---
class BuyQuantityModal(Modal):
    def __init__(self, loai, gia):
        super().__init__(title=f"MUA ACC {loai.upper()}")
        self.loai, self.gia = loai, gia
        self.quantity = TextInput(label='Số lượng mua', placeholder='Ví dụ: 1', min_length=1)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        sl = int(self.quantity.value)
        data = load_data()
        tong = sl * self.gia
        uid = str(interaction.user.id)
        balance = data["users_balance"].get(uid, 0)

        if balance < tong:
            return await interaction.followup.send(f"❌ Bạn thiếu {tong - balance:,}đ!", ephemeral=True)
        if len(data["stock"][self.loai]) < sl:
            return await interaction.followup.send(f"❌ Kho không đủ!", ephemeral=True)

        acc_list = [data["stock"][self.loai].pop(0) for _ in range(sl)]
        data["users_balance"][uid] -= tong
        save_data(data)

        try:
            await interaction.user.send(f"🎁 **ACC CLONE GUN STORE:**\n" + "\n".join([f"`{a}`" for a in acc_list]))
            await interaction.followup.send(f"✅ Đã gửi {sl} acc vào DM!", ephemeral=True)
        except:
            await interaction.followup.send(f"❌ Mở DM nhận acc: " + ", ".join(acc_list), ephemeral=True)

class ShopMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Acc FreeFire Lv5", description="Giá: 2.000đ", emoji="🔥", value="lv5|2000"),
            discord.SelectOption(label="Acc FreeFire KC", description="Giá: 25.000đ", emoji="💎", value="kc|25000"),
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
        await interaction.response.send_modal(NapTienModal())

    @discord.ui.button(label="Số dư", style=discord.ButtonStyle.primary, emoji="💰")
    async def so_du(self, interaction, button):
        data = load_data()
        bal = data["users_balance"].get(str(interaction.user.id), 0)
        await interaction.response.send_message(f"💰 Số dư: **{bal:,} VNĐ**", ephemeral=True)

@bot.command()
async def setup_shop(ctx):
    data = load_data()
    embed = discord.Embed(title="🛒 HỆ THỐNG BÁN ACC TỰ ĐỘNG", description="Chào mừng đến với **Clone Gun Store**!", color=0x2b2d31)
    embed.add_field(name="🔥 Kho LV5:", value=f"{len(data['stock']['lv5'])} acc", inline=True)
    embed.add_field(name="💎 Kho KC:", value=f"{len(data['stock']['kc'])} acc", inline=True)
    await ctx.send(embed=embed, view=ShopView())

@bot.command()
@commands.has_permissions(administrator=True)
async def nhap_kc(ctx, *, accs: str):
    data = load_data()
    list_acc = [a.strip() for a in accs.split(",") if a.strip()]
    data["stock"]["kc"].extend(list_acc)
    save_data(data)
    await ctx.send(f"✅ Đã thêm {len(list_acc)} acc KC.")

@bot.command()
@commands.has_permissions(administrator=True)
async def add(ctx, member: discord.Member, amount: int):
    data = load_data()
    data["users_balance"][str(member.id)] = data["users_balance"].get(str(member.id), 0) + amount
    save_data(data)
    await ctx.send(f"✅ Đã cộng {amount:,}đ cho {member.mention}!")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(os.getenv("BOT_TOKEN"))
