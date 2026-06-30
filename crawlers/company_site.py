"""Фаза 2-3: имя компании + домен (страницы hh, fallback DuckDuckGo) + контакты с сайта."""
import json, time, random, urllib.parse
from playwright.sync_api import sync_playwright
from auth.hh_session import new_context, has_session
from extractors.emails import extract_emails
from extractors.telegram import extract_telegrams
from config import MIN_DELAY, MAX_DELAY, ENRICHED_JSON

SOCIAL_BLOCK = ("hh.ru", "linkedin.com", "facebook.com", "instagram.com",
                "vk.com", "youtube.com", "t.me", "wikipedia.org", "setka.ru",
                "rabota.ru", "superjob.ru", "habr.com", "google.", "feedback.hh",
                "dzen.ru", "zen.yandex", "yandex.ru", "ya.ru")
CONTACT_HINTS = ("contact", "kontakt", "about", "o-kompanii", "team", "komanda",
                 "career", "vacanc", "rabota", "contacts", "контакт", "команда")

def _sleep():
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

def _is_external(href):
    if not href or not href.startswith("http"):
        return False
    return not any(s in href for s in SOCIAL_BLOCK)

def company_and_site_from_vacancy(page, vacancy_url):
    company, employer_url = "", None
    try:
        page.goto(vacancy_url, wait_until="domcontentloaded", timeout=25000)
        _sleep()
        el = page.query_selector("[data-qa='vacancy-company-name'], a[href*='/employer/']")
        if el:
            company = (el.inner_text() or "").strip().replace("\n", " ")
            href = el.get_attribute("href")
            if not href:
                inner = el.query_selector("a[href*='/employer/']")
                href = inner.get_attribute("href") if inner else None
            if href:
                employer_url = urllib.parse.urljoin("https://hh.ru", href.split("?")[0])
    except Exception as e:
        print(f"  vacancy err: {e}")
    return company, employer_url

def site_from_employer(page, employer_url):
    try:
        page.goto(employer_url, wait_until="domcontentloaded", timeout=25000)
        _sleep()
        el = page.query_selector("[data-qa='sidebar-company-site'], [data-qa='employer-site']")
        if el:
            href = el.get_attribute("href") or (el.query_selector("a") and el.query_selector("a").get_attribute("href"))
            if _is_external(href):
                p = urllib.parse.urlparse(href)
                return f"{p.scheme}://{p.netloc}"
        for a in page.query_selector_all("a[href]"):
            href = a.get_attribute("href")
            if _is_external(href):
                p = urllib.parse.urlparse(href)
                return f"{p.scheme}://{p.netloc}"
    except Exception as e:
        print(f"  employer err: {e}")
    return None

def find_domain_ddg(page, company):
    if not company:
        return None
    q = urllib.parse.quote(company + " официальный сайт")
    try:
        page.goto(f"https://html.duckduckgo.com/html/?q={q}", wait_until="domcontentloaded", timeout=25000)
        _sleep()
        for a in page.query_selector_all("a.result__a, a.result__url"):
            href = a.get_attribute("href") or ""
            if "uddg=" in href:
                href = urllib.parse.unquote(href.split("uddg=")[-1].split("&")[0])
            if _is_external(href):
                p = urllib.parse.urlparse(href)
                return f"{p.scheme}://{p.netloc}"
    except Exception as e:
        print(f"  ddg err: {e}")
    return None

def scrape_site_contacts(page, base_url):
    from bs4 import BeautifulSoup
    emails, tgs = set(), set()

    def harvest(html):
        soup = BeautifulSoup(html, "html.parser")
        for t in soup(["script", "style", "noscript", "svg"]):
            t.decompose()
        text = soup.get_text(" ")
        # явные mailto/tg ссылки
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().startswith("mailto:"):
                text += " " + href[7:]
            if "t.me/" in href.lower():
                text += " " + href
        emails.update(extract_emails(text))
        tgs.update(extract_telegrams(text))

    try:
        page.goto(base_url, wait_until="domcontentloaded", timeout=25000)
        _sleep()
    except Exception:
        return emails, tgs
    harvest(page.content())

    links = set()
    base_net = urllib.parse.urlparse(base_url).netloc
    for a in page.query_selector_all("a[href]"):
        href = (a.get_attribute("href") or "").lower()
        if any(h in href for h in CONTACT_HINTS):
            full = urllib.parse.urljoin(base_url, a.get_attribute("href"))
            if urllib.parse.urlparse(full).netloc == base_net:
                links.add(full)
    for link in list(links)[:6]:
        try:
            page.goto(link, wait_until="domcontentloaded", timeout=20000)
            _sleep()
            harvest(page.content())
        except Exception:
            continue
    return emails, tgs

def enrich(responses, limit=None):
    out = []
    seen_domains = {}

    with sync_playwright() as p:
        if has_session():
            browser, ctx = new_context(p, headless=True)
        else:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context()

        def fresh_page():
            return ctx.new_page()

        page = fresh_page()
        items = responses[:limit] if limit else responses

        for i, r in enumerate(items, 1):
            company = r.get("company", "")
            employer_url = r.get("employer_url") or ""
            vacancy_url = r.get("vacancy_url") or ""
            if not employer_url and vacancy_url:
                try:
                    vac_company, vac_employer_url = company_and_site_from_vacancy(
                        page, vacancy_url
                    )
                    if vac_company and not company:
                        company = vac_company
                    if vac_employer_url:
                        employer_url = vac_employer_url
                except Exception as e:
                    print(f"  vacancy lookup err: {e}")
            domain = None
            emails, tgs = set(), set()
            try:
                if employer_url:
                    try:
                        domain = site_from_employer(page, employer_url)
                    except Exception:
                        try: page.close()
                        except Exception: pass
                        page = fresh_page()
                if not domain:
                    try:
                        domain = find_domain_ddg(page, company)
                    except Exception:
                        try: page.close()
                        except Exception: pass
                        page = fresh_page()
                        domain = find_domain_ddg(page, company)
                if domain:
                    if domain in seen_domains:
                        emails, tgs = seen_domains[domain]
                    else:
                        try:
                            emails, tgs = scrape_site_contacts(page, domain)
                        except Exception:
                            try: page.close()
                            except Exception: pass
                            page = fresh_page()
                            emails, tgs = set(), set()
                        seen_domains[domain] = (emails, tgs)
            except Exception as e:
                print(f"  record err: {e}")
                try: page.close()
                except Exception: pass
                page = fresh_page()

            print(f"[{i}/{len(items)}] {company!r} domain={domain} emails={len(emails)} tg={len(tgs)}")
            out.append({
                "company": company,
                "vacancy": r.get("vacancy", ""),
                "vacancy_url": r.get("vacancy_url", ""),
                "hh_contact": r.get("hh_contact", ""),
                "website": domain or "",
                "emails": sorted(emails),
                "telegrams": sorted(tgs),
                "source": "site",
            })

            # промежуточное сохранение каждые 25 записей
            if i % 25 == 0:
                with open(ENRICHED_JSON, "w", encoding="utf-8") as f:
                    json.dump(out, f, ensure_ascii=False, indent=2)
                print(f"  ...autosave {i}")

        browser.close()

    with open(ENRICHED_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Обогащено {len(out)} строк -> {ENRICHED_JSON}")
    return out
