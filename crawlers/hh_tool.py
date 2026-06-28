"""Заглушка: вызовы hh-applicant-tool через API."""
import json, os, sys
from config import RESPONSES_JSON


def apply_vacancies(search, total_pages=1, ai=False, dry_run=True):
    if dry_run:
        print(f"[dry-run] apply search={search!r} pages={total_pages} ai={ai}")
        return []


def fetch_negotiations():
    if not os.path.exists(RESPONSES_JSON):
        print(f"Нет {RESPONSES_JSON}, возвращаю пустой список")
        return []
    with open(RESPONSES_JSON, encoding="utf-8") as f:
        data = json.load(f)
    print(f"Загружено {len(data)} откликов из {RESPONSES_JSON}")
    return data
