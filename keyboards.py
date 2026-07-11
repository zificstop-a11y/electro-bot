from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
import db

# ─── Главное меню ─────────────────────────────────────────────────────────────

def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌟 Люди мира электротранспорта")],
            [KeyboardButton(text="🔧 Запчасти"), KeyboardButton(text="🛵 Купить транспорт")],
            [KeyboardButton(text="🔨 Починка"), KeyboardButton(text="⭐ Отзывы")],
            [KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
        persistent=True,
    )

# ─── Категории каталога ───────────────────────────────────────────────────────

def catalog_categories_kb() -> InlineKeyboardMarkup:
    cats = db.get_categories()
    buttons = [[InlineKeyboardButton(text=c, callback_data=f"buy:cat:{c}")] for c in cats]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="nav:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def catalog_models_kb(category: str) -> InlineKeyboardMarkup:
    models = db.get_models(category)
    buttons = []
    for m in models:
        buttons.append([InlineKeyboardButton(text=m["name"], callback_data=f"buy:model:{m['id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="buy:back:cat")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ─── Типы транспорта (для запчастей) ─────────────────────────────────────────

TRANSPORT_TYPES = ["Электропитбайк", "Электросамокат", "Электровелосипед", "Гироскутер", "Моноколесо"]
BRANDS = ["Sur-Ron", "Kugoo", "Xiaomi", "Ninebot", "Midway", "Dualtron", "White Siberia"]
PART_CATEGORIES = [
    "🔋 Аккумулятор", "⚙️ Контроллер", "🛑 Тормоза", "💡 Фара",
    "🔩 Руль", "🌀 Подвеска", "🏗️ Рама", "🔌 Проводка", "💺 Сиденье",
]

def parts_type_kb() -> InlineKeyboardMarkup:
    btns = [[InlineKeyboardButton(text=t, callback_data=f"parts:type:{t}")] for t in TRANSPORT_TYPES]
    btns.append([InlineKeyboardButton(text="🔙 Назад", callback_data="nav:main")])
    return InlineKeyboardMarkup(inline_keyboard=btns)

def parts_brand_kb() -> InlineKeyboardMarkup:
    btns = []
    row = []
    for b in BRANDS:
        row.append(InlineKeyboardButton(text=b, callback_data=f"parts:brand:{b}"))
        if len(row) == 2:
            btns.append(row); row = []
    if row:
        btns.append(row)
    btns.append([InlineKeyboardButton(text="🔙 Назад", callback_data="parts:back:type")])
    return InlineKeyboardMarkup(inline_keyboard=btns)

def parts_category_kb() -> InlineKeyboardMarkup:
    btns = []
    row = []
    for c in PART_CATEGORIES:
        row.append(InlineKeyboardButton(text=c, callback_data=f"parts:cat:{c}"))
        if len(row) == 2:
            btns.append(row); row = []
    if row:
        btns.append(row)
    btns.append([InlineKeyboardButton(text="🔙 Назад", callback_data="parts:back:model")])
    return InlineKeyboardMarkup(inline_keyboard=btns)

# ─── Отзывы ───────────────────────────────────────────────────────────────────

def reviews_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Читать отзывы", callback_data="rev:read")],
        [InlineKeyboardButton(text="✍️ Написать отзыв", callback_data="rev:write")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="nav:main")],
    ])

def rating_kb() -> InlineKeyboardMarkup:
    stars = ["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=s, callback_data=f"rev:rating:{i+1}")] for i, s in enumerate(stars)
    ] + [[InlineKeyboardButton(text="🔙 Отмена", callback_data="nav:main")]])

# ─── Кнопка отмены ────────────────────────────────────────────────────────────

def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="nav:main")]
    ])

# ─── Люди ────────────────────────────────────────────────────────────────────

def people_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="nav:main")]
    ])

# ─── Админ-панель ─────────────────────────────────────────────────────────────

def admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="adm:stats")],
        [InlineKeyboardButton(text="💹 Проверить цены сейчас", callback_data="adm:checkprices")],
        [InlineKeyboardButton(text="📝 Обновить цены", callback_data="adm:prices")],
        [InlineKeyboardButton(text="➕ Добавить модель", callback_data="adm:addmodel")],
        [InlineKeyboardButton(text="🗑️ Удалить модель", callback_data="adm:delmodel")],
        [InlineKeyboardButton(text="🌟 Добавить человека", callback_data="adm:addperson")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="adm:broadcast")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="adm:close")],
    ])

def admin_models_kb(action: str) -> InlineKeyboardMarkup:
    """Список всех моделей для выбора (обновление цены / удаление)."""
    models = db.all_models_flat()
    btns = []
    for m in models:
        label = f"{m['name']} ({m['category']})"
        btns.append([InlineKeyboardButton(text=label, callback_data=f"adm:{action}:{m['id']}")])
    btns.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adm:back")])
    return InlineKeyboardMarkup(inline_keyboard=btns)

def admin_categories_kb(action: str) -> InlineKeyboardMarkup:
    cats = db.get_categories()
    btns = [[InlineKeyboardButton(text=c, callback_data=f"adm:{action}:{c}")] for c in cats]
    btns.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adm:back")])
    return InlineKeyboardMarkup(inline_keyboard=btns)
