import telebot
from telebot import types
import sqlite3
import random
from datetime import datetime
import time

# Токен бота
TOKEN = '8531867613:AAHxjS7JtTjoB0mgO_ntFTjakNFbVn2stuI'
bot = telebot.TeleBot(TOKEN)

# ID админа
ADMIN_ID = 8052884471

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

# Создание базы данных
def init_db():
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    
    c.execute('DROP TABLE IF EXISTS users')
    c.execute('DROP TABLE IF EXISTS orders')
    
    c.execute('''CREATE TABLE users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  join_date TEXT,
                  total_uc INTEGER DEFAULT 0)''')
    
    c.execute('''CREATE TABLE orders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  order_number INTEGER UNIQUE,
                  user_id INTEGER,
                  username TEXT,
                  player_id TEXT,
                  uc_amount INTEGER,
                  price INTEGER,
                  status TEXT,
                  created_at TEXT,
                  completed_at TEXT)''')
    
    conn.commit()
    conn.close()
    print("✅ База данных создана!")

# Получение следующего номера заказа
def get_next_order_number():
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT MAX(order_number) FROM orders")
    max_num = c.fetchone()[0]
    conn.close()
    return (max_num or 0) + 1

# Команда старт
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Нет username"
    first_name = message.from_user.first_name or "Игрок"
    
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("""INSERT OR IGNORE INTO users 
                 (user_id, username, first_name, join_date, total_uc) 
                 VALUES (?,?,?,?,?)""",
              (user_id, username, first_name, str(datetime.now()), 0))
    conn.commit()
    conn.close()
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🛒 КУПИТЬ UC")
    btn2 = types.KeyboardButton("👤 МОЙ ПРОФИЛЬ")
    btn3 = types.KeyboardButton("🏆 ЛИДЕРЫ")
    btn4 = types.KeyboardButton("⭐️ ОТЗЫВЫ")
    btn5 = types.KeyboardButton("📞 ПОДДЕРЖКА")
    markup.add(btn1, btn2, btn3, btn4, btn5)
    
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

# КУПИТЬ UC
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

# Выбор пакета
@bot.callback_query_handler(func=lambda call: call.data.startswith('uc_'))
def select_package(call):
    data = call.data.split('_')
    uc_amount = int(data[1])
    price = int(data[2])
    
    msg = bot.send_message(
        call.message.chat.id,
        f"📝 <b>ВВЕДИТЕ ВАШ ID В PUBG:</b>\n\n"
        f"🎮 Пакет: {uc_amount} UC\n"
        f"💰 Сумма: {price:,} ₽\n\n"
        f"⚠️ <b>ВНИМАНИЕ!</b>\n"
        f"Проверьте ID несколько раз перед отправкой!\n\n"
        f"Пример: 1234567890",
        parse_mode='HTML'
    )
    
    bot.register_next_step_handler(msg, process_player_id, uc_amount, price)

# Обработка ID
def process_player_id(message, uc_amount, price):
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
                 (order_number, user_id, username, player_id, uc_amount, price, status, created_at)
                 VALUES (?,?,?,?,?,?,?,?)""",
              (order_number, message.from_user.id, message.from_user.username or "Нет username", 
               player_id, uc_amount, price, 'pending', str(datetime.now())))
    conn.commit()
    conn.close()
    
    show_payment(message, order_number, player_id, uc_amount, price)

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
    
    # Уведомление админу ТОЛЬКО ПОСЛЕ НАЖАТИЯ "Я ОПЛАТИЛ"
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
    if call.from_user.id != ADMIN_ID:
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
        c.execute("""UPDATE users SET total_uc = total_uc + ? 
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
    if call.from_user.id != ADMIN_ID:
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
    c.execute("SELECT total_uc, join_date, first_name FROM users WHERE user_id = ?", (user_id,))
    user_data = c.fetchone()
    
    c.execute("SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'completed'", (user_id,))
    orders_count = c.fetchone()[0]
    conn.close()
    
    if user_data:
        total_uc, join_date, first_name = user_data
        join_date_str = join_date[:10] if join_date else "Неизвестно"
    else:
        total_uc, join_date_str, first_name, orders_count = 0, str(datetime.now())[:10], "Игрок", 0
    
    text = f"""
👤 <b>МОЙ ПРОФИЛЬ</b>
Привет, {first_name}!

📊 <b>СТАТИСТИКА:</b>
🆔 User ID: <code>{user_id}</code>
📅 На сайте с: {join_date_str}

💰 <b>ПОКУПКИ:</b>
📦 Всего заказов: {orders_count}
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

# ОТЗЫВЫ (исправлено - просто кнопка на канал)
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

# Админ статистика
@bot.message_handler(commands=['admin'])
def admin_stats(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ У вас нет прав администратора!")
        return
    
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
    completed_orders = c.fetchone()[0]
    
    c.execute("SELECT SUM(price) FROM orders WHERE status = 'completed'")
    total_earned = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
    pending_orders = c.fetchone()[0]
    
    c.execute("SELECT SUM(uc_amount) FROM orders WHERE status = 'completed'")
    total_uc_sold = c.fetchone()[0] or 0
    
    conn.close()
    
    text = f"""
📊 <b>СТАТИСТИКА БОТА</b>

👥 <b>Пользователи:</b>
📱 Всего: {total_users}

📦 <b>Заказы:</b>
📋 Всего: {total_orders}
✅ Выполнено: {completed_orders}
⏳ В обработке: {pending_orders}

💰 <b>Финансы:</b>
💵 Всего заработано: {total_earned:,} ₽
🎮 Продано UC: {total_uc_sold}
"""
    bot.send_message(message.chat.id, text, parse_mode='HTML')

# Запуск
if __name__ == '__main__':
    print("🔄 Создаю базу данных...")
    init_db()
    print("✅ БОТ ЗАПУЩЕН!")
    print(f"👤 ADMIN ID: {ADMIN_ID}")
    print(f"📞 SUPPORT: @{SUPPORT_USERNAME}")
    print("⚡️ БОТ РАБОТАЕТ - ОТПРАВЬ /start")
    
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)
