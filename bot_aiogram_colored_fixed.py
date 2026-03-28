import asyncio
import logging
import math
import os
import sqlite3
import traceback
from datetime import datetime, timedelta
from typing import Any

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message

# ---------- ТОКЕН ----------
# Токен перенесён из исходного файла пользователя.
TOKEN = "8273450975:AAGtQCZOKWOhCDfMzYHJ-HwVlagiCp7l-Yo"

# ---------- НАСТРОЙКИ ----------
ADMIN_ID = 8052884471
SUPPORT_USERNAME = "Kurator111"
REVIEWS_CHANNEL = "+DpdNmcj9gAY2MThi"
DB_PATH = "uc_bot.db"
MAIN_MENU_IMAGE = "IMG_2822.jpeg"
MAIN_MENU_IMAGE_FALLBACK = "IMG_2811.jpeg"

BACK_EMOJI_ID = "5255703720078879038"
BUY_EMOJI_ID = "5253542964981955943"
TG_STARS_EMOJI_ID = "5208801655004350721"
TG_PREMIUM_EMOJI_ID = "5309773986786220864"

CARDS = [
    {"bank": "СБЕР", "card": "2202 2084 1737 7224", "recipient": "Дмитрий"},
    {"bank": "ВТБ", "card": "2200 2479 5387 8262", "recipient": "Дмитрий"},
]

# Обновлённые цены на UC
UC_PRICES = {
    60: 80,
    325: 389,
    660: 810,
    1800: 2050,
    3850: 4100,
    8100: 8100,
}

POPULARITY_ITEMS = {
    "pop_regular": {
        "title": "Популярность",
        "description": (
            "<b>Популярность</b>\n\n"
            "➤ Купить Популярность Вы можете круглосуточно (24/7)\n\n"
            "❕ Не оформляйте заказ если до конца раунда осталось менее 15 минут\n\n"
            "🕒 Среднее время доставки 1-15 минут"
        ),
        "product_label": "Популярность",
        "admin_label": "Популярность",
        "prices": [
            ("10 000 ПП", 150),
            ("20 000 ПП", 300),
            ("40 000 ПП", 600),
            ("60 000 ПП", 900),
            ("100 000 ПП", 1500),
            ("200 000 ПП", 3000),
            ("500 000 ПП", 7500),
        ],
    },
    "pop_home": {
        "title": "Популярность для дома",
        "description": (
            "<b>Популярность для дома</b>\n\n"
            "➤ Купить Популярность для дома Вы можете круглосуточно (24/7)\n\n"
            "❕ Не оформляйте заказ если до конца раунда осталось менее 15 минут\n\n"
            "🕒 Среднее время доставки 1-15 минут"
        ),
        "product_label": "Популярность для дома",
        "admin_label": "ПП для дома",
        "prices": [
            ("20 000 ПП для дома", 250),
            ("40 000 ПП для дома", 500),
            ("60 000 ПП для дома", 750),
            ("100 000 ПП для дома", 1250),
            ("200 000 ПП для дома", 2500),
            ("500 000 ПП для дома", 6250),
        ],
    },
    "pop_last": {
        "title": "Популярность на последней минуте",
        "description": (
            "<b>Популярность для последних минут раунда</b>\n\n"
            "➤ Оформляйте заказ заранее и популярность вам поступит в последние 1-2 минуты раунда\n\n"
            "❕ Оформляйте заказ не позже 30 минут до конца раунда"
        ),
        "product_label": "Популярность на последней минуте",
        "admin_label": "Популярность на последней минуте",
        "prices": [
            ("50 000 ПП", 1300),
            ("100 000 ПП", 2600),
            ("150 000 ПП", 3900),
            ("200 000 ПП", 5200),
            ("500 000 ПП", 13000),
        ],
    },
}

SUBSCRIPTION_INFO_TEXT = (
    "<blockquote>⭐ Prime (1 месяц) - 60 UC\n"
    "⭐ Prime (3 месяца) - 180 UC\n"
    "⭐ Prime (6 месяцев) - 360 UC\n"
    "⭐ Prime (12 месяцев) - 720 UC\n"
    "❗ А также - 3 UC, 5 RP очков каждый день</blockquote>\n\n"
    "<blockquote>👑\n"
    "<b>PRIME PLUS (1 месяц)</b>\n"
    "- 660 UC сразу + 240 UC в течении месяца\n"
    "+300 PR очков + скидочные купоны + МАГАЗИН BP + ГАРДЕРОБ</blockquote>\n\n"
    "<blockquote>👑\n"
    "<b>PRIME PLUS (3 месяца)</b>\n"
    "- 1980 UC сразу + 730 UC в течении 3-х месяцев\n"
    "+900 PR очков + скидочные купоны + МАГАЗИН BP + ГАРДЕРОБ</blockquote>\n\n"
    "<blockquote>👑\n"
    "<b>PRIME PLUS (6 месяцев)</b>\n"
    "- 3960 UC сразу + 1460 UC в течении 6-ти месяцев\n"
    "+1,800 PR очков + скидочные купоны + МАГАЗИН BP + ГАРДЕРОБ</blockquote>\n\n"
    "<blockquote>👑\n"
    "<b>PRIME PLUS (12 месяцев)</b>\n"
    "- 7920 UC сразу + 2920 UC в течении года\n"
    "+3,600 PR очков + скидочные купоны + МАГАЗИН BP + ГАРДЕРОБ</blockquote>\n\n"
    "<blockquote>🔺 Миф Кристал: покупается 1 раз в неделю\n"
    "⚪ Набор «первой покупки»: можно купить 1 раз\n"
    "🟡 Набор «материалов»: можно купить 1 раз\n"
    "🔴 Набор «миф. эмблем»: можно купить 1 раз</blockquote>"
)

SUBSCRIPTION_ITEMS = [
    ("Prime (1 месяц)", 120),
    ("Prime (3 месяца)", 320),
    ("Prime (6 месяцев)", 557),
    ("Prime (12 месяцев)", 1007),
    ("Prime Plus (1 месяц)", 850),
    ("Prime Plus (3 месяца)", 2550),
    ("Prime Plus (6 месяцев)", 5100),
    ("Prime Plus (12 месяцев)", 6960),
    ("Миф.Кристал", 330),
]

TG_PREMIUM_ITEMS = [
    ("3 месяца", 1150),
    ("6 месяцев", 1490),
    ("12 месяцев", 2550),
]

BRAWL_STARS_ITEMS = [
    ("30 гемов", 163),
    ("80 гемов", 347),
    ("170 гемов", 796),
    ("360 гемов", 1632),
    ("950 гемов", 4080),
    ("2000 гемов", 8160),
    ("Brawl Pass", 734),
    ("Brawl Pass Plus", 1061),
]

CLASH_ROYALE_ITEMS = [
    ("80 гемов", 82),
    ("500 гемов", 408),
    ("1200 гемов", 816),
    ("2500 гемов", 1632),
    ("6500 гемов", 4080),
    ("14000 гемов", 816),
    ("Gold Pass", 979),
]

router = Router()
menu_sessions: dict[int, dict[str, Any]] = {}
mailing_data: dict[str, Any] | None = None


class UserFlow(StatesGroup):
    uc_player_id = State()
    pop_player_id = State()
    sub_player_id = State()
    tgstars_username = State()
    tgstars_amount = State()
    tgpremium_username = State()
    tgpremium_period = State()
    promo_input = State()


class AdminFlow(StatesGroup):
    promo_code = State()
    promo_discount = State()
    promo_uses = State()
    promo_expiry = State()
    mailing_content = State()


# ---------- ВСПОМОГАТЕЛЬНОЕ ----------
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


async def run_db(fn, *args, **kwargs):
    return await asyncio.to_thread(fn, *args, **kwargs)


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def fmt_price(value: float | int) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, float):
        text = f"{value:,.1f}"
    else:
        text = f"{value:,}"
    return text.replace(",", " ")


