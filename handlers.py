import re
import urllib.parse
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

import db
import ai_client
import price_checker
from keyboards import (
    main_menu, catalog_categories_kb, catalog_models_kb,
    parts_type_kb, parts_brand_kb, parts_category_kb,
    reviews_kb, rating_kb, cancel_kb, people_kb,
    admin_kb, admin_models_kb, admin_categories_kb,
)
from states import (
    BuyFlow, SparePartsFlow, RepairFlow, HelpFlow,
    ReviewWriteFlow, AdminPriceFlow, AdminAddModelFlow,
    AdminDeleteModelFlow, AdminAddPersonFlow, AdminBroadcastFlow,
)

router = Router()
ADMIN_ID = 1772786665
ADMIN_USERNAME = "zif_zsst"  # без @

# simple in-memory user counter
_seen_users: set[int] = set()


def _track(user_id: int) -> None:
    _seen_users.add(user_id)


def _admin_only(uid: int, username: str | None = None) -> bool:
    return uid == ADMIN_ID or (username or "").lstrip("@").lower() == ADMIN_USERNAME.lower()


def _search_links(query: str) -> str:
    q = urllib.parse.quote_plus(query)
    return (
        f"[Wildberries](https://www.wildberries.ru/catalog/0/search.aspx?search={q}) | "
        f"[Ozon](https://www.ozon.ru/search/?text={q}) | "
        f"[Avito](https://www.avito.ru/rossiya?q={q})"
    )


def _model_card(m: dict) -> str:
    links = _search_links(m["search_query"])
    price_fmt = f"{m['price']:,}".replace(",", " ")
    return (
        f"━━━━━━━━━━━━━━━\n"
        f"🛵 *{m['name']}*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"⚡ Мощность: {m['power']}\n"
        f"🔋 Запас хода: {m['range']}\n"
        f"⚖️ Вес: {m['weight']}\n"
        f"💰 Цена: от {price_fmt} руб\n"
        f"📅 Обновлено: {m['updated']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🛒 {links}\n"
        f"━━━━━━━━━━━━━━━"
    )


def _stars(n: int) -> str:
    return "⭐" * n + "☆" * (5 - n)


# ═══════════════════════════════════════════════════════════════
# /start
# ═══════════════════════════════════════════════════════════════

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    _track(uid)
    if uid == ADMIN_ID:
        await message.answer(
            "⚡ *SOS\_ELECTRO* — панель администратора\n\n"
            "Используй кнопки ниже или переключись в обычное меню.",
            parse_mode="MarkdownV2",
            reply_markup=main_menu(),
        )
        await message.answer("🛠️ *Панель администратора:*", parse_mode="MarkdownV2", reply_markup=admin_kb())
    else:
        await message.answer(
            "⚡ *SOS\_ELECTRO*\n\n"
            "Электротранспорт и запчасти\. Без воды — сразу к делу\.\n\n"
            "Выбирай:",
            parse_mode="MarkdownV2",
            reply_markup=main_menu(),
        )


# ═══════════════════════════════════════════════════════════════
# 🌟 Люди мира электротранспорта
# ═══════════════════════════════════════════════════════════════

@router.message(F.text == "🌟 Люди мира электротранспорта")
async def menu_people(message: Message, state: FSMContext):
    await state.clear()
    _track(message.from_user.id)
    people = db.get_people()
    if not people:
        await message.answer("Список пока пуст.", reply_markup=people_kb())
        return
    lines = ["🌟 *Люди мира электротранспорта*\n"]
    for i, p in enumerate(people, 1):
        line = f"{i}\\. *{_esc(p['name'])}*\n   {_esc(p['description'])}"
        if p.get("link"):
            line += f"\n   🔗 {_esc(p['link'])}"
        lines.append(line)
    await message.answer("\n\n".join(lines), parse_mode="MarkdownV2", reply_markup=people_kb())


# ═══════════════════════════════════════════════════════════════
# 🛵 Купить транспорт
# ═══════════════════════════════════════════════════════════════

@router.message(F.text == "🛵 Купить транспорт")
async def menu_buy(message: Message, state: FSMContext):
    await state.clear()
    _track(message.from_user.id)
    await state.set_state(BuyFlow.category)
    await message.answer(
        "🛵 *Купить транспорт*\n\nВыбирай категорию:",
        parse_mode="MarkdownV2",
        reply_markup=catalog_categories_kb(),
    )


