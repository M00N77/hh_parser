"""Фаза 4: поиск контактов сотрудников в Сетке (setka.hh.ru) под своей сессией.
Сетка часто меняет разметку — модуль best-effort: открывает поиск по компании,
собирает текст профилей и вытягивает email/telegram теми же экстракторами."""
import time, random, urllib.parse
from playwright.sync_api import sync_playwright
from auth.hh_session import new_context, has_session
from extractors.emails import extract_emails
from extractors.telegram import extract_telegrams
from config import MIN_DELAY, MAX_DELAY

SETKA_SEARCH = "https://setka.hh.ru/search?query="


def _sleep():
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


def search_company(company: str):
    if not has_session():
        raise RuntimeError("Нет сессии hh. Сначала: python main.py --phase auth")
    emails, tgs = set(), set()
    with sync_playwright() as p:
        browser, ctx = new_context(p, headless=True)
        page = ctx.new_page()
        try:
            page.goto(SETKA_SEARCH + urllib.parse.quote(company), wait_until="domcontentloaded", timeout=20000)
            _sleep()
            html = page.content()
            emails |= extract_emails(html)
            tgs |= extract_telegrams(html)
        except Exception as e:
            print(f"[setka:{company}] {e}")
        browser.close()
    return emails, tgs
