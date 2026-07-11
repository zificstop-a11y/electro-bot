"""Groq AI — только для советов по запчастям, ремонту и свободным вопросам.
Продукты/цены/ссылки — строго из базы данных, не из AI."""
import os
import httpx

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

PARTS_SYSTEM = """Ты — SOS_ELECTRO, эксперт по запчастям для электротранспорта.
Тон: жёсткий, по делу, без лишних слов.

Твоя задача — дать технический совет по выбору запчасти. Никогда не выдумывай цены и не давай прямые ссылки на товары.
Вместо цен пиши: «цена уточняется у продавца».
Вместо ссылок давай поисковые запросы: напиши что именно искать на Wildberries, Ozon, Avito.

ФОРМАТ ответа:
━━━━━━━━━━━━━━━
🔧 [Название запчасти / артикул]
━━━━━━━━━━━━━━━
📋 Что это: [одна строка]
📦 Совместимость: [модели]
⚠️ На что смотреть при покупке: [2-3 пункта]
🔍 Искать: "[точный поисковый запрос]" на WB / Ozon / Avito
━━━━━━━━━━━━━━━

Дай 2-3 варианта. Только реальные запчасти. Отвечай по-русски."""

REPAIR_SYSTEM = """Ты — SOS_ELECTRO, мастер по ремонту электротранспорта.
Тон: прямой, конкретный, без воды.

Диагностируй проблему и дай пошаговый совет по ремонту.
Не выдумывай цены на запчасти. Если нужна деталь — скажи как она называется и где искать.
Отвечай на русском языке."""

HELP_SYSTEM = """Ты — SOS_ELECTRO, эксперт по электротранспорту.
Тон: жёсткий, по делу, без «пожалуйста».

Отвечай на вопросы об электросамокатах, электропитбайках, уходе, эксплуатации, законодательстве.
Не выдумывай цены. Отвечай на русском языке."""


async def _call(system: str, user_message: str) -> str:
    if not GROQ_API_KEY:
        return "❌ GROQ_API_KEY не задан!"
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 1500,
        "temperature": 0.6,
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(GROQ_URL, json=payload, headers=headers)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as e:
        return f"❌ Groq API ошибка {e.response.status_code}. Попробуй позже."
    except Exception as e:
        return f"❌ Ошибка соединения: {e}"


async def ask_parts(transport_type: str, brand: str, model: str, part_cat: str) -> str:
    prompt = (
        f"Тип транспорта: {transport_type}\n"
        f"Бренд: {brand}\n"
        f"Модель: {model}\n"
        f"Нужна запчасть: {part_cat}\n\n"
        f"Дай 2-3 конкретных варианта с поисковыми запросами."
    )
    return await _call(PARTS_SYSTEM, prompt)


async def ask_repair(question: str) -> str:
    return await _call(REPAIR_SYSTEM, question)


async def ask_help(question: str) -> str:
    return await _call(HELP_SYSTEM, question)
