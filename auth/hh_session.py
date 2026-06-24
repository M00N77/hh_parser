"""Сохранение/переиспользование сессии hh.ru через Playwright storage_state."""
import os
from playwright.sync_api import sync_playwright
from config import STORAGE_STATE, DATA_DIR


def login_and_save():
    """Открыть браузер, дать пользователю залогиниться вручную, сохранить state."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto("https://hh.ru/account/login")
        print("\n>>> Залогинься в hh.ru в открытом окне.")
        input(">>> Когда увидишь свой личный кабинет — нажми ENTER здесь...")
        ctx.storage_state(path=STORAGE_STATE)
        print(f">>> Сессия сохранена: {STORAGE_STATE}")
        browser.close()


def has_session() -> bool:
    return os.path.exists(STORAGE_STATE)


def new_context(p, headless=True):
    """Создать контекст браузера с сохранённой сессией."""
    browser = p.chromium.launch(headless=headless)
    if has_session():
        ctx = browser.new_context(storage_state=STORAGE_STATE)
    else:
        ctx = browser.new_context()
    return browser, ctx
