import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from typing import Optional

# Setup bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# File untuk menyimpan data
DATA_FILE = "store_data.json"

# Load data dari file
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"categories": [], "items": [], "rates": {}}

# Save data ke file
def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Format harga ke Rupiah
def format_rupiah(amount):
    return f"Rp {amount:,.0f}".replace(",", ".")

# Hitung harga berdasarkan rate
def calculate_price(value, rate):
    try:
        return float(value) * float(rate)
    except:
        return 0

# Generate embed untuk price list
def generate_embed(data):
    embed = discord.Embed(
        title="📋 Price List Toko",
        description="Daftar harga semua item yang tersedia",
        color=discord.Color.green()
    )
    
    # Group items by category
    items_by_category = {}
    for item in data["items"]:
        category = item.get("category", "Uncategorized")
        if category not in items_by_category:
            items_by_category[category] = []
        items_by_category[category].append(item)
    
    # Add fields for each category
    for category, items in items_by_category.items():
        field_value = ""
        for item in items:
            item_name = item["name"]
            value = item["value"]
            value_name = item.get("value_name", "")
            rate = data["rates"].get(item.get("rate_key", "default"), 1)
            
            total_price = calculate_price(value, rate)
            
            if value_name:
                field_value += f"• **{item_name}**\n"
                field_value += f"  {value} {value_name} × {rate} ≈ {format_rupiah(total_price)}\n"
            else:
                field_value += f"• **{item_name}**\n"
                field_value += f"  {value} × {rate} ≈ {format_rupiah(total_price)}\n"
        
        if field_value:
            embed.add_field(
                name=f"📁 {category}",
                value=field_value,
                inline=False
            )
    
    embed.set_footer(text="Gunakan /help untuk menambah atau mengedit item")
    return embed

