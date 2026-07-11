"""Реальный парсер цен с Wildberries и Ozon."""
import asyncio
import urllib.parse
from datetime import date
from typing import Optional

import httpx

import db

WB_SEARCH = "https://search.wb.ru/exactmatch/ru/common/v5/search"
WB_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

OZON_SEARCH = "https://www.ozon.ru/api/composer-api.bx/page/json/v2"
OZON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "x-o3-app-name": "ozon-front",
}


async def _wb_price(query: str, client: httpx.AsyncClient) -> Optional[int]:
    """Ищет минимальную цену на Wildberries."""
    try:
        params = {
            "query": query,
            "resultset": "catalog",
            "limit": "10",
            "sort": "popular",
            "dest": "-1257786",
            "suppressSpellcheck": "false",
        }
        r = await client.get(WB_SEARCH, params=params, headers=WB_HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        products = data.get("data", {}).get("products", [])
        if not products:
            return None
        prices = []
        for p in products[:5]:
            # priceU — цена в копейках, salePriceU — цена со скидкой в копейках
            sale = p.get("salePriceU") or p.get("priceU")
            if sale:
                prices.append(sale // 100)
        return min(prices) if prices else None
    except Exception:
        return None


async def _ozon_price(query: str, client: httpx.AsyncClient) -> Optional[int]:
    """Ищет минимальную цену на Ozon через их API."""
    try:
        params = {"url": f"/search/?text={urllib.parse.quote(query)}&from_global=true"}
        r = await client.get(
            OZON_SEARCH,
            params=params,
            headers=OZON_HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        # Ищем цены в виджетах
        prices = []
        widgets = data.get("widgetStates", {})
        for key, val in widgets.items():
            if "searchResultsV2" in key or "tileGrid" in key:
                import json as _json
                try:
                    items = _json.loads(val) if isinstance(val, str) else val
                    for item in items.get("items", []):
                        price_str = (
                            item.get("price", {}).get("price", "")
                            or item.get("mainState", [{}])[0].get("atom", {}).get("price", {}).get("price", "")
                        )
                        digits = "".join(c for c in str(price_str) if c.isdigit())
                        if digits:
                            prices.append(int(digits))
                except Exception:
                    pass
        return min(prices) if prices else None
    except Exception:
        return None


async def check_and_update_all() -> list[dict]:
    """
    Проходит по всем моделям, ищет актуальные цены на WB и Ozon,
    берёт минимальную и обновляет базу.
    Возвращает список результатов.
    """
    models = db.all_models_flat()
    results = []
    today = date.today().strftime("%Y-%m-%d")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = []
        for m in models:
            tasks.append(_fetch_best_price(m, client, today))
        results = await asyncio.gather(*tasks)

    return results


async def _fetch_best_price(m: dict, client: httpx.AsyncClient, today: str) -> dict:
    query = m["search_query"]
    old_price = m["price"]

    wb_price, ozon_price = await asyncio.gather(
        _wb_price(query, client),
        _ozon_price(query, client),
    )

    candidates = [p for p in [wb_price, ozon_price] if p and p > 1000]
    new_price = min(candidates) if candidates else None

    status = "❓ не найдено"
    if new_price:
        if new_price < old_price:
            status = f"📉 снизилась"
        elif new_price > old_price:
            status = f"📈 выросла"
        else:
            status = f"✅ не изменилась"
        db.update_price(m["id"], new_price)

    return {
        "name": m["name"],
        "category": m["category"],
        "old_price": old_price,
        "new_price": new_price,
        "wb_price": wb_price,
        "ozon_price": ozon_price,
        "status": status,
    }