def escape_html(text: Any) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def tg_emoji(emoji_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def get_main_menu_image_path() -> str | None:
    image_names = [MAIN_MENU_IMAGE, MAIN_MENU_IMAGE_FALLBACK]
    candidates: list[str] = []
    for image_name in image_names:
        candidates.extend(
            [
                image_name,
                os.path.join(os.getcwd(), image_name),
                os.path.join(os.path.dirname(__file__), image_name),
                os.path.join("/mnt/data", image_name),
            ]
        )
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def get_table_columns(cursor: sqlite3.Cursor, table_name: str) -> list[str]:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [col[1] for col in cursor.fetchall()]


def add_column_if_not_exists(cursor: sqlite3.Cursor, table: str, column: str, col_type: str, default: str | None = None) -> None:
    columns = get_table_columns(cursor, table)
    if column not in columns:
        if default is not None:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default}")
        else:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


def init_db() -> None:
    conn = get_conn()
    c = conn.cursor()

    c.execute(
        """CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        join_date TEXT,
        total_uc INTEGER DEFAULT 0,
        total_orders INTEGER DEFAULT 0
    )"""
    )

    c.execute(
        """CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number INTEGER UNIQUE,
        user_id INTEGER,
        username TEXT,
        player_id TEXT,
        uc_amount INTEGER,
        price REAL,
        status TEXT,
        created_at TEXT,
        completed_at TEXT,
        discount INTEGER DEFAULT 0,
        promocode TEXT DEFAULT NULL,
        product_type TEXT DEFAULT 'uc',
        product_name TEXT DEFAULT 'UC',
        quantity_text TEXT DEFAULT NULL,
        target_value TEXT DEFAULT NULL,
        target_type TEXT DEFAULT NULL
    )"""
    )

    c.execute(
        """CREATE TABLE IF NOT EXISTS promocodes (
        code TEXT PRIMARY KEY,
        discount INTEGER,
        created_at TEXT,
        max_uses INTEGER DEFAULT 0,
        used_count INTEGER DEFAULT 0,
        expires_at TEXT DEFAULT NULL,
        active INTEGER DEFAULT 1
    )"""
    )

    c.execute(
        """CREATE TABLE IF NOT EXISTS user_promos (
        user_id INTEGER,
        promo_code TEXT,
        discount INTEGER,
        activated_at TEXT,
        PRIMARY KEY (user_id, promo_code)
    )"""
    )

    add_column_if_not_exists(c, "users", "total_orders", "INTEGER", "0")
    add_column_if_not_exists(c, "orders", "discount", "INTEGER", "0")
    add_column_if_not_exists(c, "orders", "promocode", "TEXT", "NULL")
    add_column_if_not_exists(c, "orders", "product_type", "TEXT", "'uc'")
    add_column_if_not_exists(c, "orders", "product_name", "TEXT", "'UC'")
    add_column_if_not_exists(c, "orders", "quantity_text", "TEXT", "NULL")
    add_column_if_not_exists(c, "orders", "target_value", "TEXT", "NULL")
    add_column_if_not_exists(c, "orders", "target_type", "TEXT", "NULL")
    add_column_if_not_exists(c, "promocodes", "max_uses", "INTEGER", "0")
    add_column_if_not_exists(c, "promocodes", "used_count", "INTEGER", "0")
    add_column_if_not_exists(c, "promocodes", "expires_at", "TEXT", "NULL")
    add_column_if_not_exists(c, "promocodes", "active", "INTEGER", "1")

    conn.commit()
    conn.close()


def ensure_user_db(user_id: int, username: str | None, first_name: str | None) -> None:
    conn = get_conn()
    c = conn.cursor()
    safe_username = username or "Нет username"
    safe_first_name = first_name or "Игрок"
    c.execute(
        """INSERT OR IGNORE INTO users
                 (user_id, username, first_name, join_date, total_uc, total_orders)
                 VALUES (?,?,?,?,?,?)""",
        (user_id, safe_username, safe_first_name, str(datetime.now()), 0, 0),
    )
    c.execute(
        "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
        (safe_username, safe_first_name, user_id),
    )
    conn.commit()
    conn.close()


async def ensure_user(user: Any) -> None:
    await run_db(ensure_user_db, user.id, user.username, user.first_name)


def get_next_order_number_db() -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT MAX(order_number) FROM orders")
    max_num = c.fetchone()[0]
    conn.close()
    return (max_num or 0) + 1


async def get_next_order_number() -> int:
    return await run_db(get_next_order_number_db)


def get_menu_session(user_id: int) -> dict[str, Any]:
    return dict(menu_sessions.get(user_id, {}))


def set_menu_session(user_id: int, **kwargs: Any) -> None:
    current = menu_sessions.get(user_id, {})
    current.update(kwargs)
    menu_sessions[user_id] = current


def clear_menu_session(user_id: int) -> None:
    menu_sessions[user_id] = {}


async def safe_delete_message(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


async def delete_user_message(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        pass


def build_inline_button(
    text: str,
    callback_data: str,
    emoji_id: str | None = None,
    style: str | None = None,
) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text,
        callback_data=callback_data,
        icon_custom_emoji_id=str(emoji_id) if emoji_id else None,
        style=style,
    )


def build_url_button(
    text: str,
    url: str,
    emoji_id: str | None = None,
    style: str | None = None,
) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text,
        url=url,
        icon_custom_emoji_id=str(emoji_id) if emoji_id else None,
        style=style,
    )


# ---------- КЛАВИАТУРЫ ----------
def menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [build_inline_button("Купить UC", "menu_uc", BUY_EMOJI_ID, "danger")],
            [build_inline_button("Приложение [Все игры]", "menu_all_games_stub", "5456343263340405032", "success")],
            [
                build_inline_button("Популярность", "menu_popularity", "5253698266704408740", "primary"),
                build_inline_button("Подписки", "menu_subs", "5253686910810878689", "primary"),
            ],
            [
                build_inline_button("Промокоды", "menu_promo", "5377599075237502153", "success"),
                build_inline_button("Информация", "menu_profile", "5447410659077661506", "success"),
            ],
            [
                build_inline_button("Telegram Stars", "menu_tgstars", TG_STARS_EMOJI_ID, "primary"),
                build_inline_button("Telegram Premium", "menu_tgpremium", TG_PREMIUM_EMOJI_ID, "primary"),
            ],
            [
                build_inline_button("Поддержка", "menu_support", "5213179235996294999", "danger"),
                build_inline_button("Отзывы", "menu_reviews", "5463289097336405244", "danger"),
            ],
        ]
    )


def all_games_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                build_inline_button("FC Mobile", "game_stub_fc_mobile", style="success"),
                build_inline_button("Roblox", "game_stub_roblox", style="primary"),
            ],
            [
                build_inline_button("Brawl Stars", "brawl_stars_menu", style="danger"),
                build_inline_button("Clash Royale", "clash_royale_menu", style="primary"),
            ],
            [
                build_inline_button("Free Fire", "game_stub_free_fire", style="success"),
                build_inline_button("Mobile Legends", "game_stub_mobile_legends", style="danger"),
            ],
            [build_inline_button("Mobile Legends (Russia)", "game_stub_mobile_legends_russia", style="primary")],
            [build_inline_button("Назад", "back_main", BACK_EMOJI_ID)],
        ]
    )


def back_to_menu_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[build_inline_button("Назад", "back_main", BACK_EMOJI_ID)]])


def payment_markup(order_number: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                build_inline_button("Я оплатил", f"paid_{order_number}", "5253558615842785529", "success"),
                build_inline_button("Отмена", f"user_cancel_{order_number}", "5255732655273570754", "danger"),
            ]
        ]
    )


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                build_inline_button("Статистика", "admin_stats", "5402298269129334734", "primary"),
                build_inline_button("Промокоды", "admin_promos", "5377599075237502153", "success"),
            ],
            [build_inline_button("Рассылка", "admin_mailing", "5255951007211915983", "danger")],
        ]
    )


# ---------- UI ----------
def render_main_menu_text(first_name: str = "Игрок") -> str:
    return (
        f"{tg_emoji('5404617696589390973', '👋')} <b>ДОБРО ПОЖАЛОВАТЬ В APEX UC SHOP!</b>\n\n\n"
        f"{tg_emoji('5253558615842785529', '✅')} <b>Наши преимущества:</b>\n"
        "• Быстрая доставка 5-15 минут\n"
        "• 100% гарантия пополнения\n"
        "• Круглосуточная поддержка\n"
        "• Низкие цены\n\n"
        f"{tg_emoji('5301038027601098171', '👇')} Нажми <b>КУПИТЬ UC</b> чтобы начать"
    )