@bot.event
async def on_ready():
    print(f'✅ Bot sudah online sebagai {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} command tersinkronisasi")
    except Exception as e:
        print(f"❌ Error: {e}")

# Command: /add
@bot.tree.command(name="add", description="Tambah item baru ke price list")
@app_commands.describe(
    name="Nama item",
    value="Value/nilai item (contoh: 499 untuk 499 robux)",
    value_name="Nama value (opsional, contoh: 'robux')",
    rate_key="Key rate yang dipakai (opsional, default: 'default')",
    category="Kategori item (opsional)"
)
async def add_item(
    interaction: discord.Interaction,
    name: str,
    value: str,
    value_name: Optional[str] = "",
    rate_key: Optional[str] = "default",
    category: Optional[str] = "Uncategorized"
):
    data = load_data()
    
    # Cek apakah item sudah ada
    for item in data["items"]:
        if item["name"].lower() == name.lower() and item.get("category", "Uncategorized") == category:
            await interaction.response.send_message(f"❌ Item '{name}' sudah ada di kategori '{category}'!", ephemeral=True)
            return
    
    # Tambah item baru
    new_item = {
        "name": name,
        "value": value,
        "value_name": value_name,
        "rate_key": rate_key,
        "category": category
    }
    
    data["items"].append(new_item)
    
    # Tambah kategori jika belum ada
    if category not in data["categories"]:
        data["categories"].append(category)
    
    save_data(data)
    
    # Generate preview
    rate = data["rates"].get(rate_key, 1)
    total_price = calculate_price(value, rate)
    
    preview = f"✅ Item ditambahkan!\n\n"
    preview += f"**{name}**\n"
    if value_name:
        preview += f"{value} {value_name} × {rate} ≈ {format_rupiah(total_price)}"
    else:
        preview += f"{value} × {rate} ≈ {format_rupiah(total_price)}"
    
    await interaction.response.send_message(preview, ephemeral=True)

# Command: /value
@bot.tree.command(name="value", description="Set value untuk item yang sudah ada")
@app_commands.describe(
    item_name="Nama item yang akan diubah",
    new_value="Value baru",
    category="Kategori item (opsional)"
)
async def set_value(
    interaction: discord.Interaction,
    item_name: str,
    new_value: str,
    category: Optional[str] = "Uncategorized"
):
    data = load_data()
    
    # Cari item
    found = False
    for item in data["items"]:
        if item["name"].lower() == item_name.lower() and item.get("category", "Uncategorized") == category:
            item["value"] = new_value
            found = True
            break
    
    if found:
        save_data(data)
        await interaction.response.send_message(f"✅ Value untuk '{item_name}' diubah menjadi {new_value}", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Item '{item_name}' tidak ditemukan di kategori '{category}'", ephemeral=True)

# Command: /rate
@bot.tree.command(name="rate", description="Set rate untuk kalkulasi harga")
@app_commands.describe(
    rate_key="Key/nama untuk rate ini (contoh: 'roblox', 'ml')",
    rate_value="Nilai rate (contoh: 70, 14300)"
)
async def set_rate(interaction: discord.Interaction, rate_key: str, rate_value: str):
    data = load_data()
    
    try:
        rate_float = float(rate_value)
        data["rates"][rate_key] = rate_float
        save_data(data)
        
        # Hitung ulang semua item yang pakai rate ini
        items_updated = 0
        for item in data["items"]:
            if item.get("rate_key") == rate_key:
                items_updated += 1
        
        await interaction.response.send_message(
            f"✅ Rate '{rate_key}' diset ke {rate_float}\n"
            f"📊 {items_updated} item akan terupdate di price list",
            ephemeral=True
        )
    except ValueError:
        await interaction.response.send_message("❌ Rate value harus angka!", ephemeral=True)

# Command: /category
@bot.tree.command(name="category", description="Tampilkan atau tambah kategori")
async def category_list(interaction: discord.Interaction):
    data = load_data()
    
    if data["categories"]:
        categories_list = "\n".join([f"• {cat}" for cat in data["categories"]])
        embed = discord.Embed(
            title="📁 Daftar Kategori",
            description=categories_list,
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Total Kategori",
            value=str(len(data["categories"])),
            inline=True
        )
        embed.add_field(
            name="Total Item",
            value=str(len(data["items"])),
            inline=True
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message("📭 Belum ada kategori. Gunakan /add untuk membuat kategori baru.", ephemeral=True)

# Command: /del
@bot.tree.command(name="del", description="Hapus item dari price list")
@app_commands.describe(
    item_name="Nama item yang akan dihapus",
    category="Kategori item (opsional)"
)
async def delete_item(
    interaction: discord.Interaction,
    item_name: str,
    category: Optional[str] = "Uncategorized"
):
    data = load_data()
    
    # Cari dan hapus item
    initial_count = len(data["items"])
    data["items"] = [
        item for item in data["items"] 
        if not (item["name"].lower() == item_name.lower() and item.get("category", "Uncategorized") == category)
    ]
    
    if len(data["items"]) < initial_count:
        save_data(data)
        await interaction.response.send_message(f"✅ Item '{item_name}' berhasil dihapus dari kategori '{category}'", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Item '{item_name}' tidak ditemukan di kategori '{category}'", ephemeral=True)

# Command: /pricelist
@bot.tree.command(name="pricelist", description="Tampilkan price list")
async def show_pricelist(interaction: discord.Interaction):
    data = load_data()
    
    if not data["items"]:
        await interaction.response.send_message("📭 Price list masih kosong. Gunakan /add untuk menambah item.", ephemeral=True)
        return
    
    embed = generate_embed(data)
    await interaction.response.send_message(embed=embed)

# Command: /clearall (hati-hati!)
@bot.tree.command(name="clearall", description="HAPUS SEMUA DATA! Hanya untuk emergency")
async def clear_all(interaction: discord.Interaction):
    # Buat confirmation button
    class ConfirmView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
        
        @discord.ui.button(label="Ya, Hapus Semua", style=discord.ButtonStyle.danger)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            # Reset data
            empty_data = {"categories": [], "items": [], "rates": {}}
            save_data(empty_data)
            await interaction.response.send_message("✅ Semua data telah dihapus!", ephemeral=True)
            self.stop()
        
        @discord.ui.button(label="Batal", style=discord.ButtonStyle.secondary)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("❌ Dibatalkan.", ephemeral=True)
            self.stop()
    
    embed = discord.Embed(
        title="⚠️ PERINGATAN!",
        description="Anda akan menghapus **SEMUA DATA** termasuk:\n• Semua item\n• Semua kategori\n• Semua rate\n\n**Tindakan ini tidak dapat dibatalkan!**",
        color=discord.Color.red()
    )
    
    await interaction.response.send_message(embed=embed, view=ConfirmView(), ephemeral=True)

# Command: /help
@bot.tree.command(name="help", description="Tampilkan panduan penggunaan bot")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Panduan Bot Price List",
        description="Bot untuk mengatur price list jualan dengan sistem rate",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="📝 **/add**",
        value="Tambah item baru\n"
              "`name:` Nama item\n"
              "`value:` Nilai item (contoh: 499)\n"
              "`value_name:` Opsional (contoh: 'robux')\n"
              "`rate_key:` Opsional, default 'default'\n"
              "`category:` Opsional",
        inline=False
    )
    
    embed.add_field(
        name="💰 **/rate**",
        value="Set rate untuk perhitungan\n"
              "`rate_key:` Nama rate (contoh: 'roblox')\n"
              "`rate_value:` Nilai rate (contoh: 70)",
        inline=False
    )
    
    embed.add_field(
        name="📁 **/category**",
        value="Lihat daftar kategori yang ada",
        inline=False
    )
    
    embed.add_field(
        name="❌ **/del**",
        value="Hapus item dari price list\n"
              "`item_name:` Nama item\n"
              "`category:` Opsional",
        inline=False
    )
    
    embed.add_field(
        name="📋 **/pricelist**",
        value="Tampilkan price list lengkap",
        inline=False
    )
    
    embed.add_field(
        name="📊 **/value**",
        value="Ubah value item yang sudah ada",
        inline=False
    )
    
    embed.add_field(
        name="💡 Contoh Penggunaan",
        value="1. Set rate Roblox: `/rate roblox 70`\n"
              "2. Tambah item: `/add name:"VIP" value:499 value_name:robux rate_key:roblox category:Roblox`\n"
              "3. Lihat hasil: `/pricelist`",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Command: /edit (opsional)
@bot.tree.command(name="edit", description="Edit item yang sudah ada")
@app_commands.describe(
    old_name="Nama item lama",
    new_name="Nama item baru",
    category="Kategori item (opsional)"
)
async def edit_item(
    interaction: discord.Interaction,
    old_name: str,
    new_name: str,
    category: Optional[str] = "Uncategorized"
):
    data = load_data()
    
    found = False
    for item in data["items"]:
        if item["name"].lower() == old_name.lower() and item.get("category", "Uncategorized") == category:
            item["name"] = new_name
            found = True
            break
    
    if found:
        save_data(data)
        await interaction.response.send_message(f"✅ Item '{old_name}' diubah menjadi '{new_name}'", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Item '{old_name}' tidak ditemukan", ephemeral=True)

# Run bot
TOKEN = os.getenv("DISCORD_TOKEN")  # Untuk Replit, set di Secrets
if not TOKEN:
    # Jika local, masukkan token di sini
    TOKEN = "YOUR_BOT_TOKEN_HERE"  # Ganti dengan token botmu

bot.run(TOKEN)