@router.callback_query(BuyFlow.category, F.data.startswith("buy:cat:"))
async def buy_category(cb: CallbackQuery, state: FSMContext):
    cat = cb.data.split(":", 2)[2]
    await state.update_data(category=cat)
    await state.set_state(BuyFlow.model)
    await cb.message.edit_text(
        f"🛵 *{_esc(cat)}*\n\nВыбирай модель:",
        parse_mode="MarkdownV2",
        reply_markup=catalog_models_kb(cat),
    )
    await cb.answer()


@router.callback_query(BuyFlow.model, F.data.startswith("buy:model:"))
async def buy_model(cb: CallbackQuery, state: FSMContext):
    model_id = cb.data.split(":", 2)[2]
    m = db.get_model_by_id(model_id)
    await state.clear()
    if not m:
        await cb.answer("Модель не найдена", show_alert=True)
        return
    await cb.message.edit_text(_model_card(m), parse_mode="Markdown")
    await cb.message.answer("Выбирай дальше:", reply_markup=main_menu())
    await cb.answer()


@router.callback_query(F.data == "buy:back:cat")
async def buy_back_cat(cb: CallbackQuery, state: FSMContext):
    await state.set_state(BuyFlow.category)
    await cb.message.edit_text(
        "🛵 *Купить транспорт*\n\nВыбирай категорию:",
        parse_mode="MarkdownV2",
        reply_markup=catalog_categories_kb(),
    )
    await cb.answer()


# ═══════════════════════════════════════════════════════════════
# 🔧 Запчасти
# ═══════════════════════════════════════════════════════════════

@router.message(F.text == "🔧 Запчасти")
async def menu_parts(message: Message, state: FSMContext):
    await state.clear()
    _track(message.from_user.id)
    await state.set_state(SparePartsFlow.transport_type)
    await message.answer(
        "🔧 *Запчасти*\n\nКакой тип транспорта?",
        parse_mode="MarkdownV2",
        reply_markup=parts_type_kb(),
    )


@router.callback_query(SparePartsFlow.transport_type, F.data.startswith("parts:type:"))
async def parts_type(cb: CallbackQuery, state: FSMContext):
    t = cb.data.split(":", 2)[2]
    await state.update_data(transport_type=t)
    await state.set_state(SparePartsFlow.brand)
    await cb.message.edit_text(
        f"🔧 Тип: *{_esc(t)}*\n\nВыбирай бренд:",
        parse_mode="MarkdownV2",
        reply_markup=parts_brand_kb(),
    )
    await cb.answer()


@router.callback_query(SparePartsFlow.brand, F.data.startswith("parts:brand:"))
async def parts_brand(cb: CallbackQuery, state: FSMContext):
    brand = cb.data.split(":", 2)[2]
    await state.update_data(brand=brand)
    await state.set_state(SparePartsFlow.model)
    d = await state.get_data()
    await cb.message.edit_text(
        f"🔧 {_esc(d['transport_type'])} → *{_esc(brand)}*\n\n"
        "Напиши модель \\(например: Light Bee X, Thunder 2\\) или «не знаю»:",
        parse_mode="MarkdownV2",
        reply_markup=cancel_kb(),
    )
    await cb.answer()


@router.message(SparePartsFlow.model)
async def parts_model(message: Message, state: FSMContext):
    await state.update_data(model=message.text)
    await state.set_state(SparePartsFlow.part_category)
    d = await state.get_data()
    await message.answer(
        f"🔧 {_esc(d['transport_type'])} → {_esc(d['brand'])} → *{_esc(message.text)}*\n\n"
        "Выбирай категорию запчасти:",
        parse_mode="MarkdownV2",
        reply_markup=parts_category_kb(),
    )


@router.callback_query(SparePartsFlow.part_category, F.data.startswith("parts:cat:"))
async def parts_category(cb: CallbackQuery, state: FSMContext):
    cat = cb.data.split(":", 2)[2]
    d = await state.get_data()
    await state.clear()
    await cb.message.edit_text(
        f"⏳ Ищу *{_esc(cat)}* для {_esc(d['brand'])} {_esc(d['model'])}\\.\\.\\.",
        parse_mode="MarkdownV2",
    )
    await cb.answer()
    result = await ai_client.ask_parts(d["transport_type"], d["brand"], d["model"], cat)
    await cb.message.answer(result, parse_mode="Markdown", reply_markup=main_menu())