async def send_or_update_main_menu(bot: Bot, chat_id: int, user_id: int, first_name: str = "Игрок") -> None:
    text = render_main_menu_text(first_name)
    markup = menu_keyboard()
    state = get_menu_session(user_id)
    menu_message_id = state.get("menu_message_id")
    menu_chat_id = state.get("menu_chat_id", chat_id)
    image_path = get_main_menu_image_path()

    if menu_message_id and menu_chat_id == chat_id:
        await safe_delete_message(bot, chat_id, menu_message_id)

    clear_menu_session(user_id)

    if image_path:
        try:
            sent = await bot.send_photo(
                chat_id=chat_id,
                photo=FSInputFile(image_path),
                caption=text,
                reply_markup=markup,
            )
            set_menu_session(
                user_id,
                menu_chat_id=chat_id,
                menu_message_id=sent.message_id,
                menu_message_type="photo",
            )
            return
        except Exception:
            pass

    sent = await bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)
    set_menu_session(
        user_id,
        menu_chat_id=chat_id,
        menu_message_id=sent.message_id,
        menu_message_type="text",
    )


async def edit_menu(
    bot: Bot,
    user_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    chat_id: int | None = None,
) -> bool:
    state = get_menu_session(user_id)
    target_chat_id = chat_id or state.get("menu_chat_id") or user_id
    message_id = state.get("menu_message_id")

    if message_id and state.get("menu_chat_id") == target_chat_id:
        await safe_delete_message(bot, target_chat_id, message_id)

    try:
        sent = await bot.send_message(target_chat_id, text, reply_markup=reply_markup)
        set_menu_session(
            user_id,
            menu_chat_id=target_chat_id,
            menu_message_id=sent.message_id,
            menu_message_type="text",
        )
        return True
    except Exception:
        logging.exception("Не удалось обновить меню")
        return False


async def show_main_menu_for_user(bot: Bot, user: Any) -> None:
    await send_or_update_main_menu(
        bot=bot,
        chat_id=user.id,
        user_id=user.id,
        first_name=user.first_name or "Игрок",
    )


def build_payment_text(order_number: int, product_name: str, quantity_text: str | None, price: float | int, target_value: str, target_type: str) -> str:
    lines = [
        f"{tg_emoji('5253558615842785529', '✅')} <b>ЗАКАЗ №{order_number} СОЗДАН!</b>",
        "",
        f"{tg_emoji('5854908544712707500', '📦')} <b>Детали заказа:</b>",
        f"• Товар: {escape_html(product_name)}",
    ]
    if quantity_text:
        lines.append(f"• Выбрано: {escape_html(quantity_text)}")
    if target_type == "player_id":
        lines.append(f"• PUBG ID: <code>{escape_html(target_value)}</code>")
    elif target_type == "telegram_username":
        lines.append(f"• Получатель: <code>{escape_html(target_value)}</code>")
    elif target_type == "gift":
        lines.append(f"• Способ: {escape_html(target_value)}")
    lines.append(f"• Сумма: {fmt_price(price)} ₽")
    lines.append("")
    lines.append(f"{tg_emoji('5253558615842785529', '✅')} <b>РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ:</b>")
    lines.append("")
    for card in CARDS:
        bank_emoji = "5201863929906620821" if card["bank"] == "СБЕР" else "5201870565631093696"
        lines.extend(
            [
                f"{tg_emoji(bank_emoji, '🏦')} {card['bank']}",
                f"{tg_emoji('5287761106868140153', '💳')} Карта: <code>{card['card']}</code>",
                f"{tg_emoji('5458789419014182183', '👤')} Получатель: {escape_html(card['recipient'])}",
                "",
            ]
        )
    lines.extend(
        [
            f"{tg_emoji('5375296873982604963', '💰')} <b>Сумма: {fmt_price(price)} ₽</b>",
            "",
            f"{tg_emoji('5447644880824181073', '⚠️')} <b>Важно:</b>",
            "1. Переведите точную сумму.",
            "2. После оплаты нажмите кнопку «Я оплатил».",
            "3. Кнопка «Отмена» вернёт вас в главное меню.",
        ]
    )
    return "\n".join(lines)


