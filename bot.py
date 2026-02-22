import telebot
from telebot import types
import sqlite3
import random
from datetime import datetime, timedelta
import time

# НОВЫЙ ТОКЕН
TOKEN = '8561596225:AAHlM8q5mVRamck9oASQjL52v_AxcTqPzGI'
bot = telebot.TeleBot(TOKEN)

# ID админа - УБЕДИСЬ, ЧТО ЭТО ТВОЙ ID!
# Чтобы узнать свой ID, напиши боту @userinfobot
ADMIN_ID = 8052884471  # Проверь, точно ли это твой ID?

# Аккаунт поддержки
SUPPORT_USERNAME = 'Kurator111'

# Канал с отзывами
REVIEWS_CHANNEL = '+DpdNmcj9gAY2MThi'

# Реквизиты карт
CARDS = [
    {'bank': 'СБЕР', 'card': '2200 3394 8208 3478', 'recipient': 'Дмитрий'},
    {'bank': 'ВТБ', 'card': '2203 1647 7814 6419', 'recipient': 'Дмитрий'}
]

# Цены на UC
UC_PRICES = {
    60: 80,
    120: 160,
    180: 240,
    325: 400,
    385: 480,
    660: 800,
    720: 910,
    985: 1250,
    1320: 1700,
    1800: 1950,
    2460: 2800,
    3850: 4000,
    8100: 8200
}

# Временное хранилище для данных (текст рассылки, активированные промокоды)
bot_data = {}

