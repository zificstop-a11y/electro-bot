"""JSON-based storage layer."""
import json
import os
from datetime import date
from typing import Any

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "database.json")
REVIEWS_PATH = os.path.join(DATA_DIR, "reviews.json")
PEOPLE_PATH = os.path.join(DATA_DIR, "people.json")


def _load(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: str, data: Any) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── Catalogue ───────────────────────────────────────────────────────────────

def get_catalogue() -> dict:
    return _load(DB_PATH)


def get_categories() -> list[str]:
    return list(get_catalogue().keys())


def get_models(category: str) -> list[dict]:
    return get_catalogue().get(category, [])


def get_model_by_id(model_id: str) -> dict | None:
    for models in get_catalogue().values():
        for m in models:
            if m["id"] == model_id:
                return m
    return None


def update_price(model_id: str, new_price: int) -> bool:
    cat = get_catalogue()
    today = date.today().strftime("%Y-%m-%d")
    for models in cat.values():
        for m in models:
            if m["id"] == model_id:
                m["price"] = new_price
                m["updated"] = today
                _save(DB_PATH, cat)
                return True
    return False


def add_model(category: str, model: dict) -> None:
    cat = get_catalogue()
    if category not in cat:
        cat[category] = []
    cat[category].append(model)
    _save(DB_PATH, cat)


def delete_model(model_id: str) -> bool:
    cat = get_catalogue()
    for models in cat.values():
        for i, m in enumerate(models):
            if m["id"] == model_id:
                models.pop(i)
                _save(DB_PATH, cat)
                return True
    return False


def all_models_flat() -> list[dict]:
    result = []
    for cat, models in get_catalogue().items():
        for m in models:
            result.append({**m, "category": cat})
    return result


# ─── Reviews ─────────────────────────────────────────────────────────────────

def get_reviews() -> list[dict]:
    return _load(REVIEWS_PATH)


def add_review(review: dict) -> None:
    reviews = get_reviews()
    reviews.insert(0, review)
    _save(REVIEWS_PATH, reviews)


def get_latest_reviews(n: int = 5) -> list[dict]:
    return get_reviews()[:n]


# ─── People ──────────────────────────────────────────────────────────────────

def get_people() -> list[dict]:
    data = _load(PEOPLE_PATH)
    return sorted(data, key=lambda p: p.get("order", 999))


def add_person(person: dict) -> None:
    people = get_people()
    new_id = max((p["id"] for p in people), default=0) + 1
    person["id"] = new_id
    person["order"] = new_id
    people.append(person)
    _save(PEOPLE_PATH, people)


def delete_person(person_id: int) -> bool:
    people = _load(PEOPLE_PATH)
    original = len(people)
    people = [p for p in people if p["id"] != person_id]
    if len(people) < original:
        _save(PEOPLE_PATH, people)
        return True
    return False
