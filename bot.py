
import logging
import json
import os
import sqlite3
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [7021228972, 5848609177]  # asa, vivan_saikyo
CATALOG_FILE = "catalog.json"
DATABASE_FILE = "bot.db"

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Database Functions ---

def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            language TEXT DEFAULT 'en'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interest_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            series_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_user_language(user_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 'en'

def set_user_language(user_id, username, language):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, username, language) VALUES (?, ?, ?)",
                   (user_id, username, language))
    conn.commit()
    conn.close()

def log_interest(user_id, series_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO interest_log (user_id, series_id) VALUES (?, ?)", (user_id, series_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, language FROM users")
    users = cursor.fetchall()
    conn.close()
    return users

def get_active_users_last_7_days():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    seven_days_ago = datetime.now() - timedelta(days=7)
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM interest_log WHERE timestamp >= ?", (seven_days_ago,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_contact_clicks_per_series():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT series_id, COUNT(*) FROM interest_log GROUP BY series_id")
    results = cursor.fetchall()
    conn.close()
    return results

# --- Catalog Functions ---

def load_catalog():
    if not os.path.exists(CATALOG_FILE):
        return {"series": [], "vip_bundle": {"price": "25,000 MMK", "description": ""}}
    with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_catalog(catalog_data):
    with open(CATALOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(catalog_data, f, indent=2, ensure_ascii=False)

# --- Localization ---

LANGUAGES = {
    'en': {
        'welcome': "Hello there! I'm your friendly animation bot. What language would you like to use?",
        'main_menu_welcome': "Welcome to the main menu!",
        'browse_catalog': "Browse Catalog",
        'vip_bundle': "VIP Bundle",
        'how_to_purchase': "How to Purchase",
        'contact_owner': "Contact Owner",
        'change_language': "Change Language",
        'help': "Help",
        'series_details': "**{title}**\n{description}\nPrice: {price}\n[Original Post]({link})",
        'contact_to_buy': "Contact to Buy",
        'vip_details': "**VIP Bundle**\n{description}\nPrice: {price}",
        'contact_to_buy_vip': "Contact to Buy VIP",
        'purchase_steps': "**How to Purchase:**\n1. Browse our catalog and pick your favorite series.\n2. Click 'Contact to Buy' and chat with the owner (@vivan_saikyo).\n3. Make your payment via KBZPay, WavePay, or AYAPay.\n4. The owner will deliver your content!",
        'owner_contact_info': "You can contact the owner directly here: @vivan_saikyo",
        'language_changed': "Language changed to English.",
        'select_language': "Please select your preferred language:",
        'no_series_found': "No series found matching your search.",
        'search_prompt': "Please enter the series name you want to search for.",
        'full_pricing': "**Our Pricing:**\n\n",
        'admin_panel_welcome': "Welcome to the Admin Panel!",
        'add_series': "Add New Series",
        'edit_series': "Edit Existing Series",
        'remove_series': "Remove Series",
        'update_vip_price': "Update VIP Bundle Price",
        'broadcast_message': "Broadcast Message",
        'view_stats': "View Statistics",
        'export_users': "Export User List",
        'enter_series_title': "Enter series title:",
        'enter_series_description': "Enter series description:",
        'enter_series_price': "Enter series price (e.g., 5000 MMK, or 'Name your price'):",
        'enter_series_link': "Enter original channel post link:",
        'series_added': "Series '{title}' added successfully!",
        'series_not_found': "Series not found.",
        'select_series_to_edit': "Select series to edit:",
        'select_series_to_remove': "Select series to remove:",
        'series_removed': "Series '{title}' removed successfully!",
        'enter_new_vip_price': "Enter new VIP bundle price (e.g., 25000 MMK):",
        'vip_price_updated': "VIP bundle price updated to {price}.",
        'enter_broadcast_message': "Enter the message to broadcast to all users:",
        'confirm_broadcast': "Are you sure you want to broadcast this message to {user_count} users?",
        'broadcast_sent': "Message broadcasted to {user_count} users.",
        'stats_report': "**Bot Statistics:**\nTotal Users: {total_users}\nActive Users (last 7 days): {active_users}\nContact Clicks per Series:\n{series_clicks}",
        'export_success': "User list exported to users.csv.",
        'not_admin': "You are not authorized to use this command.",
        'admin_interest_notification': "User @{username} ({user_id}) is interested in {series_title}.",
        'back_to_main_menu': "Back to Main Menu",
        'back_to_admin_panel': "Back to Admin Panel",
        'cancel': "Cancel",
        'confirm': "Confirm",
        'broadcast_cancelled': "Broadcast cancelled.",
        'invalid_input': "Invalid input. Please try again."
    },
    'my': {
        'welcome': "မင်္ဂလာပါ! ကျွန်ုပ်သည် သင်၏ ဖော်ရွေသော ကာတွန်းဘော့လေး ဖြစ်ပါသည်။ မည်သည့်ဘာသာစကားကို အသုံးပြုလိုပါသလဲ?",
        'main_menu_welcome': "ပင်မ မီနူးမှ ကြိုဆိုပါသည်။",
        'browse_catalog': "ရုပ်ရှင်များ ကြည့်ရှုရန်",
        'vip_bundle': "VIP အစီအစဉ်",
        'how_to_purchase': "ဝယ်ယူနည်း",
        'contact_owner': "ပိုင်ရှင်ကို ဆက်သွယ်ရန်",
        'change_language': "ဘာသာစကား ပြောင်းရန်",
        'help': "အကူအညီ",
        'series_details': "**{title}**\n{description}\nစျေးနှုန်း: {price}\n[မူရင်းပို့စ်]({link})",
        'contact_to_buy': "ဝယ်ယူရန် ဆက်သွယ်ပါ",
        'vip_details': "**VIP အစီအစဉ်**\n{description}\nစျေးနှုန်း: {price}",
        'contact_to_buy_vip': "VIP ဝယ်ယူရန် ဆက်သွယ်ပါ",
        'purchase_steps': "**ဝယ်ယူနည်း:**\n1. ကျွန်ုပ်တို့၏ ရုပ်ရှင်များကို ကြည့်ရှုပြီး သင်နှစ်သက်ရာကို ရွေးချယ်ပါ။\n2. 'ဝယ်ယူရန် ဆက်သွယ်ပါ' ကိုနှိပ်ပြီး ပိုင်ရှင် (@vivan_saikyo) နှင့် စကားပြောပါ။\n3. KBZPay, WavePay, သို့မဟုတ် AYAPay ဖြင့် ငွေပေးချေပါ။\n4. ပိုင်ရှင်က သင့်အား ရုပ်ရှင်များ ပေးပို့ပါလိမ့်မည်။",
        'owner_contact_info': "ပိုင်ရှင်ကို ဤနေရာတွင် တိုက်ရိုက်ဆက်သွယ်နိုင်ပါသည်: @vivan_saikyo",
        'language_changed': "ဘာသာစကားကို မြန်မာသို့ ပြောင်းလဲပြီးပါပြီ။",
        'select_language': "ကျေးဇူးပြု၍ သင်နှစ်သက်ရာ ဘာသာစကားကို ရွေးချယ်ပါ။",
        'no_series_found': "သင်ရှာဖွေသော ရုပ်ရှင် မတွေ့ပါ။",
        'search_prompt': "ကျေးဇူးပြု၍ သင်ရှာဖွေလိုသော ရုပ်ရှင်အမည်ကို ရိုက်ထည့်ပါ။",
        'full_pricing': "**ကျွန်ုပ်တို့၏ စျေးနှုန်းများ:**\n\n",
        'admin_panel_welcome': "Admin Panel မှ ကြိုဆိုပါသည်။",
        'add_series': "ရုပ်ရှင်အသစ် ထည့်ရန်",
        'edit_series': "ရှိပြီးသား ရုပ်ရှင် ပြင်ဆင်ရန်",
        'remove_series': "ရုပ်ရှင် ဖျက်ရန်",
        'update_vip_price': "VIP အစီအစဉ် စျေးနှုန်း ပြင်ဆင်ရန်",
        'broadcast_message': "စာတို ပေးပို့ရန်",
        'view_stats': "စာရင်းဇယားများ ကြည့်ရန်",
        'export_users': "အသုံးပြုသူစာရင်း ထုတ်ယူရန်",
        'enter_series_title': "ရုပ်ရှင်အမည် ထည့်ပါ။",
        'enter_series_description': "ရုပ်ရှင်အကြောင်းအရာ ထည့်ပါ။",
        'enter_series_price': "ရုပ်ရှင်စျေးနှုန်း ထည့်ပါ (ဥပမာ: 5000 MMK, သို့မဟုတ် 'စျေးနှုန်းညှိနှိုင်း'):",
        'enter_series_link': "မူရင်းပို့စ်လင့်ခ် ထည့်ပါ။",
        'series_added': "'{title}' ရုပ်ရှင်ကို အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ။",
        'series_not_found': "ရုပ်ရှင် မတွေ့ပါ။",
        'select_series_to_edit': "ပြင်ဆင်ရန် ရုပ်ရှင်ကို ရွေးချယ်ပါ။",
        'select_series_to_remove': "ဖျက်ရန် ရုပ်ရှင်ကို ရွေးချယ်ပါ။",
        'series_removed': "'{title}' ရုပ်ရှင်ကို အောင်မြင်စွာ ဖျက်ပြီးပါပြီ။",
        'enter_new_vip_price': "VIP အစီအစဉ်၏ စျေးနှုန်းအသစ် ထည့်ပါ (ဥပမာ: 25000 MMK):",
        'vip_price_updated': "VIP အစီအစဉ် စျေးနှုန်းကို {price} သို့ ပြောင်းလဲပြီးပါပြီ။",
        'enter_broadcast_message': "အသုံးပြုသူအားလုံးသို့ ပေးပို့မည့် စာတိုကို ရိုက်ထည့်ပါ။",
        'confirm_broadcast': "ဤစာတိုကို အသုံးပြုသူ {user_count} ဦးထံသို့ ပေးပို့ရန် သေချာပါသလား။",
        'broadcast_sent': "စာတိုကို အသုံးပြုသူ {user_count} ဦးထံသို့ ပေးပို့ပြီးပါပြီ။",
        'stats_report': "**ဘော့ စာရင်းဇယားများ:**\nစုစုပေါင်း အသုံးပြုသူ: {total_users}\nပြီးခဲ့သည့် ၇ ရက်အတွင်း အသုံးပြုသူ: {active_users}\nရုပ်ရှင်အလိုက် ဆက်သွယ်မှုများ:\n{series_clicks}",
        'export_success': "အသုံးပြုသူစာရင်းကို users.csv သို့ ထုတ်ယူပြီးပါပြီ။",
        'not_admin': "ဤ command ကို အသုံးပြုရန် ခွင့်ပြုချက် မရှိပါ။",
        'admin_interest_notification': "အသုံးပြုသူ @{username} ({user_id}) သည် {series_title} ကို စိတ်ဝင်စားပါသည်။",
        'back_to_main_menu': "ပင်မ မီနူးသို့ ပြန်သွားရန်",
        'back_to_admin_panel': "Admin Panel သို့ ပြန်သွားရန်",
        'cancel': "ဖျက်သိမ်းရန်",
        'confirm': "အတည်ပြုရန်",
        'broadcast_cancelled': "စာတို ပေးပို့ခြင်းကို ဖျက်သိမ်းလိုက်ပါသည်။",
        'invalid_input': "ထည့်သွင်းမှု မှားယွင်းပါသည်။ ထပ်ကြိုးစားပါ။"
    }
}

def get_text(user_id, key, **kwargs):
    lang = get_user_language(user_id)
    text = LANGUAGES.get(lang, LANGUAGES['en']).get(key, LANGUAGES['en'][key])
    return text.format(**kwargs)

# --- Handlers ---

async def start(update: Update, context):
    user_id = update.effective_user.id
    username = update.effective_user.username
    set_user_language(user_id, username, 'en') # Default to English for new users

    keyboard = [
        [InlineKeyboardButton("English", callback_data="set_lang_en")],
        [InlineKeyboardButton("မြန်မာ", callback_data="set_lang_my")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(LANGUAGES['en']['welcome'], reply_markup=reply_markup)

async def set_language(update: Update, context):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.username
    lang = query.data.split('_')[-1]
    set_user_language(user_id, username, lang)
    await query.answer()
    await query.edit_message_text(text=get_text(user_id, 'language_changed'))
    await main_menu(update, context)

async def main_menu(update: Update, context):
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'browse_catalog'), callback_data="browse_catalog")],
        [InlineKeyboardButton(get_text(user_id, 'vip_bundle'), callback_data="vip_bundle")],
        [InlineKeyboardButton(get_text(user_id, 'how_to_purchase'), callback_data="how_to_purchase")],
        [InlineKeyboardButton(get_text(user_id, 'contact_owner'), url="https://t.me/vivan_saikyo")],
        [InlineKeyboardButton(get_text(user_id, 'change_language'), callback_data="change_language_menu")],
        [InlineKeyboardButton(get_text(user_id, 'help'), callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(text=get_text(user_id, 'main_menu_welcome'), reply_markup=reply_markup)
    else:
        await update.message.reply_text(get_text(user_id, 'main_menu_welcome'), reply_markup=reply_markup)

async def browse_catalog(update: Update, context):
    user_id = update.effective_user.id
    catalog = load_catalog()
    series_buttons = []
    for series in catalog['series']:
        series_buttons.append([InlineKeyboardButton(series['title'], callback_data=f"series_detail_{series['id']}")])
    series_buttons.append([InlineKeyboardButton(get_text(user_id, 'back_to_main_menu'), callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(series_buttons)
    await update.callback_query.edit_message_text(text=get_text(user_id, 'browse_catalog'), reply_markup=reply_markup)

async def series_detail(update: Update, context):
    query = update.callback_query
    user_id = query.from_user.id
    series_id = query.data.split('_')[-1]
    catalog = load_catalog()
    series = next((s for s in catalog['series'] if s['id'] == series_id), None)

    if series:
        text = get_text(user_id, 'series_details',
                        title=series['title'],
                        description=series['description'],
                        price=series['price'],
                        link=series['link'])
        keyboard = [
            [InlineKeyboardButton(get_text(user_id, 'contact_to_buy'), url="https://t.me/vivan_saikyo")],
            [InlineKeyboardButton(get_text(user_id, 'back_to_main_menu'), callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')
        log_interest(user_id, series_id)
        # Notify admins
        for admin_id in ADMIN_IDS:
            admin_username = (await context.bot.get_chat(user_id)).username or user_id
            await context.bot.send_message(chat_id=admin_id,
                                           text=get_text(admin_id, 'admin_interest_notification',
                                                         username=admin_username,
                                                         user_id=user_id,
                                                         series_title=series['title']))
    else:
        await query.edit_message_text(text=get_text(user_id, 'series_not_found'))

async def vip_bundle(update: Update, context):
    user_id = update.effective_user.id
    catalog = load_catalog()
    vip_info = catalog['vip_bundle']
    text = get_text(user_id, 'vip_details',
                    description=vip_info['description'],
                    price=vip_info['price'])
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'contact_to_buy_vip'), url="https://t.me/vivan_saikyo")],
        [InlineKeyboardButton(get_text(user_id, 'back_to_main_menu'), callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')
    log_interest(user_id, "vip_bundle")
    # Notify admins
    for admin_id in ADMIN_IDS:
        admin_username = (await context.bot.get_chat(user_id)).username or user_id
        await context.bot.send_message(chat_id=admin_id,
                                       text=get_text(admin_id, 'admin_interest_notification',
                                                     username=admin_username,
                                                     user_id=user_id,
                                                     series_title="VIP Bundle"))

async def how_to_purchase(update: Update, context):
    user_id = update.effective_user.id
    text = get_text(user_id, 'purchase_steps')
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'back_to_main_menu'), callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

async def contact_owner_menu(update: Update, context):
    user_id = update.effective_user.id
    text = get_text(user_id, 'owner_contact_info')
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'contact_owner'), url="https://t.me/vivan_saikyo")],
        [InlineKeyboardButton(get_text(user_id, 'back_to_main_menu'), callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

async def change_language_menu(update: Update, context):
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("English", callback_data="set_lang_en")],
        [InlineKeyboardButton("မြန်မာ", callback_data="set_lang_my")],
        [InlineKeyboardButton(get_text(user_id, 'back_to_main_menu'), callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(text=get_text(user_id, 'select_language'), reply_markup=reply_markup)

async def help_menu(update: Update, context):
    user_id = update.effective_user.id
    # For simplicity, help just redirects to main menu for now. Can be expanded.
    await main_menu(update, context)



async def handle_message_input(update: Update, context):
    user_id = update.effective_user.id
    current_state = context.user_data.get("state")
    admin_state = context.user_data.get("admin_state")

    if current_state == "awaiting_search_query":
        await handle_search_query(update, context)
    elif admin_state:
        await handle_admin_input(update, context)
    else:
        # Default behavior if no specific state is active
        await update.message.reply_text(get_text(user_id, 'invalid_input'))

async def search_command(update: Update, context):
    user_id = update.effective_user.id
    await update.message.reply_text(get_text(user_id, 'search_prompt'))
    context.user_data['state'] = 'awaiting_search_query'

async def handle_admin_input(update: Update, context):
    user_id = update.effective_user.id
    admin_state = context.user_data.get("admin_state")
    input_text = update.message.text

    catalog = load_catalog()

    if admin_state == 'add_series_title':
        context.user_data['new_series'] = {'id': input_text.lower().replace(' ', '_'), 'title': input_text}
        context.user_data['admin_state'] = 'add_series_description'
        await update.message.reply_text(get_text(user_id, 'enter_series_description'))
    elif admin_state == 'add_series_description':
        context.user_data['new_series']['description'] = input_text
        context.user_data['admin_state'] = 'add_series_price'
        await update.message.reply_text(get_text(user_id, 'enter_series_price'))
    elif admin_state == 'add_series_price':
        context.user_data['new_series']['price'] = input_text
        context.user_data['admin_state'] = 'add_series_link'
        await update.message.reply_text(get_text(user_id, 'enter_series_link'))
    elif admin_state == 'add_series_link':
        context.user_data['new_series']['link'] = input_text
        catalog['series'].append(context.user_data['new_series'])
        save_catalog(catalog)
        await update.message.reply_text(get_text(user_id, 'series_added', title=context.user_data['new_series']['title']))
        context.user_data['admin_state'] = None
        await admin_panel(update, context)

    elif admin_state == 'edit_series_description':
        series_id = context.user_data['current_series_id']
        for s in catalog['series']:
            if s['id'] == series_id:
                s['description'] = input_text
                break
        context.user_data['admin_state'] = 'edit_series_price'
        await update.message.reply_text(get_text(user_id, 'enter_series_price'))
    elif admin_state == 'edit_series_price':
        series_id = context.user_data['current_series_id']
        for s in catalog['series']:
            if s['id'] == series_id:
                s['price'] = input_text
                break
        context.user_data['admin_state'] = 'edit_series_link'
        await update.message.reply_text(get_text(user_id, 'enter_series_link'))
    elif admin_state == 'edit_series_link':
        series_id = context.user_data['current_series_id']
        for s in catalog['series']:
            if s['id'] == series_id:
                s['link'] = input_text
                break
        save_catalog(catalog)
        await update.message.reply_text(get_text(user_id, 'series_added', title=context.user_data['current_series_data']['title'])) # Re-using series_added text
        context.user_data['admin_state'] = None
        context.user_data['current_series_id'] = None
        context.user_data['current_series_data'] = None
        await admin_panel(update, context)

    elif admin_state == 'update_vip_price':
        catalog['vip_bundle']['price'] = input_text
        save_catalog(catalog)
        await update.message.reply_text(get_text(user_id, 'vip_price_updated', price=input_text))
        context.user_data['admin_state'] = None
        await admin_panel(update, context)

    elif admin_state == 'awaiting_broadcast_message':
        context.user_data['broadcast_message'] = input_text
        all_users = get_all_users()
        user_count = len(all_users)
        keyboard = [
            [InlineKeyboardButton(get_text(user_id, 'confirm'), callback_data="admin_broadcast_confirm")],
            [InlineKeyboardButton(get_text(user_id, 'cancel'), callback_data="admin_broadcast_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(get_text(user_id, 'confirm_broadcast', user_count=user_count), reply_markup=reply_markup)
        context.user_data['admin_state'] = 'confirming_broadcast'

    else:
        await update.message.reply_text(get_text(user_id, 'invalid_input'))



async def handle_search_query(update: Update, context):
    user_id = update.effective_user.id
    if context.user_data.get('state') == 'awaiting_search_query':
        query_text = update.message.text.lower()
        catalog = load_catalog()
        results = [s for s in catalog['series'] if query_text in s['title'].lower() or query_text in s['description'].lower()]

        if results:
            for series in results:
                text = get_text(user_id, 'series_details',
                                title=series['title'],
                                description=series['description'],
                                price=series['price'],
                                link=series['link'])
                keyboard = [
                    [InlineKeyboardButton(get_text(user_id, 'contact_to_buy'), url="https://t.me/vivan_saikyo")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(get_text(user_id, 'no_series_found'))
        context.user_data['state'] = None # Reset state
        await main_menu(update, context) # Return to main menu after search

async def prices_command(update: Update, context):
    user_id = update.effective_user.id
    catalog = load_catalog()
    pricing_text = get_text(user_id, 'full_pricing')

    for series in catalog['series']:
        pricing_text += f"- **{series['title']}**: {series['price']}\n"
    pricing_text += f"- **VIP Bundle**: {catalog['vip_bundle']['price']}\n"

    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'back_to_main_menu'), callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=pricing_text, reply_markup=reply_markup, parse_mode='Markdown')

# --- Admin Handlers ---

async def admin_check(update: Update, context):
    return update.effective_user.id in ADMIN_IDS

async def admin_panel(update: Update, context):
    if not await admin_check(update, context):
        await update.message.reply_text(get_text(update.effective_user.id, 'not_admin'))
        return

    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'add_series'), callback_data="admin_add_series")],
        [InlineKeyboardButton(get_text(user_id, 'edit_series'), callback_data="admin_edit_series_select")],
        [InlineKeyboardButton(get_text(user_id, 'remove_series'), callback_data="admin_remove_series_select")],
        [InlineKeyboardButton(get_text(user_id, 'update_vip_price'), callback_data="admin_update_vip_price")],
        [InlineKeyboardButton(get_text(user_id, 'broadcast_message'), callback_data="admin_broadcast_message")],
        [InlineKeyboardButton(get_text(user_id, 'view_stats'), callback_data="admin_view_stats")],
        [InlineKeyboardButton(get_text(user_id, 'export_users'), callback_data="admin_export_users")],
        [InlineKeyboardButton(get_text(user_id, 'back_to_main_menu'), callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(text=get_text(user_id, 'admin_panel_welcome'), reply_markup=reply_markup)
    else:
        await update.message.reply_text(get_text(user_id, 'admin_panel_welcome'), reply_markup=reply_markup)

async def admin_add_series_start(update: Update, context):
    if not await admin_check(update, context):
        return
    user_id = update.effective_user.id
    context.user_data['admin_state'] = 'add_series_title'
    await update.callback_query.edit_message_text(get_text(user_id, 'enter_series_title'))

async def admin_edit_series_select(update: Update, context):
    if not await admin_check(update, context):
        return
    user_id = update.effective_user.id
    catalog = load_catalog()
    series_buttons = []
    for series in catalog['series']:
        series_buttons.append([InlineKeyboardButton(series['title'], callback_data=f"admin_edit_series_{series['id']}")])
    series_buttons.append([InlineKeyboardButton(get_text(user_id, 'back_to_admin_panel'), callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(series_buttons)
    await update.callback_query.edit_message_text(get_text(user_id, 'select_series_to_edit'), reply_markup=reply_markup)

async def admin_edit_series_start(update: Update, context):
    if not await admin_check(update, context):
        return
    query = update.callback_query
    user_id = query.from_user.id
    series_id = query.data.split('_')[-1]
    catalog = load_catalog()
    series = next((s for s in catalog['series'] if s['id'] == series_id), None)

    if series:
        context.user_data['admin_state'] = 'edit_series_description'
        context.user_data['current_series_id'] = series_id
        context.user_data['current_series_data'] = series # Store current data for editing
        await query.edit_message_text(get_text(user_id, 'enter_series_description'))
    else:
        await query.edit_message_text(get_text(user_id, 'series_not_found'))

async def admin_remove_series_select(update: Update, context):
    if not await admin_check(update, context):
        return
    user_id = update.effective_user.id
    catalog = load_catalog()
    series_buttons = []
    for series in catalog['series']:
        series_buttons.append([InlineKeyboardButton(series['title'], callback_data=f"admin_remove_series_{series['id']}")])
    series_buttons.append([InlineKeyboardButton(get_text(user_id, 'back_to_admin_panel'), callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(series_buttons)
    await update.callback_query.edit_message_text(get_text(user_id, 'select_series_to_remove'), reply_markup=reply_markup)

async def admin_remove_series_confirm(update: Update, context):
    if not await admin_check(update, context):
        return
    query = update.callback_query
    user_id = query.from_user.id
    series_id = query.data.split('_')[-1]
    catalog = load_catalog()
    original_len = len(catalog['series'])
    catalog['series'] = [s for s in catalog['series'] if s['id'] != series_id]
    if len(catalog['series']) < original_len:
        save_catalog(catalog)
        await query.edit_message_text(get_text(user_id, 'series_removed', title=series_id))
    else:
        await query.edit_message_text(get_text(user_id, 'series_not_found'))
    await admin_panel(update, context)

async def admin_update_vip_price_start(update: Update, context):
    if not await admin_check(update, context):
        return
    user_id = update.effective_user.id
    context.user_data['admin_state'] = 'update_vip_price'
    await update.callback_query.edit_message_text(get_text(user_id, 'enter_new_vip_price'))

async def admin_broadcast_message_start(update: Update, context):
    if not await admin_check(update, context):
        return
    user_id = update.effective_user.id
    context.user_data['admin_state'] = 'awaiting_broadcast_message'
    await update.callback_query.edit_message_text(get_text(user_id, 'enter_broadcast_message'))

async def admin_view_stats(update: Update, context):
    if not await admin_check(update, context):
        return
    user_id = update.effective_user.id
    total_users = len(get_all_users())
    active_users = get_active_users_last_7_days()
    series_clicks_data = get_contact_clicks_per_series()

    series_clicks_str = ""
    for series_id, count in series_clicks_data:
        # Try to get series title from catalog, fallback to ID
        catalog = load_catalog()
        series_title = next((s['title'] for s in catalog['series'] if s['id'] == series_id), series_id)
        if series_id == "vip_bundle":
            series_title = "VIP Bundle"
        series_clicks_str += f"- {series_title}: {count}\n"

    text = get_text(user_id, 'stats_report',
                    total_users=total_users,
                    active_users=active_users,
                    series_clicks=series_clicks_str)
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'back_to_admin_panel'), callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_export_users(update: Update, context):
    if not await admin_check(update, context):
        return
    user_id = update.effective_user.id
    users = get_all_users()
    csv_content = "user_id,username,language\n"
    for uid, uname, lang in users:
        csv_content += f"{uid},{uname or ''},{lang}\n"

    with open("users.csv", "w", encoding="utf-8") as f:
        f.write(csv_content)

    await context.bot.send_document(chat_id=user_id, document=open("users.csv", "rb"),
                                    caption=get_text(user_id, 'export_success'))
    await admin_panel(update, context)



async def admin_broadcast_confirm(update: Update, context):
    if not await admin_check(update, context):
        return
    query = update.callback_query
    user_id = query.from_user.id
    broadcast_message = context.user_data.get('broadcast_message')

    if broadcast_message:
        all_users = get_all_users()
        sent_count = 0
        for user_info in all_users:
            try:
                await context.bot.send_message(chat_id=user_info[0], text=broadcast_message)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send broadcast to user {user_info[0]}: {e}")
        await query.edit_message_text(get_text(user_id, 'broadcast_sent', user_count=sent_count))
    else:
        await query.edit_message_text(get_text(user_id, 'invalid_input'))

    context.user_data['admin_state'] = None
    context.user_data['broadcast_message'] = None
    await admin_panel(update, context)

async def admin_broadcast_cancel(update: Update, context):
    if not await admin_check(update, context):
        return
    query = update.callback_query
    user_id = query.from_user.id
    await query.edit_message_text(get_text(user_id, 'broadcast_cancelled'))
    context.user_data['admin_state'] = None
    context.user_data['broadcast_message'] = None
    await admin_panel(update, context)


def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    # User commands and callbacks
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("prices", prices_command))
    application.add_handler(CallbackQueryHandler(set_language, pattern="^set_lang_.*"))
    application.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(browse_catalog, pattern="^browse_catalog$"))
    application.add_handler(CallbackQueryHandler(series_detail, pattern="^series_detail_.*"))
    application.add_handler(CallbackQueryHandler(vip_bundle, pattern="^vip_bundle$"))
    application.add_handler(CallbackQueryHandler(how_to_purchase, pattern="^how_to_purchase$"))
    application.add_handler(CallbackQueryHandler(contact_owner_menu, pattern="^contact_owner_menu$"))
    application.add_handler(CallbackQueryHandler(change_language_menu, pattern="^change_language_menu$"))
    application.add_handler(CallbackQueryHandler(help_menu, pattern="^help$"))

    # Admin commands and callbacks
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(admin_add_series_start, pattern="^admin_add_series$"))
    application.add_handler(CallbackQueryHandler(admin_edit_series_select, pattern="^admin_edit_series_select$"))
    application.add_handler(CallbackQueryHandler(admin_edit_series_start, pattern="^admin_edit_series_.*"))
    application.add_handler(CallbackQueryHandler(admin_remove_series_select, pattern="^admin_remove_series_select$"))
    application.add_handler(CallbackQueryHandler(admin_remove_series_confirm, pattern="^admin_remove_series_.*"))
    application.add_handler(CallbackQueryHandler(admin_update_vip_price_start, pattern="^admin_update_vip_price$"))
    application.add_handler(CallbackQueryHandler(admin_broadcast_message_start, pattern="^admin_broadcast_message$"))
    application.add_handler(CallbackQueryHandler(admin_view_stats, pattern="^admin_view_stats$"))
    application.add_handler(CallbackQueryHandler(admin_export_users, pattern="^admin_export_users$"))
    application.add_handler(CallbackQueryHandler(admin_broadcast_confirm, pattern="^admin_broadcast_confirm$"))
    application.add_handler(CallbackQueryHandler(admin_broadcast_cancel, pattern="^admin_broadcast_cancel$"))

    # Message handler for states (e.g., search query, admin input)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_message_input))



    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