# Создание базы данных (без удаления, только если таблиц нет)
def init_db():
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  join_date TEXT,
                  total_uc INTEGER DEFAULT 0,
                  total_orders INTEGER DEFAULT 0)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  order_number INTEGER UNIQUE,
                  user_id INTEGER,
                  username TEXT,
                  player_id TEXT,
                  uc_amount INTEGER,
                  price INTEGER,
                  discount INTEGER DEFAULT 0,
                  promocode TEXT,
                  status TEXT,
                  created_at TEXT,
                  completed_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS promocodes
                 (code TEXT PRIMARY KEY,
                  discount INTEGER,
                  max_uses INTEGER,
                  used_count INTEGER DEFAULT 0,
                  expires_at TEXT,
                  created_by INTEGER,
                  created_at TEXT)''')
    
    conn.commit()
    conn.close()
    print("✅ База данных проверена/создана!")

# Получение следующего номера заказа
def get_next_order_number():
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT MAX(order_number) FROM orders")
    max_num = c.fetchone()[0]
    conn.close()
    return (max_num or 0) + 1

# Проверка админа
def is_admin(user_id):
    return user_id == ADMIN_ID

# Команда старт
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Нет username"
    first_name = message.from_user.first_name or "Игрок"
    
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("""INSERT OR IGNORE INTO users 
                 (user_id, username, first_name, join_date, total_uc, total_orders) 
                 VALUES (?,?,?,?,?,?)""",
              (user_id, username, first_name, str(datetime.now()), 0, 0))
    conn.commit()
    conn.close()
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🛒 КУПИТЬ UC")
    btn2 = types.KeyboardButton("👤 МОЙ ПРОФИЛЬ")
    btn3 = types.KeyboardButton("🏆 ЛИДЕРЫ")
    btn4 = types.KeyboardButton("⭐️ ОТЗЫВЫ")
    btn5 = types.KeyboardButton("📞 ПОДДЕРЖКА")
    btn6 = types.KeyboardButton("🎟 ПРОМОКОД")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    
    welcome_text = f"""
👋 <b>ДОБРО ПОЖАЛОВАТЬ В APEX UC SHOP!</b>

🔥 Лучший магазин UC для PUBG Mobile

✅ Наши преимущества:
• Быстрая доставка 5-15 минут
• 100% гарантия пополнения
• Круглосуточная поддержка
• Низкие цены

👇 Нажми КУПИТЬ UC чтобы начать
"""
    bot.send_message(message.chat.id, welcome_text, parse_mode='HTML', reply_markup=markup)

# ==================== ПРОМОКОДЫ ====================

@bot.message_handler(func=lambda message: message.text == "🎟 ПРОМОКОД")
def promocode_menu(message):
    markup = types.InlineKeyboardMarkup()
    btn_activate = types.InlineKeyboardButton("🎟 Активировать промокод", callback_data="activate_promo")
    markup.add(btn_activate)
    
    bot.send_message(
        message.chat.id,
        "🎟 <b>ПРОМОКОДЫ</b>\n\n"
        "Введи промокод и получи скидку на покупку!",
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "activate_promo")
def ask_promocode(call):
    msg = bot.send_message(
        call.message.chat.id,
        "📝 <b>ВВЕДИТЕ ПРОМОКОД:</b>\n\n"
        "Пример: WELCOME10",
        parse_mode='HTML'
    )
    bot.register_next_step_handler(msg, process_promocode)

def process_promocode(message):
    code = message.text.upper().strip()
    user_id = message.from_user.id
    
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    
    c.execute("SELECT discount, max_uses, used_count, expires_at FROM promocodes WHERE code = ?", (code,))
    promo = c.fetchone()
    
    if not promo:
        bot.send_message(message.chat.id, "❌ <b>Промокод не найден!</b>", parse_mode='HTML')
        conn.close()
        return
    
    discount, max_uses, used_count, expires_at = promo
    
    # Проверка лимита использований
    if max_uses > 0 and used_count >= max_uses:
        bot.send_message(message.chat.id, "❌ <b>Промокод больше не действует!</b>", parse_mode='HTML')
        conn.close()
        return
    
    # Проверка срока действия
    if expires_at:
        if datetime.now() > datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S'):
            bot.send_message(message.chat.id, "❌ <b>Срок действия промокода истек!</b>", parse_mode='HTML')
            conn.close()
            return
    
    # Увеличиваем счётчик использований
    c.execute("UPDATE promocodes SET used_count = used_count + 1 WHERE code = ?", (code,))
    conn.commit()
    conn.close()
    
    # Сохраняем активированный промокод для пользователя (в оперативной памяти)
    # В реальном проекте лучше хранить в БД, но для простоты так
    bot_data[f"promo_{user_id}"] = {'code': code, 'discount': discount}
    
    bot.send_message(
        message.chat.id,
        f"✅ <b>Промокод активирован!</b>\n\n"
        f"🎁 Ваша скидка: <b>{discount}%</b>\n"
        f"💰 Скидка будет применена при следующей покупке!",
        parse_mode='HTML'
    )

# ==================== АДМИН ПАНЕЛЬ ====================

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ У вас нет прав администратора!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("📊 СТАТИСТИКА", callback_data="admin_stats")
    btn2 = types.InlineKeyboardButton("📢 РАССЫЛКА", callback_data="admin_mailing")
    btn3 = types.InlineKeyboardButton("🎟 ПРОМОКОДЫ", callback_data="admin_promocodes")
    btn4 = types.InlineKeyboardButton("💰 ЗАКАЗЫ", callback_data="admin_orders")
    btn5 = types.InlineKeyboardButton("👥 ПОЛЬЗОВАТЕЛИ", callback_data="admin_users")
    btn6 = types.InlineKeyboardButton("⚙️ НАСТРОЙКИ", callback_data="admin_settings")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    
    bot.send_message(
        message.chat.id,
        "👨‍💼 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        "Выберите раздел:",
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав!")
        return
    
    action = call.data.split('_')[1]
    
    if action == "stats":
        show_admin_stats(call)
    elif action == "mailing":
        start_mailing(call)
    elif action == "promocodes":
        show_promocodes_menu(call)
    elif action == "orders":
        bot.answer_callback_query(call.id, "В разработке")
    elif action == "users":
        bot.answer_callback_query(call.id, "В разработке")
    elif action == "settings":
        bot.answer_callback_query(call.id, "В разработке")

def show_admin_stats(call):
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE join_date > date('now', '-1 day')")
    new_users_today = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
    completed_orders = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
    pending_orders = c.fetchone()[0]
    
    c.execute("SELECT SUM(price) FROM orders WHERE status = 'completed'")
    total_earned = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(price) FROM orders WHERE date(created_at) = date('now') AND status = 'completed'")
    earned_today = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(uc_amount) FROM orders WHERE status = 'completed'")
    total_uc_sold = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM promocodes")
    total_promocodes = c.fetchone()[0]
    
    conn.close()
    
    text = f"""
📊 <b>СТАТИСТИКА БОТА</b>

👥 <b>Пользователи:</b>
📱 Всего: {total_users}
📈 Новых сегодня: {new_users_today}

📦 <b>Заказы:</b>
📋 Всего: {total_orders}
✅ Выполнено: {completed_orders}
⏳ В обработке: {pending_orders}

💰 <b>Финансы:</b>
💵 Всего заработано: {total_earned:,} ₽
💳 Сегодня: {earned_today:,} ₽
🎮 Продано UC: {total_uc_sold}

🎟 <b>Промокоды:</b>
🏷 Всего создано: {total_promocodes}
"""
    
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_admin")
    markup.add(btn_back)
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        parse_mode='HTML',
        reply_markup=markup
    )

# ==================== РАССЫЛКА ====================

def start_mailing(call):
    markup = types.InlineKeyboardMarkup()
    btn_cancel = types.InlineKeyboardButton("❌ ОТМЕНА", callback_data="back_to_admin")
    markup.add(btn_cancel)
    
    msg = bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="📢 <b>РАССЫЛКА</b>\n\n"
             "Введите текст для рассылки всем пользователям:",
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.register_next_step_handler(msg.message, process_mailing_text)

def process_mailing_text(message):
    if not is_admin(message.from_user.id):
        return
    
    mailing_text = message.text
    
    # Сохраняем текст во временном хранилище с уникальным ключом
    msg_id = message.message_id
    bot_data[f"mailing_{msg_id}"] = mailing_text
    
    markup = types.InlineKeyboardMarkup()
    btn_confirm = types.InlineKeyboardButton("✅ ПОДТВЕРДИТЬ", callback_data=f"mailing_confirm:{msg_id}")
    btn_cancel = types.InlineKeyboardButton("❌ ОТМЕНА", callback_data="back_to_admin")
    markup.add(btn_confirm, btn_cancel)
    
    bot.send_message(
        message.chat.id,
        f"📢 <b>ПРЕДПРОСМОТР РАССЫЛКИ:</b>\n\n{mailing_text}\n\n"
        f"Отправить это сообщение всем пользователям?",
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('mailing_confirm:'))
def confirm_mailing(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав!")
        return
    
    msg_id = int(call.data.split(':')[1])
    mailing_text = bot_data.get(f"mailing_{msg_id}")
    
    if not mailing_text:
        bot.answer_callback_query(call.id, "❌ Текст рассылки не найден!")
        return
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="📢 <b>РАССЫЛКА НАЧАТА</b>\n\n"
             "Сообщения отправляются пользователям...",
        parse_mode='HTML'
    )
    
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    
    sent_count = 0
    error_count = 0
    
    for user in users:
        user_id = user[0]
        try:
            bot.send_message(user_id, mailing_text, parse_mode='HTML')
            sent_count += 1
            time.sleep(0.05)
        except Exception as e:
            print(f"Ошибка отправки пользователю {user_id}: {e}")
            error_count += 1
    
    # Удаляем временные данные
    if f"mailing_{msg_id}" in bot_data:
        del bot_data[f"mailing_{msg_id}"]
    
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_admin")
    markup.add(btn_back)
    
    bot.send_message(
        call.message.chat.id,
        f"📢 <b>РАССЫЛКА ЗАВЕРШЕНА</b>\n\n"
        f"✅ Успешно отправлено: {sent_count}\n"
        f"❌ Ошибок: {error_count}\n"
        f"👥 Всего пользователей: {len(users)}",
        parse_mode='HTML',
        reply_markup=markup
    )

# ==================== УПРАВЛЕНИЕ ПРОМОКОДАМИ ====================

def show_promocodes_menu(call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_create = types.InlineKeyboardButton("➕ СОЗДАТЬ", callback_data="promo_create")
    btn_list = types.InlineKeyboardButton("📋 СПИСОК", callback_data="promo_list")
    btn_delete = types.InlineKeyboardButton("❌ УДАЛИТЬ", callback_data="promo_delete")
    btn_back = types.InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_admin")
    markup.add(btn_create, btn_list, btn_delete, btn_back)
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🎟 <b>УПРАВЛЕНИЕ ПРОМОКОДАМИ</b>\n\n"
             "Выберите действие:",
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('promo_'))
def promo_actions(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав!")
        return
    
    action = call.data.split('_')[1]
    
    if action == "create":
        msg = bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🎟 <b>СОЗДАНИЕ ПРОМОКОДА</b>\n\n"
                 "Введите код промокода (например, SUMMER2026):",
            parse_mode='HTML'
        )
        bot.register_next_step_handler(msg.message, process_promo_code)
    
    elif action == "list":
        show_promo_list(call)
    
    elif action == "delete":
        msg = bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🎟 <b>УДАЛЕНИЕ ПРОМОКОДА</b>\n\n"
                 "Введите код промокода для удаления:",
            parse_mode='HTML'
        )
        bot.register_next_step_handler(msg.message, process_promo_delete)

def process_promo_code(message):
    if not is_admin(message.from_user.id):
        return
    
    promo_code = message.text.upper().strip()
    
    msg = bot.send_message(
        message.chat.id,
        f"🎟 Промокод: <b>{promo_code}</b>\n\n"
        f"Введите размер скидки (только число, например 10):",
        parse_mode='HTML'
    )
    bot.register_next_step_handler(msg, lambda m: process_promo_discount(m, promo_code))

def process_promo_discount(message, promo_code):
    if not is_admin(message.from_user.id):
        return
    
    try:
        discount = int(message.text)
        if discount < 1 or discount > 100:
            raise ValueError
    except:
        bot.send_message(message.chat.id, "❌ Ошибка! Введите число от 1 до 100")
        return
    
    msg = bot.send_message(
        message.chat.id,
        f"🎟 Промокод: <b>{promo_code}</b>\n"
        f"💰 Скидка: <b>{discount}%</b>\n\n"
        f"Введите максимальное количество использований (0 - без ограничений):",
        parse_mode='HTML'
    )
    bot.register_next_step_handler(msg, lambda m: process_promo_uses(m, promo_code, discount))

def process_promo_uses(message, promo_code, discount):
    if not is_admin(message.from_user.id):
        return
    
    try:
        max_uses = int(message.text)
    except:
        bot.send_message(message.chat.id, "❌ Ошибка! Введите число")
        return
    
    msg = bot.send_message(
        message.chat.id,
        f"🎟 Промокод: <b>{promo_code}</b>\n"
        f"💰 Скидка: <b>{discount}%</b>\n"
        f"📊 Использований: {max_uses if max_uses > 0 else 'без ограничений'}\n\n"
        f"Введите срок действия (дней, 0 - без срока):",
        parse_mode='HTML'
    )
    bot.register_next_step_handler(msg, lambda m: save_promocode(m, promo_code, discount, max_uses))

def save_promocode(message, promo_code, discount, max_uses):
    if not is_admin(message.from_user.id):
        return
    
    try:
        days = int(message.text)
    except:
        bot.send_message(message.chat.id, "❌ Ошибка! Введите число")
        return
    
    expires_at = None
    if days > 0:
        expires_at = str(datetime.now() + timedelta(days=days))
    
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    
    try:
        c.execute("""INSERT INTO promocodes 
                     (code, discount, max_uses, expires_at, created_by, created_at)
                     VALUES (?,?,?,?,?,?)""",
                  (promo_code, discount, max_uses, expires_at, message.from_user.id, str(datetime.now())))
        conn.commit()
        
        markup = types.InlineKeyboardMarkup()
        btn_back = types.InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_admin")
        markup.add(btn_back)
        
        bot.send_message(
            message.chat.id,
            f"✅ <b>ПРОМОКОД СОЗДАН!</b>\n\n"
            f"🎟 Код: {promo_code}\n"
            f"💰 Скидка: {discount}%\n"
            f"📊 Лимит: {max_uses if max_uses > 0 else 'без ограничений'}\n"
            f"⏰ Срок: {days if days > 0 else 'бессрочно'}",
            parse_mode='HTML',
            reply_markup=markup
        )
    except sqlite3.IntegrityError:
        bot.send_message(message.chat.id, f"❌ Промокод {promo_code} уже существует!")
    finally:
        conn.close()

def show_promo_list(call):
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT code, discount, max_uses, used_count, expires_at FROM promocodes ORDER BY created_at DESC LIMIT 10")
    promos = c.fetchall()
    conn.close()
    
    if not promos:
        text = "🎟 <b>ПРОМОКОДЫ</b>\n\nСписок пуст"
    else:
        text = "🎟 <b>ПОСЛЕДНИЕ ПРОМОКОДЫ:</b>\n\n"
        for promo in promos:
            code, discount, max_uses, used, expires = promo
            status = "✅ Активен"
            if expires:
                try:
                    if datetime.now() > datetime.strptime(expires, '%Y-%m-%d %H:%M:%S'):
                        status = "❌ Истек"
                except:
                    status = "⚠️ Ошибка даты"
            text += f"• <b>{code}</b> — {discount}%\n"
            text += f"  Использовано: {used}/{max_uses if max_uses > 0 else '∞'} | {status}\n\n"
    
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("◀️ НАЗАД", callback_data="promo_back")
    markup.add(btn_back)
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        parse_mode='HTML',
        reply_markup=markup
    )

def process_promo_delete(message):
    if not is_admin(message.from_user.id):
        return
    
    code = message.text.upper().strip()
    
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("DELETE FROM promocodes WHERE code = ?", (code,))
    deleted = c.rowcount
    conn.commit()
    conn.close()
    
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("◀️ НАЗАД", callback_data="promo_back")
    markup.add(btn_back)
    
    if deleted:
        bot.send_message(
            message.chat.id,
            f"✅ Промокод <b>{code}</b> удален!",
            parse_mode='HTML',
            reply_markup=markup
        )
    else:
        bot.send_message(
            message.chat.id,
            f"❌ Промокод <b>{code}</b> не найден!",
            parse_mode='HTML',
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data == "back_to_admin")
def back_to_admin(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав!")
        return
    
    # Возвращаемся в админ-панель, имитируем команду /admin
    admin_panel(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "promo_back")
def promo_back(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав!")
        return
    
    show_promocodes_menu(call)

# ==================== ПОКУПКА UC ====================
# (весь код покупки остаётся без изменений, кроме добавления применения скидки)

@bot.message_handler(func=lambda message: message.text == "🛒 КУПИТЬ UC")
def buy_uc(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    
    for uc, price in sorted(UC_PRICES.items()):
        price_str = f"{price:,}".replace(',', '.')
        buttons.append(types.InlineKeyboardButton(
            f"{uc} UC — {price_str} ₽", 
            callback_data=f"uc_{uc}_{price}"
        ))
    
    markup.add(*buttons)
    
    bot.send_message(
        message.chat.id,
        "🛒 <b>ВЫБЕРИТЕ ПАКЕТ UC:</b>\n\n👇 Нажмите на нужный пакет",
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('uc_'))
def select_package(call):
    data = call.data.split('_')
    uc_amount = int(data[1])
    price = int(data[2])
    
    # Проверяем, есть ли активированный промокод
    user_id = call.from_user.id
    promo_info = bot_data.get(f"promo_{user_id}")
    final_price = price
    discount = 0
    promo_code = None
    
    if promo_info:
        discount = promo_info['discount']
        promo_code = promo_info['code']
        final_price = int(price * (100 - discount) / 100)
        # Удаляем промокод после использования (одноразово)
        del bot_data[f"promo_{user_id}"]
    
    msg = bot.send_message(
        call.message.chat.id,
        f"📝 <b>ВВЕДИТЕ ВАШ ID В PUBG:</b>\n\n"
        f"🎮 Пакет: {uc_amount} UC\n"
        f"💰 Исходная сумма: {price:,} ₽\n"
        + (f"🎟 Скидка {discount}%: {final_price:,} ₽\n" if discount else "")
        + f"\n⚠️ <b>ВНИМАНИЕ!</b>\n"
        f"Проверьте ID несколько раз перед отправкой!\n\n"
        f"Пример: 1234567890",
        parse_mode='HTML'
    )
    
    # Передаём все параметры в следующий шаг
    bot.register_next_step_handler(msg, process_player_id, uc_amount, final_price, price, discount, promo_code)

def process_player_id(message, uc_amount, final_price, original_price, discount, promo_code):
    player_id = message.text.strip()
    
    if not player_id.isdigit() or len(player_id) < 5:
        bot.send_message(
            message.chat.id,
            "❌ <b>ОШИБКА!</b>\n\n"
            "Введите корректный ID (только цифры, минимум 5 цифр).\n"
            "Попробуйте снова через 🛒 КУПИТЬ UC",
            parse_mode='HTML'
        )
        return
    
    order_number = get_next_order_number()
    
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("""INSERT INTO orders 
                 (order_number, user_id, username, player_id, uc_amount, price, discount, promocode, status, created_at)
                 VALUES (?,?,?,?,?,?,?,?,?,?)""",
              (order_number, message.from_user.id, message.from_user.username or "Нет username", 
               player_id, uc_amount, final_price, discount, promo_code, 'pending', str(datetime.now())))
    conn.commit()
    conn.close()
    
    show_payment(message, order_number, player_id, uc_amount, final_price)

def show_payment(message, order_number, player_id, uc_amount, price):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("✅ Я ОПЛАТИЛ", callback_data=f"paid_{order_number}")
    btn2 = types.InlineKeyboardButton("❌ ОТМЕНА", callback_data=f"cancel_{order_number}")
    markup.add(btn1, btn2)
    
    price_str = f"{price:,}".replace(',', '.')
    
    text = f"""
✅ <b>ЗАКАЗ №{order_number} СОЗДАН!</b>

📦 <b>Детали заказа:</b>
• Пакет: {uc_amount} UC
• Сумма: {price_str} ₽
• ID: {player_id}

💳 <b>РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ:</b>\n
"""
    for card in CARDS:
        text += f"""
🏦 {card['bank']}
💳 Карта: <code>{card['card']}</code>
👤 Получатель: {card['recipient']}\n"""
    
    text += f"""
💰 <b>Сумма: {price_str} ₽ (на любую карту)</b>

⚠️ <b>ВАЖНО:</b>
1. Переведи точную сумму
2. Можешь выбрать любой удобный банк
3. После оплаты нажми кнопку '✅ Я ОПЛАТИЛ'
4. Ожидай пополнения 5-15 минут
"""
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)

# Подтверждение оплаты (пользователь)
@bot.callback_query_handler(func=lambda call: call.data.startswith('paid_'))
def user_paid(call):
    order_number = int(call.data.split('_')[1])
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"""
✅ <b>ЗАЯВКА ПРИНЯТА!</b>

📋 <b>ЗАКАЗ №{order_number}</b>

✅ Ваша оплата проверяется!
⏱ Ожидайте, оператор проверит платеж

⏳ СРЕДНЕЕ ВРЕМЯ: 5-15 минут
""",
        parse_mode='HTML'
    )
    
    # Уведомление админу
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id, username, player_id, uc_amount, price FROM orders WHERE order_number = ?", (order_number,))
    order = c.fetchone()
    conn.close()
    
    if order:
        user_id, username, player_id, uc_amount, price = order
        price_str = f"{price:,}".replace(',', '.')
        
        markup_admin = types.InlineKeyboardMarkup(row_width=2)
        btn_confirm = types.InlineKeyboardButton("✅ ПОДТВЕРДИТЬ", callback_data=f"confirm_{order_number}")
        btn_cancel = types.InlineKeyboardButton("❌ ОТМЕНИТЬ", callback_data=f"admin_cancel_{order_number}")
        markup_admin.add(btn_confirm, btn_cancel)
        
        try:
            bot.send_message(
                ADMIN_ID,
                f"💰 <b>ПОДТВЕРЖДЕНИЕ ОПЛАТЫ №{order_number}</b> 💰\n\n"
                f"👤 Пользователь: @{username}\n"
                f"🆔 User ID: <code>{user_id}</code>\n"
                f"🎮 Пакет: {uc_amount} UC\n"
                f"💰 Сумма: {price_str} ₽\n"
                f"🆔 Player ID: {player_id}\n\n"
                f"👇 <b>Выберите действие:</b>",
                parse_mode='HTML',
                reply_markup=markup_admin
            )
        except:
            print("Не удалось отправить уведомление админу")

# Подтверждение заказа (админ)
@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
def admin_confirm(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав!")
        return
    
    order_number = int(call.data.split('_')[1])
    
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("""UPDATE orders SET status = 'completed', completed_at = ? 
                 WHERE order_number = ?""", (str(datetime.now()), order_number))
    
    c.execute("SELECT user_id, uc_amount, player_id FROM orders WHERE order_number = ?", (order_number,))
    order = c.fetchone()
    if order:
        user_id, uc_amount, player_id = order
        c.execute("""UPDATE users SET total_uc = total_uc + ?, total_orders = total_orders + 1
                     WHERE user_id = ?""", (uc_amount, user_id))
    
    conn.commit()
    conn.close()
    
    if order:
        user_id, uc_amount, player_id = order
        
        markup = types.InlineKeyboardMarkup()
        btn_review = types.InlineKeyboardButton("⭐ Оставить отзыв", url=f"https://t.me/{REVIEWS_CHANNEL}")
        markup.add(btn_review)
        
        try:
            bot.send_message(
                user_id,
                f"""
✅ <b>ЗАКАЗ №{order_number} ВЫПОЛНЕН!</b>

💰 <b>{uc_amount} UC</b> успешно зачислены на твой аккаунт!
Спасибо за покупку! ❤️

⭐ Будем благодарны за отзыв о нашей работе!
                """,
                parse_mode='HTML',
                reply_markup=markup
            )
            
            bot.answer_callback_query(call.id, "✅ UC выданы!")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"✅ <b>ЗАКАЗ №{order_number} ПОДТВЕРЖДЕН!</b>\n\nUC успешно выданы.",
                parse_mode='HTML'
            )
            
        except Exception as e:
            bot.answer_callback_query(call.id, f"⚠️ Ошибка: {e}")

# Отмена заказа АДМИНОМ
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_cancel_'))
def admin_cancel(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ У вас нет прав!")
        return
    
    order_number = int(call.data.split('_')[2])
    
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM orders WHERE order_number = ?", (order_number,))
    order = c.fetchone()
    conn.close()
    
    if order:
        user_id = order[0]
        
        markup = types.InlineKeyboardMarkup()
        btn_support = types.InlineKeyboardButton("📞 НАПИСАТЬ В ПОДДЕРЖКУ", url=f"https://t.me/{SUPPORT_USERNAME}")
        markup.add(btn_support)
        
        try:
            bot.send_message(
                user_id,
                f"""
❌ <b>ЗАКАЗ №{order_number} ОТМЕНЕН</b>

Ваш заказ был отменен администратором.

📞 Пожалуйста, уточните детали в поддержке
                """,
                parse_mode='HTML',
                reply_markup=markup
            )
        except:
            pass
    
    bot.answer_callback_query(call.id, "✅ Заказ отменен")
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"❌ <b>ЗАКАЗ №{order_number} ОТМЕНЕН</b>",
        parse_mode='HTML'
    )

# Отмена заказа (пользователь)
@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_'))
def cancel_order(call):
    order_number = int(call.data.split('_')[1])
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"""
❌ <b>ЗАКАЗ ОТМЕНЕН</b>

📋 <b>ЗАКАЗ №{order_number}</b>

Вы можете создать новый заказ в любое время!

👇 Нажмите 🛒 КУПИТЬ UC
""",
        parse_mode='HTML'
    )

# МОЙ ПРОФИЛЬ
@bot.message_handler(func=lambda message: message.text == "👤 МОЙ ПРОФИЛЬ")
def my_profile(message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT total_uc, total_orders, join_date, first_name FROM users WHERE user_id = ?", (user_id,))
    user_data = c.fetchone()
    
    if user_data:
        total_uc, total_orders, join_date, first_name = user_data
        join_date_str = join_date[:10] if join_date else "Неизвестно"
    else:
        total_uc, total_orders, join_date_str, first_name = 0, 0, str(datetime.now())[:10], "Игрок"
    
    text = f"""
👤 <b>МОЙ ПРОФИЛЬ</b>
Привет, {first_name}!

📊 <b>СТАТИСТИКА:</b>
🆔 User ID: <code>{user_id}</code>
📅 На сайте с: {join_date_str}

💰 <b>ПОКУПКИ:</b>
📦 Всего заказов: {total_orders}
🎮 Всего UC: {total_uc}
"""
    bot.send_message(message.chat.id, text, parse_mode='HTML')

# ЛИДЕРЫ
@bot.message_handler(func=lambda message: message.text == "🏆 ЛИДЕРЫ")
def leaders(message):
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("""SELECT first_name, total_uc FROM users 
                 WHERE total_uc > 0 
                 ORDER BY total_uc DESC LIMIT 10""")
    leaders_list = c.fetchall()
    conn.close()
    
    if not leaders_list:
        bot.send_message(
            message.chat.id,
            "🏆 <b>ЛИДЕРОВ ПОКА НЕТ</b>\n\nСделайте первый заказ и попадите в топ!",
            parse_mode='HTML'
        )
        return
    
    text = "🏆 <b>ТОП-10 ПОКУПАТЕЛЕЙ (по количеству UC)</b>\n\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, leader in enumerate(leaders_list):
        first_name, total_uc = leader
        text += f"{medals[i]} {first_name} — {total_uc} UC\n"
    
    bot.send_message(message.chat.id, text, parse_mode='HTML')

# ОТЗЫВЫ
@bot.message_handler(func=lambda message: message.text == "⭐️ ОТЗЫВЫ")
def reviews(message):
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("📢 ПЕРЕЙТИ В КАНАЛ С ОТЗЫВАМИ", url=f"https://t.me/{REVIEWS_CHANNEL}")
    markup.add(btn)
    
    text = """
⭐️ <b>НАШИ ОТЗЫВЫ</b> ⭐️

👇 Нажми на кнопку чтобы перейти в канал с отзывами
"""
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)

# ПОДДЕРЖКА
@bot.message_handler(func=lambda message: message.text == "📞 ПОДДЕРЖКА")
def support(message):
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("👨‍💼 НАПИСАТЬ В ПОДДЕРЖКУ", url=f"https://t.me/{SUPPORT_USERNAME}")
    markup.add(btn)
    
    text = """
📞 <b>СЛУЖБА ПОДДЕРЖКИ</b>

🕐 Работаем 24/7 без выходных
⏱ Среднее время ответа: 5-10 минут

👇 Нажми кнопку ниже
"""
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)

# Запуск
if __name__ == '__main__':
    print("🔄 Проверяю базу данных...")
    init_db()
    print("✅ БОТ ЗАПУЩЕН!")
    print(f"👤 ADMIN ID: {ADMIN_ID}")
    print("⚡️ БОТ РАБОТАЕТ - ОТПРАВЬ /start")
    
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)
