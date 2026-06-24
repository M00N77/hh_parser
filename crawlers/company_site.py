"""Фаза 2-3: домен компании (DuckDuckGo) + контакты с сайта."""
import time
import random
import urllib.parse
from playwright.sync_api import sync_playwright
from extractors.emails import extract_emails
from extractors.telegram import extract_telegrams
from config import MIN_DELAY, MAX_DELAY

SOCIAL_BLOCK = ("hh.ru", "linkedin.com", "facebook.com", "instagram.com",
                "vk.com", "youtube.com", "t.me", "wikipedia.org",
                "rabota.ru", "superjob.ru", "habr.com", "google.")

CONTACT_HINTS = ("contact", "kontakt", "about", "o-kompanii", "team", "komanda",
                 "career", "vacanc", "rabota", "contacts", "контакт", "команда")


def _sleep():
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


def find_domain(page, company: str):
    q = urllib.parse.quote(company + " официальный сайт")
    page.goto(f"https://html.duckduckgo.com/html/?q={q}", wait_until="domcontentloaded")
    _sleep()
    for a in page.query_selector_all("a.result__a, a.result__url"):
        href = a.get_attribute("href") or ""
        # ddg оборачивает ссылки в редирект
        if "uddg=" in href:
            href = urllib.parse.unquote(href.split("uddg=")[-1].split("&")[0])
        if href.startswith("http") and not any(s in href for s in SOCIAL_BLOCK):
            parsed = urllib.parse.urlparse(href)
            return f"{parsed.scheme}://{parsed.netloc}"
    return None


def scrape_site_contacts(page, base_url: str):
    emails, tgs = set(), set()
    try:
        page.goto(base_url, wait_until="domcontentloaded", timeout=20000)
        _sleep()
    except Exception:
        return emails, tgs

    html = page.content()
    emails |= extract_emails(html)
    tgs |= extract_telegrams(html)

    # собрать ссылки на контактные страницы
    links = set()
    for a in page.query_selector_all("a[href]"):
        href = (a.get_attribute("href") or "").lower()
        if any(h in href for h in CONTACT_HINTS):
            full = urllib.parse.urljoin(base_url, a.get_attribute("href"))
            if urllib.parse.urlparse(full).netloc == urllib.parse.urlparse(base_url).netloc:
                links.add(full)

    for link in list(links)[:6]:
        try:
            page.goto(link, wait_until="domcontentloaded", timeout=20000)
            _sleep()
            html = page.content()
            emails |= extract_emails(html)
            tgs |= extract_telegrams(html)
        except Exception:
            continue
    return emails, tgs


def enrich(responses):
    import json
    from config import ENRICHED_JSON
    out = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # уникальные компании
        companies = {}
        for r in responses:
            companies.setdefault(r["company"], []).append(r)

        for company, items in companies.items():
            if not company:
                continue
            try:
                domain = find_domain(page, company)
                emails, tgs = (set(), set())
                if domain:
                    emails, tgs = scrape_site_contacts(page, domain)
                print(f"[{company}] domain={domain} emails={len(emails)} tg={len(tgs)}")
                for r in items:
                    out.append({**r,
                                "website": domain or "",
                                "emails": sorted(emails),
                                "telegrams": sorted(tgs),
                                "source": "site"})
            except Exception as e:
                print(f"[{company}] ошибка: {e}")
                for r in items:
                    out.append({**r, "website": "", "emails": [], "telegrams": [], "source": "site"})
        browser.close()

    with open(ENRICHED_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Обогащено {len(out)} строк -> {ENRICHED_JSON}")
    return out