@router.callback_query(F.data == "parts:back:type")
async def parts_back_type(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SparePartsFlow.transport_type)
    await cb.message.edit_text(
        "🔧 *Запчасти*\n\nКакой тип транспорта?",
        parse_mode="MarkdownV2",
        reply_markup=parts_type_kb(),
    )
    await cb.answer()


@router.callback_query(F.data == "parts:back:model")
async def parts_back_model(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SparePartsFlow.model)
    await cb.message.edit_text(
        "🔧 Напиши модель или «не знаю»:",
        parse_mode="MarkdownV2",
        reply_markup=cancel_kb(),
    )
    await cb.answer()


# ═══════════════════════════════════════════════════════════════
# 🔨 Починка
# ═══════════════════════════════════════════════════════════════

@router.message(F.text == "🔨 Починка")
async def menu_repair(message: Message, state: FSMContext):
    await state.clear()
    _track(message.from_user.id)
    await state.set_state(RepairFlow.question)
    await message.answer(
        "🔨 *Починка*\n\nОпиши проблему — диагностирую и скажу что делать:",
        parse_mode="MarkdownV2",
        reply_markup=cancel_kb(),
    )


@router.message(RepairFlow.question)
async def repair_question(message: Message, state: FSMContext):
    await state.clear()
    thinking = await message.answer("🔧 Диагностирую...")
    result = await ai_client.ask_repair(message.text)
    await thinking.delete()
    await message.answer(result, parse_mode="Markdown", reply_markup=main_menu())


# ═══════════════════════════════════════════════════════════════
# ❓ Помощь
# ═══════════════════════════════════════════════════════════════

@router.message(F.text == "❓ Помощь")
async def menu_help(message: Message, state: FSMContext):
    await state.clear()
    _track(message.from_user.id)
    await state.set_state(HelpFlow.question)
    await message.answer(
        "❓ *Помощь*\n\nЗадавай вопрос:",
        parse_mode="MarkdownV2",
        reply_markup=cancel_kb(),
    )


@router.message(HelpFlow.question)
async def help_question(message: Message, state: FSMContext):
    await state.clear()
    thinking = await message.answer("⏳ Думаю...")
    result = await ai_client.ask_help(message.text)
    await thinking.delete()
    await message.answer(result, parse_mode="Markdown", reply_markup=main_menu())


# ═══════════════════════════════════════════════════════════════
# ⭐ Отзывы
# ═══════════════════════════════════════════════════════════════

@router.message(F.text == "⭐ Отзывы")
async def menu_reviews(message: Message, state: FSMContext):
    await state.clear()
    _track(message.from_user.id)
    await message.answer(
        "⭐ *Отзывы*\n\nЧитай чужой опыт или делись своим:",
        parse_mode="MarkdownV2",
        reply_markup=reviews_kb(),
    )


@router.callback_query(F.data == "rev:read")
async def reviews_read(cb: CallbackQuery, state: FSMContext):
    reviews = db.get_latest_reviews(5)
    if not reviews:
        await cb.message.edit_text(
            "⭐ Отзывов пока нет\\. Будь первым\\!",
            parse_mode="MarkdownV2",
            reply_markup=reviews_kb(),
        )
        await cb.answer()
        return
    lines = ["⭐ *Последние отзывы:*\n"]
    for r in reviews:
        stars = _stars(r.get("rating", 5))
        name = _esc(r.get("username") or "Аноним")
        transport = _esc(r.get("transport", ""))
        text = _esc(r.get("text", ""))
        date_str = _esc(r.get("date", ""))
        lines.append(
            f"{stars}\n"
            f"👤 {name} — {transport}\n"
            f"💬 {text}\n"
            f"📅 {date_str}"
        )
    await cb.message.edit_text(
        "\n\n".join(lines),
        parse_mode="MarkdownV2",
        reply_markup=reviews_kb(),
    )
    await cb.answer()


@router.callback_query(F.data == "rev:write")
async def reviews_write_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(ReviewWriteFlow.transport)
    await cb.message.edit_text(
        "✍️ *Новый отзыв*\n\nО каком транспорте пишешь? \\(название модели\\)",
        parse_mode="MarkdownV2",
        reply_markup=cancel_kb(),
    )
    await cb.answer()