# ---------- DB ОПЕРАЦИИ ----------
def create_order_db(
    user: Any,
    product_type: str,
    product_name: str,
    quantity_text: str | None,
    price: float | int,
    target_value: str,
    target_type: str,
    uc_amount: int = 0,
    discount: int = 0,
    promo_code: str | None = None,
) -> int:
    order_number = get_next_order_number_db()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """INSERT INTO orders
                 (order_number, user_id, username, player_id, uc_amount, price, status, created_at,
                  completed_at, discount, promocode, product_type, product_name, quantity_text, target_value, target_type)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            order_number,
            user.id,
            user.username or "Нет username",
            target_value if target_type == "player_id" else None,
            uc_amount,
            price,
            "pending",
            str(datetime.now()),
            None,
            discount,
            promo_code,
            product_type,
            product_name,
            quantity_text,
            target_value,
            target_type,
        ),
    )
    if promo_code:
        c.execute("DELETE FROM user_promos WHERE user_id = ? AND promo_code = ?", (user.id, promo_code))
    conn.commit()
    conn.close()
    return order_number


async def create_order(**kwargs: Any) -> int:
    return await run_db(create_order_db, **kwargs)


def get_order_status_db(order_number: int) -> str | None:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT status FROM orders WHERE order_number = ?", (order_number,))
    row = c.fetchone()
    conn.close()
    return row["status"] if row else None


async def get_order_status(order_number: int) -> str | None:
    return await run_db(get_order_status_db, order_number)


def get_user_active_promo_db(user_id: int) -> dict[str, Any] | None:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT promo_code, discount FROM user_promos WHERE user_id = ? LIMIT 1", (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


async def get_user_active_promo(user_id: int) -> dict[str, Any] | None:
    return await run_db(get_user_active_promo_db, user_id)


def get_profile_data_db(user_id: int) -> dict[str, Any]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT username, first_name, total_orders FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    c.execute("SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'completed'", (user_id,))
    completed_orders = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'pending'", (user_id,))
    pending_orders = c.fetchone()[0]
    conn.close()
    return {
        "row": dict(row) if row else None,
        "completed_orders": completed_orders,
        "pending_orders": pending_orders,
    }


async def get_profile_data(user_id: int) -> dict[str, Any]:
    return await run_db(get_profile_data_db, user_id)


def get_admin_stats_db() -> dict[str, Any]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
    completed = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
    pending = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(price), 0) FROM orders WHERE status = 'completed'")
    earned = c.fetchone()[0]
    conn.close()
    return {
        "total_users": total_users,
        "total_orders": total_orders,
        "completed": completed,
        "pending": pending,
        "earned": earned,
    }


async def get_admin_stats() -> dict[str, Any]:
    return await run_db(get_admin_stats_db)


def get_promos_db() -> list[sqlite3.Row]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT code, discount, max_uses, used_count, expires_at, active FROM promocodes ORDER BY created_at DESC")
    promos = c.fetchall()
    conn.close()
    return promos


async def get_promos() -> list[sqlite3.Row]:
    return await run_db(get_promos_db)


def create_promo_db(code: str, discount: int, max_uses: int, expires_days: int) -> tuple[bool, str]:
    expires_at = None if expires_days == 0 else str(datetime.now() + timedelta(days=expires_days))
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO promocodes (code, discount, created_at, max_uses, used_count, expires_at, active) VALUES (?,?,?,?,?,?,1)",
            (code, discount, str(datetime.now()), max_uses, 0, expires_at),
        )
        conn.commit()
        return True, f"✅ Промокод <b>{escape_html(code)}</b> создан."
    except sqlite3.IntegrityError:
        return False, "❌ Такой промокод уже существует."
    finally:
        conn.close()


async def create_promo(code: str, discount: int, max_uses: int, expires_days: int) -> tuple[bool, str]:
    return await run_db(create_promo_db, code, discount, max_uses, expires_days)


def delete_promo_db(code: str) -> None:
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM promocodes WHERE code = ?", (code,))
    c.execute("DELETE FROM user_promos WHERE promo_code = ?", (code,))
    conn.commit()
    conn.close()


async def delete_promo(code: str) -> None:
    await run_db(delete_promo_db, code)


def get_all_user_ids_db() -> list[int]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    rows = c.fetchall()
    conn.close()
    return [row["user_id"] for row in rows]


async def get_all_user_ids() -> list[int]:
    return await run_db(get_all_user_ids_db)


def get_order_for_admin_db(order_number: int) -> dict[str, Any] | None:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """SELECT user_id, username, product_name, quantity_text, price, target_value, target_type
                 FROM orders WHERE order_number = ?""",
        (order_number,),
    )
    order = c.fetchone()
    conn.close()
    return dict(order) if order else None


async def get_order_for_admin(order_number: int) -> dict[str, Any] | None:
    return await run_db(get_order_for_admin_db, order_number)


def finalize_order_success_db(order_number: int) -> dict[str, Any] | None:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT user_id, product_type, product_name, quantity_text, target_value, uc_amount FROM orders WHERE order_number = ?",
        (order_number,),
    )
    order = c.fetchone()
    if not order:
        conn.close()
        return None

    c.execute(
        "UPDATE orders SET status = 'completed', completed_at = ? WHERE order_number = ?",
        (str(datetime.now()), order_number),
    )

    if order["product_type"] == "uc" and order["uc_amount"]:
        c.execute(
            "UPDATE users SET total_uc = total_uc + ?, total_orders = total_orders + 1 WHERE user_id = ?",
            (order["uc_amount"], order["user_id"]),
        )
    else:
        c.execute("UPDATE users SET total_orders = total_orders + 1 WHERE user_id = ?", (order["user_id"],))

    conn.commit()
    conn.close()
    return dict(order)


async def finalize_order_success(order_number: int) -> dict[str, Any] | None:
    return await run_db(finalize_order_success_db, order_number)


def finalize_order_denied_db(order_number: int) -> int | None:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE orders SET status = 'cancelled', completed_at = ? WHERE order_number = ?",
        (str(datetime.now()), order_number),
    )
    c.execute("SELECT user_id FROM orders WHERE order_number = ?", (order_number,))
    row = c.fetchone()
    conn.commit()
    conn.close()
    return row["user_id"] if row else None


async def finalize_order_denied(order_number: int) -> int | None:
    return await run_db(finalize_order_denied_db, order_number)


def cancel_pending_order_db(order_number: int) -> None:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE orders SET status = 'cancelled', completed_at = ? WHERE order_number = ? AND status = 'pending'",
        (str(datetime.now()), order_number),
    )
    conn.commit()
    conn.close()


async def cancel_pending_order(order_number: int) -> None:
    await run_db(cancel_pending_order_db, order_number)


def apply_user_promo_db(user_id: int, code: str) -> tuple[bool, str]:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT discount, max_uses, used_count, expires_at, code FROM promocodes WHERE UPPER(code) = ? AND active = 1",
        (code,),
    )
    promo = c.fetchone()
    if not promo:
        conn.close()
        return False, "❌ <b>Промокод не найден или неактивен.</b>"

    if promo["expires_at"]:
        exp = None
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                exp = datetime.strptime(promo["expires_at"], fmt)
                break
            except ValueError:
                continue
        if exp and datetime.now() > exp:
            conn.close()
            return False, "❌ <b>Срок действия промокода истёк.</b>"

    if promo["max_uses"] > 0 and promo["used_count"] >= promo["max_uses"]:
        conn.close()
        return False, "❌ <b>Лимит использований промокода исчерпан.</b>"

    c.execute("SELECT 1 FROM user_promos WHERE user_id = ? AND promo_code = ?", (user_id, promo["code"]))
    if c.fetchone():
        conn.close()
        return False, "❌ <b>Вы уже активировали этот промокод.</b>"

    c.execute("UPDATE promocodes SET used_count = used_count + 1 WHERE code = ?", (promo["code"],))
    c.execute(
        "INSERT INTO user_promos (user_id, promo_code, discount, activated_at) VALUES (?,?,?,?)",
        (user_id, promo["code"], promo["discount"], str(datetime.now())),
    )
    conn.commit()
    conn.close()
    return (
        True,
        f"{tg_emoji('5253558615842785529', '✅')} <b>Промокод активирован!</b>\n{tg_emoji('5206607081334906820', '🎁')} Ваша скидка: {promo['discount']}%\n\nСкидка применится к следующей покупке UC.",
    )


async def apply_user_promo(user_id: int, code: str) -> tuple[bool, str]:
    return await run_db(apply_user_promo_db, user_id, code)


# ---------- ЛОГИКА ----------
async def notify_admin_about_paid_order(bot: Bot, order_number: int) -> None:
    order = await get_order_for_admin(order_number)
    if not order:
        return

    username = order["username"] or "Нет username"
    user_display = f"@{escape_html(username)}" if username != "Нет username" else "Нет username"
    if order["target_type"] == "player_id":
        target_label = "PUBG ID"
    elif order["target_type"] == "gift":
        target_label = "Способ выдачи"
    else:
        target_label = "Telegram username"

    admin_text = [
        f"{tg_emoji('5375296873982604963', '💰')} <b>ПОДТВЕРЖДЕНИЕ ОПЛАТЫ №{order_number}</b>",
        "",
        f"{tg_emoji('5458789419014182183', '👤')} Пользователь: {user_display}",
        f"{tg_emoji('5307860772641309071', '🆔')} User ID: <code>{order['user_id']}</code>",
        f"{tg_emoji('5253542964981955943', '🛒')} Товар: {escape_html(order['product_name'])}",
    ]
    if order["quantity_text"]:
        admin_text.append(f"{tg_emoji('5854908544712707500', '📦')} Выбрано: {escape_html(order['quantity_text'])}")
    admin_text.extend(
        [
            f"{tg_emoji('5375296873982604963', '💰')} Сумма: {fmt_price(order['price'])} ₽",
            f"{target_label}: <code>{escape_html(order['target_value'] or '-')}</code>",
            "",
            f"{tg_emoji('5301038027601098171', '👇')} <b>Выберите действие:</b>",
        ]
    )

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                build_inline_button("Выполнил", f"admin_done_{order_number}", "5253558615842785529", "success"),
                build_inline_button("Отказать", f"admin_deny_{order_number}", "5255732655273570754", "danger"),
            ]
        ]
    )

    try:
        await bot.send_message(ADMIN_ID, "\n".join(admin_text), reply_markup=markup)
    except Exception:
        logging.exception("Не удалось отправить уведомление админу")


def normalize_username(text: str | None) -> str | None:
    username = (text or "").strip()
    if username.startswith("https://t.me/"):
        username = username.split("https://t.me/", 1)[1]
    username = username.lstrip("@").strip()
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
    if not username or len(username) < 5 or len(username) > 32:
        return None
    if any(ch not in allowed for ch in username):
        return None
    return "@" + username


async def safe_menu_error(callback: CallbackQuery, text: str = "❌ Произошла ошибка") -> None:
    try:
        await callback.answer(text)
    except Exception:
        pass


async def safe_replace_callback_message(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
        return
    except Exception:
        pass

    try:
        await callback.message.edit_caption(caption=text, reply_markup=reply_markup)
        return
    except Exception:
        pass

    try:
        await callback.message.answer(text, reply_markup=reply_markup)
    except Exception:
        logging.exception("Не удалось заменить сообщение callback")


# ---------- /start ----------
@router.message(CommandStart())
async def start_handler(message: Message, bot: Bot, state: FSMContext) -> None:
    await ensure_user(message.from_user)
    await state.clear()
    await send_or_update_main_menu(bot, message.chat.id, message.from_user.id, message.from_user.first_name or "Игрок")


@router.message(Command("menu"))
async def menu_command_handler(message: Message, bot: Bot, state: FSMContext) -> None:
    await ensure_user(message.from_user)
    await state.clear()
    await send_or_update_main_menu(bot, message.chat.id, message.from_user.id, message.from_user.first_name or "Игрок")


# ---------- АДМИНКА ----------
@router.message(Command("admin"))
async def admin_command_handler(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора!")
        return
    await state.clear()
    await message.answer("👨‍💼 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:", reply_markup=admin_keyboard())


@router.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=False)
        return

    stats = await get_admin_stats()
    text = (
        f"{tg_emoji('5402298269129334734', '📊')} <b>СТАТИСТИКА</b>\n\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"📦 Всего заказов: {stats['total_orders']}\n"
        f"✅ Выполнено: {stats['completed']}\n"
        f"⏳ В обработке: {stats['pending']}\n"
        f"💰 Заработано: {fmt_price(stats['earned'])} ₽"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[[build_inline_button("Назад", "admin_back", BACK_EMOJI_ID)]])
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data == "admin_promos")
async def admin_promos_handler(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=False)
        return

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                build_inline_button("➕ Создать", "promo_create"),
                build_inline_button("📋 Список", "promo_list"),
            ],
            [build_inline_button("🗑 Удалить", "promo_delete")],
            [build_inline_button("Назад", "admin_back", BACK_EMOJI_ID)],
        ]
    )
    await callback.message.edit_text("🎟 <b>Управление промокодами</b>", reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back_handler(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=False)
        return
    await callback.message.edit_text("👨‍💼 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:", reply_markup=admin_keyboard())
    await callback.answer()


@router.callback_query(F.data == "promo_create")
async def promo_create_step1(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=False)
        return
    await state.set_state(AdminFlow.promo_code)
    await callback.message.answer("🎟 <b>Создание промокода</b>\n\nВведите код промокода:")
    await callback.answer()


@router.message(AdminFlow.promo_code)
async def process_promo_code(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    code = (message.text or "").strip().upper()
    if not code:
        await message.answer("❌ Код не может быть пустым.")
        return
    await state.update_data(code=code)
    await state.set_state(AdminFlow.promo_discount)
    await message.answer(f"Код: {escape_html(code)}\nТеперь введите размер скидки (1-100):")


@router.message(AdminFlow.promo_discount)
async def process_promo_discount(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    try:
        discount = int(message.text or "")
        if discount < 1 or discount > 100:
            raise ValueError
    except Exception:
        await message.answer("❌ Введите целое число от 1 до 100.")
        return
    await state.update_data(discount=discount)
    await state.set_state(AdminFlow.promo_uses)
    await message.answer("Введите максимальное количество использований (0 - безлимит):")


@router.message(AdminFlow.promo_uses)
async def process_promo_uses(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    try:
        max_uses = int(message.text or "")
        if max_uses < 0:
            raise ValueError
    except Exception:
        await message.answer("❌ Введите корректное число.")
        return
    await state.update_data(max_uses=max_uses)
    await state.set_state(AdminFlow.promo_expiry)
    await message.answer("Введите срок действия в днях (0 - бессрочно):")


@router.message(AdminFlow.promo_expiry)
async def process_promo_expiry(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    try:
        days = int(message.text or "")
        if days < 0:
            raise ValueError
    except Exception:
        await message.answer("❌ Введите корректное число.")
        return

    data = await state.get_data()
    ok, response = await create_promo(data["code"], data["discount"], data["max_uses"], days)
    await state.clear()
    await message.answer(response)


@router.callback_query(F.data == "promo_list")
async def promo_list_handler(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=False)
        return
    promos = await get_promos()
    if not promos:
        text = "🎟 Промокодов пока нет."
    else:
        lines = ["🎟 <b>Список промокодов:</b>", ""]
        for p in promos:
            expiry = "бессрочно" if not p["expires_at"] else p["expires_at"][:10]
            limit = "безлимит" if p["max_uses"] == 0 else p["max_uses"]
            status = "✅ Активен" if p["active"] else "❌ Неактивен"
            lines.append(f"• <b>{escape_html(p['code'])}</b> — {p['discount']}% ({p['used_count']}/{limit}) {expiry} {status}")
        text = "\n".join(lines)
    markup = InlineKeyboardMarkup(inline_keyboard=[[build_inline_button("Назад", "admin_promos", BACK_EMOJI_ID)]])
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data == "promo_delete")
async def promo_delete_menu(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=False)
        return
    promos = await get_promos()
    rows: list[list[InlineKeyboardButton]] = []
    if not promos:
        rows.append([build_inline_button("Назад", "admin_promos", BACK_EMOJI_ID)])
        await callback.message.edit_text("🗑 <b>Удаление промокода</b>\n\nПромокодов пока нет.", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
        await callback.answer()
        return
    for promo in promos:
        rows.append([build_inline_button(f"{promo['code']} — {promo['discount']}%", f"promo_delete_select:{promo['code']}")])
    rows.append([build_inline_button("Назад", "admin_promos", BACK_EMOJI_ID)])
    await callback.message.edit_text(
        "🗑 <b>Удаление промокода</b>\n\nНажмите на промокод, чтобы удалить его:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("promo_delete_select:"))
async def promo_delete_select(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=False)
        return
    code = callback.data.split(":", 1)[1]
    await delete_promo(code)
    await callback.answer("✅ Промокод удалён")
    await promo_delete_menu(callback)


@router.callback_query(F.data == "admin_mailing")
async def admin_mailing_handler(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=False)
        return
    await state.set_state(AdminFlow.mailing_content)
    await callback.message.answer("📢 <b>Рассылка</b>\n\nОтправьте сообщение для рассылки. Можно текст или фото с подписью:")
    await callback.answer()


@router.message(AdminFlow.mailing_content, F.text | F.photo)
async def process_mailing_content(message: Message, state: FSMContext) -> None:
    global mailing_data
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    data: dict[str, Any] = {"type": None, "text": None, "photo": None, "caption": None}
    if message.photo:
        data["type"] = "photo"
        data["photo"] = message.photo[-1].file_id
        data["caption"] = (message.caption or "").strip()
    else:
        text = (message.text or "").strip()
        if not text:
            await message.answer("❌ Текст не может быть пустым.")
            return
        data["type"] = "text"
        data["text"] = text

    mailing_data = data
    preview_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                build_inline_button("Подтвердить", "mailing_confirm", "5253558615842785529", "success"),
                build_inline_button("Отмена", "mailing_cancel", "5255732655273570754", "danger"),
            ]
        ]
    )

    if data["type"] == "photo":
        await message.answer_photo(
            data["photo"],
            caption=f"📢 <b>Предпросмотр рассылки:</b>\n\n{escape_html(data['caption'] or '')}",
            reply_markup=preview_markup,
        )
    else:
        await message.answer(
            f"📢 <b>Предпросмотр рассылки:</b>\n\n{escape_html(data['text'])}",
            reply_markup=preview_markup,
        )


@router.callback_query(F.data.in_({"mailing_confirm", "mailing_cancel"}))
async def mailing_action(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    global mailing_data
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=False)
        return

    if callback.data == "mailing_cancel":
        mailing_data = None
        await state.clear()
        await safe_replace_callback_message(callback, "❌ Рассылка отменена.")
        await callback.answer()
        return

    if not mailing_data:
        await callback.answer("❌ Нет данных для рассылки", show_alert=False)
        return

    user_ids = await get_all_user_ids()
    sent = 0
    errors = 0
    for user_id in user_ids:
        try:
            if mailing_data["type"] == "photo":
                await bot.send_photo(user_id, mailing_data["photo"], caption=mailing_data["caption"] or None)
            else:
                await bot.send_message(user_id, mailing_data["text"])
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            errors += 1

    mailing_data = None
    await state.clear()
    await callback.message.answer(f"📢 <b>Рассылка завершена!</b>\n\n✅ Успешно: {sent}\n❌ Ошибок: {errors}")
    await callback.answer()


@router.message(AdminFlow.mailing_content)
async def mailing_invalid_content(message: Message) -> None:
    if is_admin(message.from_user.id):
        await message.answer("❌ Поддерживается только текст или фото с подписью.")


# ---------- CALLBACK МЕНЮ ----------
@router.callback_query(F.data == "back_main")
async def back_main_handler(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    await state.clear()
    await show_main_menu_for_user(bot, callback.from_user)
    await callback.answer()


@router.callback_query(F.data == "menu_all_games_stub")
async def menu_all_games_handler(callback: CallbackQuery, bot: Bot) -> None:
    await edit_menu(bot, callback.from_user.id, "<b>Выберите нужную игру</b>", all_games_keyboard())
    await callback.answer()


@router.callback_query(F.data == "brawl_stars_menu")
async def brawl_stars_menu_handler(callback: CallbackQuery, bot: Bot) -> None:
    rows = [[build_inline_button(f"{label} — {fmt_price(price)} ₽", f"bsel_{idx}", style="primary")] for idx, (label, price) in enumerate(BRAWL_STARS_ITEMS)]
    rows.append([build_inline_button("Назад", "menu_all_games_stub", BACK_EMOJI_ID)])
    await edit_menu(
        bot,
        callback.from_user.id,
        (
            "💎 <b>Brawl Stars</b>\n\n"
            "Выберете нужный товар который нужен вам.\n\n"
            f"Также можно купить любой Донат который есть в игре писать - @{SUPPORT_USERNAME}\n\n"
            "Мы отправим вам товар подарком.\n\n"
            "‼️ Важно чтобы я был у вас в друзьях 24 часа!!"
        ),
        InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(F.data == "clash_royale_menu")
async def clash_royale_menu_handler(callback: CallbackQuery, bot: Bot) -> None:
    rows = [[build_inline_button(f"{label} — {fmt_price(price)} ₽", f"crsel_{idx}", style="primary")] for idx, (label, price) in enumerate(CLASH_ROYALE_ITEMS)]
    rows.append([build_inline_button("Назад", "menu_all_games_stub", BACK_EMOJI_ID)])
    await edit_menu(
        bot,
        callback.from_user.id,
        (
            "👑 <b>Clash Royale</b>\n\n"
            "Выберете нужный товар который нужен вам.\n\n"
            f"Также можно купить любой Донат который есть в игре писать - @{SUPPORT_USERNAME}\n\n"
            "Мы отправим вам товар подарком.\n\n"
            "‼️ Важно чтобы я был у вас в друзьях 24 часа!!"
        ),
        InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bsel_"))
async def brawl_select_handler(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    idx = int(callback.data.split("_")[1])
    label, price = BRAWL_STARS_ITEMS[idx]
    order_number = await create_order(
        user=callback.from_user,
        product_type="game_gift",
        product_name="Brawl Stars",
        quantity_text=label,
        price=price,
        target_value="Подарком",
        target_type="gift",
    )
    await state.clear()
    await edit_menu(bot, callback.from_user.id, build_payment_text(order_number, "Brawl Stars", label, price, "Подарком", "gift"), payment_markup(order_number))
    await callback.answer()


@router.callback_query(F.data.startswith("crsel_"))
async def clash_select_handler(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    idx = int(callback.data.split("_")[1])
    label, price = CLASH_ROYALE_ITEMS[idx]
    order_number = await create_order(
        user=callback.from_user,
        product_type="game_gift",
        product_name="Clash Royale",
        quantity_text=label,
        price=price,
        target_value="Подарком",
        target_type="gift",
    )
    await state.clear()
    await edit_menu(bot, callback.from_user.id, build_payment_text(order_number, "Clash Royale", label, price, "Подарком", "gift"), payment_markup(order_number))
    await callback.answer()


@router.callback_query(F.data.startswith("game_stub_"))
async def game_stub_handler(callback: CallbackQuery, bot: Bot) -> None:
    await edit_menu(bot, callback.from_user.id, "🛠 <b>Пока что в разработке</b>", back_to_menu_markup())
    await callback.answer()


@router.callback_query(F.data == "menu_uc")
async def menu_uc_handler(callback: CallbackQuery, bot: Bot) -> None:
    rows = [[build_inline_button(f"{uc} UC — {fmt_price(price)} ₽", f"ucsel_{uc}", style="primary")] for uc, price in sorted(UC_PRICES.items())]
    rows.append([build_inline_button("Назад", "back_main", BACK_EMOJI_ID)])
    await edit_menu(bot, callback.from_user.id, f"{tg_emoji('5253542964981955943', '🛒')} <b>ВЫБЕРИТЕ ПАКЕТ UC</b>\n\nНажмите на нужный пакет ниже.", InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data.startswith("ucsel_"))
async def uc_select_handler(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    uc_amount = int(callback.data.split("_")[1])
    price = UC_PRICES[uc_amount]
    final_price = price
    promo_code = None
    discount = 0

    promo = await get_user_active_promo(callback.from_user.id)
    if promo:
        promo_code = promo["promo_code"]
        discount = promo["discount"]
        final_price = int(price * (100 - discount) / 100)

    text = (
        "🪪 <b>Введите ваш PUBG ID:</b>\n\n"
        f"🎮 Пакет: {uc_amount} UC\n"
        f"💰 Сумма: {fmt_price(final_price)} ₽"
    )
    if discount:
        text += f"\n🎟 Скидка {discount}% по промокоду"
    text += "\n\nID должен начинаться с цифры 5."

    markup = InlineKeyboardMarkup(inline_keyboard=[[build_inline_button("Отмена", "back_main", "5255732655273570754", "danger")]])
    await edit_menu(bot, callback.from_user.id, text, markup)
    await state.set_state(UserFlow.uc_player_id)
    await state.update_data(
        draft={
            "uc_amount": uc_amount,
            "price": final_price,
            "original_price": price,
            "discount": discount,
            "promo_code": promo_code,
        }
    )
    await callback.answer()


@router.callback_query(F.data == "menu_popularity")
async def menu_popularity_handler(callback: CallbackQuery, bot: Bot) -> None:
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [build_inline_button("Популярность", "pop_menu_pop_regular", "5253698266704408740", "primary")],
            [build_inline_button("Популярность для дома", "pop_menu_pop_home", "5253698266704408740", "success")],
            [build_inline_button("Популярность на последней минуте", "pop_menu_pop_last", "5253698266704408740", "danger")],
            [build_inline_button("Назад", "back_main", BACK_EMOJI_ID)],
        ]
    )
    await edit_menu(bot, callback.from_user.id, "<b>Выберите тип популярности</b>", markup)
    await callback.answer()


@router.callback_query(F.data.startswith("pop_menu_"))
async def popularity_submenu_handler(callback: CallbackQuery, bot: Bot) -> None:
    key = callback.data.replace("pop_menu_", "")
    config = POPULARITY_ITEMS[key]
    rows = [[build_inline_button(f"{label} — {fmt_price(price)} ₽", f"popsel_{key}_{idx}", style="primary")] for idx, (label, price) in enumerate(config["prices"])]
    rows.append([build_inline_button("Назад", "menu_popularity", BACK_EMOJI_ID)])
    await edit_menu(bot, callback.from_user.id, config["description"], InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data.startswith("popsel_"))
async def popularity_select_handler(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    payload = callback.data[len("popsel_"):]
    key, idx_str = payload.rsplit("_", 1)
    config = POPULARITY_ITEMS[key]
    qty, price = config["prices"][int(idx_str)]
    text = f"Вы выбрали: <b>{escape_html(qty)}</b>\n🪪 <b>Введите ваш PUBG ID:</b>"
    markup = InlineKeyboardMarkup(inline_keyboard=[[build_inline_button("Отмена", "back_main", "5255732655273570754", "danger")]])
    await edit_menu(bot, callback.from_user.id, text, markup)
    await state.set_state(UserFlow.pop_player_id)
    await state.update_data(
        draft={
            "category": key,
            "product_name": config["product_label"],
            "quantity_text": qty,
            "price": price,
        }
    )
    await callback.answer()


@router.callback_query(F.data == "menu_subs")
async def menu_subs_handler(callback: CallbackQuery, bot: Bot) -> None:
    rows = [[build_inline_button(f"{label} — {fmt_price(price)} ₽", f"subsel_{idx}", style="primary")] for idx, (label, price) in enumerate(SUBSCRIPTION_ITEMS)]
    rows.append([build_inline_button("Назад", "back_main", BACK_EMOJI_ID)])
    await edit_menu(bot, callback.from_user.id, SUBSCRIPTION_INFO_TEXT, InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data.startswith("subsel_"))
async def sub_select_handler(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    idx = int(callback.data.split("_")[1])
    label, price = SUBSCRIPTION_ITEMS[idx]
    text = f"Вы выбрали: <b>{escape_html(label)}</b>\n🪪 <b>Введите ваш PUBG ID:</b>"
    markup = InlineKeyboardMarkup(inline_keyboard=[[build_inline_button("Отмена", "back_main", "5255732655273570754", "danger")]])
    await edit_menu(bot, callback.from_user.id, text, markup)
    await state.set_state(UserFlow.sub_player_id)
    await state.update_data(draft={"product_name": label, "price": price})
    await callback.answer()


@router.callback_query(F.data == "menu_tgstars")
async def menu_tgstars_handler(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    text = (
        f"{tg_emoji('5208801655004350721', '⭐️')} <b>Telegram Stars</b>\n\n"
        "Минимальный заказ: 50\n\n"
        "Звёзды будут отправлены на указанный Telegram username анонимно.\n\n"
        f"{tg_emoji('5458685931777199791', '✏️')} <b>Введите Telegram username получателя</b> (с @ или без):"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[[build_inline_button("Назад", "back_main", BACK_EMOJI_ID)]])
    await edit_menu(bot, callback.from_user.id, text, markup)
    await state.set_state(UserFlow.tgstars_username)
    await callback.answer()


@router.callback_query(F.data == "menu_tgpremium")
async def menu_tgpremium_handler(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    text = (
        f"{tg_emoji('5309773986786220864', '✨')} <b>Telegram Premium</b>\n\n"
        f"{tg_emoji('5309773986786220864', '✨')} Подписка будет отправлена на указанный Telegram username анонимно.\n\n"
        f"{tg_emoji('5375296873982604963', '💰')} Цены:\n"
        "  • 3 месяца — 1150₽\n"
        "  • 6 месяцев — 1490₽\n"
        "  • 12 месяцев — 2550₽\n\n"
        f"{tg_emoji('5458685931777199791', '✏️')} Введите Telegram username получателя (с @ или без):"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[[build_inline_button("Назад", "back_main", BACK_EMOJI_ID)]])
    await edit_menu(bot, callback.from_user.id, text, markup)
    await state.set_state(UserFlow.tgpremium_username)
    await callback.answer()


@router.callback_query(F.data.startswith("tgpremium_period_"))
async def tgpremium_period_handler(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    idx = int(callback.data.split("_")[-1])
    label, price = TG_PREMIUM_ITEMS[idx]
    data = await state.get_data()
    draft = data.get("draft", {})
    username = draft.get("username")
    if not username:
        await state.clear()
        await show_main_menu_for_user(bot, callback.from_user)
        await callback.answer()
        return

    order_number = await create_order(
        user=callback.from_user,
        product_type="telegram_premium",
        product_name="Telegram Premium",
        quantity_text=label,
        price=price,
        target_value=username,
        target_type="telegram_username",
    )
    await state.clear()
    await edit_menu(
        bot,
        callback.from_user.id,
        build_payment_text(order_number, "Telegram Premium", label, price, username, "telegram_username"),
        payment_markup(order_number),
    )
    await callback.answer()


@router.callback_query(F.data == "menu_profile")
async def menu_profile_handler(callback: CallbackQuery, bot: Bot) -> None:
    profile = await get_profile_data(callback.from_user.id)
    row = profile["row"]
    username = row["username"] if row and row["username"] and row["username"] != "Нет username" else "Нет username"
    username_text = f"@{escape_html(username)}" if username != "Нет username" else "Нет username"
    total_orders = row["total_orders"] if row else 0
    text = (
        f"{tg_emoji('5458789419014182183', '👤')} <b>ПРОФИЛЬ</b>\n\n"
        f"{tg_emoji('5458789419014182183', '👤')} Telegram username: {username_text}\n"
        f"{tg_emoji('5307860772641309071', '🆔')} Telegram ID: <code>{callback.from_user.id}</code>\n\n"
        f"{tg_emoji('5854908544712707500', '📦')} Всего заказов: {total_orders}\n"
        f"{tg_emoji('5253558615842785529', '✅')} Куплено: {profile['completed_orders']}\n"
        f"{tg_emoji('5343663274117334560', '⏳')} В обработке: {profile['pending_orders']}"
    )
    await edit_menu(bot, callback.from_user.id, text, back_to_menu_markup())
    await callback.answer()


@router.callback_query(F.data == "menu_reviews")
async def menu_reviews_handler(callback: CallbackQuery, bot: Bot) -> None:
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [build_url_button("Перейти к отзывам", f"https://t.me/{REVIEWS_CHANNEL}", "5463289097336405244", "danger")],
            [build_inline_button("Назад", "back_main", BACK_EMOJI_ID)],
        ]
    )
    await edit_menu(bot, callback.from_user.id, f"{tg_emoji('5463289097336405244', '📝')} <b>Отзывы</b>\n\nНажмите кнопку ниже, чтобы открыть канал с отзывами.", markup)
    await callback.answer()


@router.callback_query(F.data == "menu_support")
async def menu_support_handler(callback: CallbackQuery, bot: Bot) -> None:
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [build_url_button("Написать в поддержку", f"https://t.me/{SUPPORT_USERNAME}", "5213179235996294999", "danger")],
            [build_inline_button("Назад", "back_main", BACK_EMOJI_ID)],
        ]
    )
    await edit_menu(bot, callback.from_user.id, f"{tg_emoji('5213179235996294999', '💬')} <b>Поддержка</b>\n\nРаботаем 24/7. Нажмите кнопку ниже.", markup)
    await callback.answer()


@router.callback_query(F.data == "menu_promo")
async def menu_promo_handler(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    markup = InlineKeyboardMarkup(inline_keyboard=[[build_inline_button("Отмена", "back_main", "5255732655273570754", "danger")]])
    await edit_menu(bot, callback.from_user.id, f"{tg_emoji('5377599075237502153', '🎟')} <b>Введите промокод:</b>", markup)
    await state.set_state(UserFlow.promo_input)
    await callback.answer()


@router.callback_query(F.data.startswith("paid_"))
async def paid_handler(callback: CallbackQuery, bot: Bot) -> None:
    order_number = int(callback.data.split("_")[1])
    status = await get_order_status(order_number)
    if not status:
        await callback.answer("❌ Заказ не найден", show_alert=False)
        await show_main_menu_for_user(bot, callback.from_user)
        return
    if status != "pending":
        await callback.answer("⚠️ Этот заказ уже обработан", show_alert=False)
        return

    text = (
        f"✅ <b>ЗАЯВКА ПРИНЯТА!</b>\n\n"
        f"📋 <b>ЗАКАЗ №{order_number}</b>\n\n"
        "✅ Ваша оплата проверяется.\n"
        "⏱ Ожидайте, оператор проверит платеж."
    )
    await edit_menu(bot, callback.from_user.id, text, back_to_menu_markup())
    await notify_admin_about_paid_order(bot, order_number)
    await callback.answer("✅ Отправили заявку администратору")


@router.callback_query(F.data.startswith("user_cancel_"))
async def user_cancel_handler(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    order_number = int(callback.data.split("_")[2])
    await cancel_pending_order(order_number)
    await state.clear()
    await show_main_menu_for_user(bot, callback.from_user)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_done_"))
async def admin_done_handler(callback: CallbackQuery, bot: Bot) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=False)
        return
    order_number = int(callback.data.split("_")[2])
    order = await finalize_order_success(order_number)
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=False)
        return

    review_markup = InlineKeyboardMarkup(
        inline_keyboard=[[build_url_button("Оставить отзыв", f"https://t.me/{REVIEWS_CHANNEL}", "5463289097336405244", "danger")]]
    )
    if order["product_type"] == "uc":
        user_text = (
            f"✅ <b>Ваш заказ №{order_number} выполнен!</b>\n\n"
            f"💰 <b>{order['quantity_text'] or str(order['uc_amount']) + ' UC'}</b> доставлены на аккаунт.\n\n"
            "Спасибо за покупку ❤️"
        )
    else:
        user_text = (
            f"✅ <b>Ваш заказ №{order_number} выполнен!</b>\n\n"
            f"💰 <b>{escape_html(order['product_name'])}</b> успешно оформлен.\n"
            f"📦 Выбрано: {escape_html(order['quantity_text'] or order['product_name'])}\n\n"
            "Спасибо за покупку ❤️"
        )

    await bot.send_message(order["user_id"], user_text, reply_markup=review_markup)
    await safe_replace_callback_message(callback, f"✅ <b>ЗАКАЗ №{order_number} ВЫПОЛНЕН</b>")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_deny_"))
async def admin_deny_handler(callback: CallbackQuery, bot: Bot) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=False)
        return
    order_number = int(callback.data.split("_")[2])
    order_user_id = await finalize_order_denied(order_number)
    if order_user_id:
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[build_url_button("Написать в поддержку", f"https://t.me/{SUPPORT_USERNAME}", "5213179235996294999", "danger")]]
        )
        await bot.send_message(order_user_id, f"❌ <b>Ваш заказ №{order_number} был отменён.</b>", reply_markup=markup)
    await safe_replace_callback_message(callback, f"❌ <b>ЗАКАЗ №{order_number} ОТМЕНЁН</b>")
    await callback.answer()


# ---------- ОБРАБОТКА ТЕКСТА ----------
@router.message(UserFlow.uc_player_id)
async def handle_uc_player_id(message: Message, bot: Bot, state: FSMContext) -> None:
    player_id = (message.text or "").strip()
    await delete_user_message(message)
    if not player_id.isdigit() or not player_id.startswith("5"):
        await edit_menu(
            bot,
            message.from_user.id,
            "❌ <b>Неверный PUBG ID.</b>\n\nВведите ID только цифрами. ID должен начинаться с 5.",
            InlineKeyboardMarkup(inline_keyboard=[[build_inline_button("Отмена", "back_main", "5255732655273570754", "danger")]]),
        )
        return

    data = await state.get_data()
    draft = data["draft"]
    order_number = await create_order(
        user=message.from_user,
        product_type="uc",
        product_name="UC",
        quantity_text=f"{draft['uc_amount']} UC",
        price=draft["price"],
        target_value=player_id,
        target_type="player_id",
        uc_amount=draft["uc_amount"],
        discount=draft.get("discount", 0),
        promo_code=draft.get("promo_code"),
    )
    await state.clear()
    await edit_menu(
        bot,
        message.from_user.id,
        build_payment_text(order_number, "UC", f"{draft['uc_amount']} UC", draft["price"], player_id, "player_id"),
        payment_markup(order_number),
    )


@router.message(UserFlow.pop_player_id)
async def handle_popularity_player_id(message: Message, bot: Bot, state: FSMContext) -> None:
    player_id = (message.text or "").strip()
    await delete_user_message(message)
    if not player_id.isdigit() or not player_id.startswith("5"):
        await edit_menu(
            bot,
            message.from_user.id,
            "❌ <b>Неверный PUBG ID.</b>\n\nВведите ID только цифрами. ID должен начинаться с 5.",
            InlineKeyboardMarkup(inline_keyboard=[[build_inline_button("Отмена", "back_main", "5255732655273570754", "danger")]]),
        )
        return

    data = await state.get_data()
    draft = data["draft"]
    order_number = await create_order(
        user=message.from_user,
        product_type="popularity",
        product_name=draft["product_name"],
        quantity_text=draft["quantity_text"],
        price=draft["price"],
        target_value=player_id,
        target_type="player_id",
    )
    await state.clear()
    await edit_menu(
        bot,
        message.from_user.id,
        build_payment_text(order_number, draft["product_name"], draft["quantity_text"], draft["price"], player_id, "player_id"),
        payment_markup(order_number),
    )


@router.message(UserFlow.sub_player_id)
async def handle_subscription_player_id(message: Message, bot: Bot, state: FSMContext) -> None:
    player_id = (message.text or "").strip()
    await delete_user_message(message)
    if not player_id.isdigit() or not player_id.startswith("5"):
        await edit_menu(
            bot,
            message.from_user.id,
            "❌ <b>Неверный PUBG ID.</b>\n\nВведите ID только цифрами. ID должен начинаться с 5.",
            InlineKeyboardMarkup(inline_keyboard=[[build_inline_button("Отмена", "back_main", "5255732655273570754", "danger")]]),
        )
        return

    data = await state.get_data()
    draft = data["draft"]
    order_number = await create_order(
        user=message.from_user,
        product_type="subscription",
        product_name="Подписки",
        quantity_text=draft["product_name"],
        price=draft["price"],
        target_value=player_id,
        target_type="player_id",
    )
    await state.clear()
    await edit_menu(
        bot,
        message.from_user.id,
        build_payment_text(order_number, "Подписки", draft["product_name"], draft["price"], player_id, "player_id"),
        payment_markup(order_number),
    )


@router.message(UserFlow.tgstars_username)
async def handle_tgstars_username(message: Message, bot: Bot, state: FSMContext) -> None:
    await delete_user_message(message)
    username = normalize_username(message.text)
    if not username:
        await edit_menu(
            bot,
            message.from_user.id,
            "❌ <b>Неверный username.</b>\n\nВведите Telegram username получателя с @ или без @.",
            InlineKeyboardMarkup(inline_keyboard=[[build_inline_button("Назад", "back_main", BACK_EMOJI_ID)]]),
        )
        return
    await state.set_state(UserFlow.tgstars_amount)
    await state.update_data(draft={"username": username})
    text = f"Получатель: <code>{escape_html(username)}</code>\n\n✏️ <b>Введите количество звёзд</b> (минимум 50):"
    await edit_menu(bot, message.from_user.id, text, InlineKeyboardMarkup(inline_keyboard=[[build_inline_button("Назад", "back_main", BACK_EMOJI_ID)]]))


@router.message(UserFlow.tgstars_amount)
async def handle_tgstars_amount(message: Message, bot: Bot, state: FSMContext) -> None:
    await delete_user_message(message)
    try:
        amount = int((message.text or "").strip())
        if amount < 50:
            raise ValueError
    except Exception:
        await edit_menu(
            bot,
            message.from_user.id,
            "❌ <b>Введите корректное количество звёзд.</b>\n\nМинимальный заказ: 50.",
            InlineKeyboardMarkup(inline_keyboard=[[build_inline_button("Назад", "back_main", BACK_EMOJI_ID)]]),
        )
        return
    data = await state.get_data()
    username = data["draft"]["username"]
    price = amount * 1.5
    order_number = await create_order(
        user=message.from_user,
        product_type="telegram_stars",
        product_name="Telegram Stars",
        quantity_text=f"{amount} звёзд",
        price=price,
        target_value=username,
        target_type="telegram_username",
    )
    await state.clear()
    await edit_menu(
        bot,
        message.from_user.id,
        build_payment_text(order_number, "Telegram Stars", f"{amount} звёзд", price, username, "telegram_username"),
        payment_markup(order_number),
    )


@router.message(UserFlow.tgpremium_username)
async def handle_tgpremium_username(message: Message, bot: Bot, state: FSMContext) -> None:
    await delete_user_message(message)
    username = normalize_username(message.text)
    if not username:
        await edit_menu(
            bot,
            message.from_user.id,
            "❌ <b>Неверный username.</b>\n\nВведите Telegram username получателя с @ или без @.",
            InlineKeyboardMarkup(inline_keyboard=[[build_inline_button("Назад", "back_main", BACK_EMOJI_ID)]]),
        )
        return

    await state.set_state(UserFlow.tgpremium_period)
    await state.update_data(draft={"username": username})
    text = f"{tg_emoji('5458789419014182183', '👤')} Получатель: <code>{escape_html(username)}</code>\n\n{tg_emoji('5309773986786220864', '💎')} <b>Выберите период подписки Telegram Premium:</b>"
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [build_inline_button("3 месяца — 1150₽", "tgpremium_period_0", style="primary")],
            [build_inline_button("6 месяцев — 1490₽", "tgpremium_period_1", style="primary")],
            [build_inline_button("12 месяцев — 2550₽", "tgpremium_period_2", style="primary")],
            [build_inline_button("Назад", "back_main", BACK_EMOJI_ID)],
        ]
    )
    await edit_menu(bot, message.from_user.id, text, markup)


@router.message(UserFlow.promo_input)
async def handle_user_promo(message: Message, bot: Bot, state: FSMContext) -> None:
    await delete_user_message(message)
    code = (message.text or "").strip().upper()
    ok, response = await apply_user_promo(message.from_user.id, code)
    await state.clear()
    await edit_menu(bot, message.from_user.id, response, back_to_menu_markup())


@router.callback_query()
async def fallback_callback_handler(callback: CallbackQuery, bot: Bot) -> None:
    await show_main_menu_for_user(bot, callback.from_user)
    await callback.answer("Меню обновлено")


# Ловим прочие сообщения только если пользователь в процессе диалога.
@router.message()
async def fallback_text_handler(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state:
        await message.answer("Используйте кнопки бота или завершите текущий шаг.")


async def on_startup(bot: Bot) -> None:
    await bot.delete_webhook(drop_pending_updates=True)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    init_db()

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await on_startup(bot)
    logging.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
    except Exception:
        traceback.print_exc()
        raise
