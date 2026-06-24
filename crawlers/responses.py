"""Фаза 1: сбор откликов из ЛК hh.ru (раздел 'Мои отклики')."""
import json
import time
import random
from playwright.sync_api import sync_playwright
from auth.hh_session import new_context, has_session
from config import HH_RESPONSES_URL, RESPONSES_JSON, MIN_DELAY, MAX_DELAY, MAX_PAGES


def _sleep():
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


def _is_login_redirect(page) -> bool:
    return "account/login" in page.url or "/auth/" in page.url


def scrape_responses():
    if not has_session():
        raise RuntimeError("Нет сессии. Сначала: python main.py --phase auth")

    results = []
    seen = set()
    with sync_playwright() as p:
        browser, ctx = new_context(p, headless=False)
        page = ctx.new_page()
        page_num = 0
        url = HH_RESPONSES_URL
        while page_num < MAX_PAGES:
            target = url + ("&" if "?" in url else "?") + f"page={page_num}"
            page.goto(target, wait_until="domcontentloaded")
            _sleep()
            if _is_login_redirect(page):
                raise RuntimeError("Сессия протухла. Перезапусти: python main.py --phase auth")

            # карточки откликов: hh использует data-qa маркеры
            cards = page.query_selector_all("[data-qa='negotiations-item'], div.negotiations-item, [data-qa*='topic']")
            if not cards:
                # fallback: ссылки на вакансии
                cards = page.query_selector_all("a[data-qa='serp-item__title'], a[href*='/vacancy/']")
            if not cards:
                print(f"[page {page_num}] карточек не найдено — стоп.")
                break

            page_added = 0
            for c in cards:
                try:
                    link = c.query_selector("a[href*='/vacancy/']") or (c if c.get_attribute("href") else None)
                    vac_url = link.get_attribute("href") if link else None
                    vacancy = (link.inner_text().strip() if link else "") or ""
                    comp_el = c.query_selector("[data-qa='vacancy-serp__vacancy-employer'], a[href*='/employer/'], .negotiations-item__company")
                    company = comp_el.inner_text().strip() if comp_el else ""
                    contact_el = c.query_selector("[data-qa*='contact'], .negotiations-item__contact")
                    hh_contact = contact_el.inner_text().strip() if contact_el else ""
                    if vac_url and vac_url.startswith("/"):
                        vac_url = "https://hh.ru" + vac_url
                    key = vac_url or (company + vacancy)
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    results.append({
                        "company": company,
                        "vacancy": vacancy,
                        "vacancy_url": vac_url,
                        "hh_contact": hh_contact,
                    })
                    page_added += 1
                except Exception as e:
                    continue

            print(f"[page {page_num}] +{page_added} (всего {len(results)})")
            if page_added == 0:
                break
            page_num += 1

        browser.close()

    with open(RESPONSES_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Сохранено {len(results)} откликов -> {RESPONSES_JSON}")
    return results