@router.message(ReviewWriteFlow.transport)
async def review_transport(message: Message, state: FSMContext):
    await state.update_data(transport=message.text)
    await state.set_state(ReviewWriteFlow.rating)
    await message.answer(
        f"✍️ *{_esc(message.text)}*\n\nСтавь оценку:",
        parse_mode="MarkdownV2",
        reply_markup=rating_kb(),
    )


@router.callback_query(ReviewWriteFlow.rating, F.data.startswith("rev:rating:"))
async def review_rating(cb: CallbackQuery, state: FSMContext):
    rating = int(cb.data.split(":")[2])
    await state.update_data(rating=rating)
    await state.set_state(ReviewWriteFlow.text)
    await cb.message.edit_text(
        f"✍️ Оценка: {_stars(rating)}\n\nТеперь напиши отзыв текстом:",
        parse_mode="MarkdownV2",
        reply_markup=cancel_kb(),
    )
    await cb.answer()


@router.message(ReviewWriteFlow.text)
async def review_text(message: Message, state: FSMContext):
    d = await state.get_data()
    await state.clear()
    review = {
        "transport": d["transport"],
        "rating": d["rating"],
        "text": message.text,
        "username": message.from_user.username or message.from_user.first_name,
        "user_id": message.from_user.id,
        "date": datetime.now().strftime("%d.%m.%Y"),
    }
    db.add_review(review)
    await message.answer(
        f"✅ Отзыв о *{_esc(d['transport'])}* сохранён\\! {_stars(d['rating'])}",
        parse_mode="MarkdownV2",
        reply_markup=main_menu(),
    )


# ═══════════════════════════════════════════════════════════════
# Навигация «Назад» / Главное меню
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "nav:main")
async def nav_main(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await cb.message.delete()
    except Exception:
        pass
    await cb.message.answer("Главное меню:", reply_markup=main_menu())
    await cb.answer()


# ═══════════════════════════════════════════════════════════════
# ADMIN — инлайн-панель
# ═══════════════════════════════════════════════════════════════


@router.callback_query(F.data == "adm:checkprices")
async def adm_check_prices(cb: CallbackQuery):
    if not _admin_only(cb.from_user.id, cb.from_user.username):
        await cb.answer("Нет доступа", show_alert=True); return
    await cb.answer()
    await cb.message.edit_text(
        "🔍 *Ищу актуальные цены на WB и Ozon\\.\\.\\.*\n\n"
        "⏳ Проверяю все модели — займёт 10\\-30 секунд\\.",
        parse_mode="MarkdownV2",
    )
    results = await price_checker.check_and_update_all()
    lines = ["💹 *Проверка цен завершена:*\n"]
    for r in results:
        old_fmt = f"{r['old_price']:,}".replace(",", " ")
        if r["new_price"]:
            new_fmt = f"{r['new_price']:,}".replace(",", " ")
            wb_str = f"{r['wb_price']:,}".replace(",", " ") + " руб" if r["wb_price"] else "—"
            oz_str = f"{r['ozon_price']:,}".replace(",", " ") + " руб" if r["ozon_price"] else "—"
            lines.append(
                f"{r['status']} *{_esc(r['name'])}*\n"
                f"   Было: {old_fmt} руб → Стало: *{new_fmt} руб*\n"
                f"   WB: {_esc(wb_str)} \\| Ozon: {_esc(oz_str)}"
            )
        else:
            lines.append(
                f"❓ *{_esc(r['name'])}*\n"
                f"   Цена в базе: {old_fmt} руб \\| На маркетплейсах не найдено"
            )
    lines.append("\n✅ База данных обновлена автоматически\\.")
    await cb.message.edit_text(
        "\n\n".join(lines),
        parse_mode="MarkdownV2",
        reply_markup=admin_kb(),
    )


@router.callback_query(F.data == "adm:stats")
async def adm_stats(cb: CallbackQuery):
    if not _admin_only(cb.from_user.id, cb.from_user.username):
        await cb.answer("Нет доступа", show_alert=True); return
    models_count = len(db.all_models_flat())
    reviews_count = len(db.get_reviews())
    people_count = len(db.get_people())
    await cb.message.edit_text(
        f"📊 *Статистика SOS\_ELECTRO*\n\n"
        f"👤 Уникальных пользователей: *{len(_seen_users)}*\n"
        f"🛵 Моделей в базе: *{models_count}*\n"
        f"⭐ Отзывов: *{reviews_count}*\n"
        f"🌟 Людей мира: *{people_count}*",
        parse_mode="MarkdownV2",
        reply_markup=admin_kb(),
    )
    await cb.answer()


@router.callback_query(F.data == "adm:prices")
async def adm_prices(cb: CallbackQuery, state: FSMContext):
    if not _admin_only(cb.from_user.id, cb.from_user.username):
        await cb.answer("Нет доступа", show_alert=True); return
    await state.set_state(AdminPriceFlow.choose_model)
    await cb.message.edit_text(
        "📝 *Обновить цену*\n\nВыбери модель:",
        parse_mode="MarkdownV2",
        reply_markup=admin_models_kb("price"),
    )
    await cb.answer()


@router.callback_query(AdminPriceFlow.choose_model, F.data.startswith("adm:price:"))
async def adm_price_choose(cb: CallbackQuery, state: FSMContext):
    model_id = cb.data.split(":", 2)[2]
    m = db.get_model_by_id(model_id)
    if not m:
        await cb.answer("Модель не найдена", show_alert=True); return
    await state.update_data(model_id=model_id, model_name=m["name"])
    await state.set_state(AdminPriceFlow.enter_price)
    await cb.message.edit_text(
        f"📝 *{_esc(m['name'])}*\n\nТекущая цена: {m['price']:,} руб\n\nВведи новую цену \\(только цифры\\):",
        parse_mode="MarkdownV2",
        reply_markup=cancel_kb(),
    )
    await cb.answer()


@router.message(AdminPriceFlow.enter_price)
async def adm_price_enter(message: Message, state: FSMContext):
    if not _admin_only(message.from_user.id, message.from_user.username): return
    text = message.text.strip().replace(" ", "").replace(",", "")
    if not text.isdigit():
        await message.answer("❌ Только цифры\\. Попробуй ещё раз:", parse_mode="MarkdownV2"); return
    d = await state.get_data()
    db.update_price(d["model_id"], int(text))
    await state.clear()
    price_fmt = f"{int(text):,}".replace(",", " ")
    await message.answer(
        f"✅ Цена *{_esc(d['model_name'])}* обновлена: *{price_fmt} руб*",
        parse_mode="MarkdownV2",
        reply_markup=main_menu(),
    )
    await message.answer("🛠️ Панель:", reply_markup=admin_kb())


@router.callback_query(F.data == "adm:delmodel")
async def adm_del_model(cb: CallbackQuery, state: FSMContext):
    if not _admin_only(cb.from_user.id, cb.from_user.username):
        await cb.answer("Нет доступа", show_alert=True); return
    await state.set_state(AdminDeleteModelFlow.choose_model)
    await cb.message.edit_text(
        "🗑️ *Удалить модель*\n\nВыбери:",
        parse_mode="MarkdownV2",
        reply_markup=admin_models_kb("del"),
    )
    await cb.answer()


@router.callback_query(AdminDeleteModelFlow.choose_model, F.data.startswith("adm:del:"))
async def adm_del_confirm(cb: CallbackQuery, state: FSMContext):
    model_id = cb.data.split(":", 2)[2]
    m = db.get_model_by_id(model_id)
    if not m:
        await cb.answer("Не найдена", show_alert=True); return
    ok = db.delete_model(model_id)
    await state.clear()
    if ok:
        await cb.message.edit_text(
            f"✅ *{_esc(m['name'])}* удалена из базы\\.",
            parse_mode="MarkdownV2",
            reply_markup=admin_kb(),
        )
    else:
        await cb.message.edit_text("❌ Ошибка удаления\\.", parse_mode="MarkdownV2", reply_markup=admin_kb())
    await cb.answer()


@router.callback_query(F.data == "adm:addmodel")
async def adm_add_model_start(cb: CallbackQuery, state: FSMContext):
    if not _admin_only(cb.from_user.id, cb.from_user.username):
        await cb.answer("Нет доступа", show_alert=True); return
    await state.set_state(AdminAddModelFlow.category)
    await cb.message.edit_text(
        "➕ *Добавить модель*\n\nВыбери категорию:",
        parse_mode="MarkdownV2",
        reply_markup=admin_categories_kb("newcat"),
    )
    await cb.answer()


@router.callback_query(AdminAddModelFlow.category, F.data.startswith("adm:newcat:"))
async def adm_add_model_cat(cb: CallbackQuery, state: FSMContext):
    cat = cb.data.split(":", 2)[2]
    await state.update_data(category=cat)
    await state.set_state(AdminAddModelFlow.name)
    await cb.message.edit_text(
        f"➕ Категория: *{_esc(cat)}*\n\nВведи название модели:",
        parse_mode="MarkdownV2",
        reply_markup=cancel_kb(),
    )
    await cb.answer()


@router.message(AdminAddModelFlow.name)
async def adm_add_model_name(message: Message, state: FSMContext):
    if not _admin_only(message.from_user.id, message.from_user.username): return
    await state.update_data(name=message.text)
    await state.set_state(AdminAddModelFlow.power)
    await message.answer("⚡ Мощность \\(например: 6000 Вт\\):", parse_mode="MarkdownV2", reply_markup=cancel_kb())


@router.message(AdminAddModelFlow.power)
async def adm_add_model_power(message: Message, state: FSMContext):
    if not _admin_only(message.from_user.id, message.from_user.username): return
    await state.update_data(power=message.text)
    await state.set_state(AdminAddModelFlow.range_)
    await message.answer("🔋 Запас хода \\(например: 90 км\\):", parse_mode="MarkdownV2", reply_markup=cancel_kb())


@router.message(AdminAddModelFlow.range_)
async def adm_add_model_range(message: Message, state: FSMContext):
    if not _admin_only(message.from_user.id, message.from_user.username): return
    await state.update_data(range_=message.text)
    await state.set_state(AdminAddModelFlow.weight)
    await message.answer("⚖️ Вес \\(например: 50 кг\\):", parse_mode="MarkdownV2", reply_markup=cancel_kb())


@router.message(AdminAddModelFlow.weight)
async def adm_add_model_weight(message: Message, state: FSMContext):
    if not _admin_only(message.from_user.id, message.from_user.username): return
    await state.update_data(weight=message.text)
    await state.set_state(AdminAddModelFlow.price)
    await message.answer("💰 Цена в рублях \\(только цифры\\):", parse_mode="MarkdownV2", reply_markup=cancel_kb())


@router.message(AdminAddModelFlow.price)
async def adm_add_model_price(message: Message, state: FSMContext):
    if not _admin_only(message.from_user.id, message.from_user.username): return
    text = message.text.strip().replace(" ", "").replace(",", "")
    if not text.isdigit():
        await message.answer("❌ Только цифры:", parse_mode="MarkdownV2"); return
    d = await state.get_data()
    await state.clear()
    model_id = re.sub(r"[^a-z0-9_]", "_", d["name"].lower().replace(" ", "_"))
    search_query = d["name"]
    new_model = {
        "id": model_id,
        "name": d["name"],
        "power": d["power"],
        "range": d["range_"],
        "weight": d["weight"],
        "price": int(text),
        "updated": datetime.now().strftime("%Y-%m-%d"),
        "search_query": search_query,
    }
    db.add_model(d["category"], new_model)
    await message.answer(
        f"✅ *{_esc(d['name'])}* добавлена в *{_esc(d['category'])}*\\!",
        parse_mode="MarkdownV2",
        reply_markup=main_menu(),
    )
    await message.answer("🛠️ Панель:", reply_markup=admin_kb())


# ─── Добавить человека ────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:addperson")
async def adm_add_person_start(cb: CallbackQuery, state: FSMContext):
    if not _admin_only(cb.from_user.id, cb.from_user.username):
        await cb.answer("Нет доступа", show_alert=True); return
    await state.set_state(AdminAddPersonFlow.name)
    await cb.message.edit_text(
        "🌟 *Добавить человека*\n\nВведи имя:",
        parse_mode="MarkdownV2",
        reply_markup=cancel_kb(),
    )
    await cb.answer()


@router.message(AdminAddPersonFlow.name)
async def adm_person_name(message: Message, state: FSMContext):
    if not _admin_only(message.from_user.id, message.from_user.username): return
    await state.update_data(name=message.text)
    await state.set_state(AdminAddPersonFlow.description)
    await message.answer("📝 Описание \\(пара слов кто это\\):", parse_mode="MarkdownV2", reply_markup=cancel_kb())


@router.message(AdminAddPersonFlow.description)
async def adm_person_desc(message: Message, state: FSMContext):
    if not _admin_only(message.from_user.id, message.from_user.username): return
    await state.update_data(description=message.text)
    await state.set_state(AdminAddPersonFlow.link)
    await message.answer(
        "🔗 Ссылка \\(канал, страница\\) или напиши «нет»:",
        parse_mode="MarkdownV2",
        reply_markup=cancel_kb(),
    )


@router.message(AdminAddPersonFlow.link)
async def adm_person_link(message: Message, state: FSMContext):
    if not _admin_only(message.from_user.id, message.from_user.username): return
    d = await state.get_data()
    await state.clear()
    link = "" if message.text.lower() == "нет" else message.text
    db.add_person({"name": d["name"], "description": d["description"], "link": link})
    await message.answer(
        f"✅ *{_esc(d['name'])}* добавлен в список\\!",
        parse_mode="MarkdownV2",
        reply_markup=main_menu(),
    )
    await message.answer("🛠️ Панель:", reply_markup=admin_kb())


# ─── Рассылка ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:broadcast")
async def adm_broadcast_start(cb: CallbackQuery, state: FSMContext):
    if not _admin_only(cb.from_user.id, cb.from_user.username):
        await cb.answer("Нет доступа", show_alert=True); return
    await state.set_state(AdminBroadcastFlow.text)
    await cb.message.edit_text(
        "📢 *Рассылка*\n\nНапиши текст для всех пользователей:",
        parse_mode="MarkdownV2",
        reply_markup=cancel_kb(),
    )
    await cb.answer()


@router.message(AdminBroadcastFlow.text)
async def adm_broadcast_send(message: Message, state: FSMContext):
    if not _admin_only(message.from_user.id, message.from_user.username): return
    await state.clear()
    await message.answer(
        f"📢 Текст принят\\. Разослать *{len(_seen_users)}* пользователям\\?\n\n"
        f"\\(В текущей версии — без постоянного хранилища ID\\. "
        f"Для полноценной рассылки подключи БД\\.\\)",
        parse_mode="MarkdownV2",
        reply_markup=admin_kb(),
    )


@router.callback_query(F.data == "adm:close")
async def adm_close(cb: CallbackQuery):
    await cb.message.delete()
    await cb.answer("Панель закрыта")


@router.callback_query(F.data == "adm:back")
async def adm_back(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("🛠️ *Панель администратора:*", parse_mode="MarkdownV2", reply_markup=admin_kb())
    await cb.answer()


# ═══════════════════════════════════════════════════════════════
# Команды администратора
# ═══════════════════════════════════════════════════════════════

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not _admin_only(message.from_user.id, message.from_user.username):
        await message.answer("⛔ Нет доступа.")
        return
    await state.clear()
    await message.answer("🛠️ *Панель администратора:*", parse_mode="MarkdownV2", reply_markup=admin_kb())


@router.message(Command("updateprice"))
async def cmd_updateprice(message: Message, state: FSMContext):
    if not _admin_only(message.from_user.id, message.from_user.username): return
    await state.set_state(AdminPriceFlow.choose_model)
    await message.answer(
        "📝 *Обновить цену*\n\nВыбери модель:",
        parse_mode="MarkdownV2",
        reply_markup=admin_models_kb("price"),
    )


@router.message(Command("addmodel"))
async def cmd_addmodel(message: Message, state: FSMContext):
    if not _admin_only(message.from_user.id, message.from_user.username): return
    await state.set_state(AdminAddModelFlow.category)
    await message.answer(
        "➕ *Добавить модель*\n\nВыбери категорию:",
        parse_mode="MarkdownV2",
        reply_markup=admin_categories_kb("newcat"),
    )


@router.message(Command("deletemodel"))
async def cmd_deletemodel(message: Message, state: FSMContext):
    if not _admin_only(message.from_user.id, message.from_user.username): return
    await state.set_state(AdminDeleteModelFlow.choose_model)
    await message.answer(
        "🗑️ *Удалить модель*\n\nВыбери:",
        parse_mode="MarkdownV2",
        reply_markup=admin_models_kb("del"),
    )


@router.message(Command("addperson"))
async def cmd_addperson(message: Message, state: FSMContext):
    if not _admin_only(message.from_user.id, message.from_user.username): return
    await state.set_state(AdminAddPersonFlow.name)
    await message.answer(
        "🌟 *Добавить человека*\n\nВведи имя:",
        parse_mode="MarkdownV2",
        reply_markup=cancel_kb(),
    )


# ─── Утилита: экранирование MarkdownV2 ───────────────────────────────────────

_ESC = re.compile(r"([_\*\[\]\(\)~`>#+\-=|{}.!\\])")

def _esc(text: str) -> str:
    return _ESC.sub(r"\\\1", str(text))
