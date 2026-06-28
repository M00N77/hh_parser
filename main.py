"""Оркестратор пайплайна HH Outreach Parser."""
import argparse, json, logging, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from config import RESPONSES_JSON, ENRICHED_JSON

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _load(path):
    if not os.path.exists(path):
        raise SystemExit(f"Нет файла {path}. Запусти предыдущую фазу.")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True,
                    choices=["auth","apply","fetch","responses","contacts","setka","sheets","send","all","pipeline"])
    ap.add_argument("--send-real", action="store_true", help="реальная отправка писем")
    ap.add_argument("--search", default="")
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--apply-real", action="store_true")
    ap.add_argument("--ai", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    if args.phase == "auth":
        from auth.hh_session import login_and_save
        login_and_save()

    elif args.phase == "responses":
        from crawlers.responses import scrape_responses
        scrape_responses()

    elif args.phase == "contacts":
        from crawlers.company_site import enrich
        enrich(_load(RESPONSES_JSON), limit=args.limit or None)

    elif args.phase == "setka":
        from crawlers.setka import search_company
        data = _load(ENRICHED_JSON)
        for r in data:
            if not r.get("emails") and not r.get("telegrams") and r.get("company"):
                e, t = search_company(r["company"])
                r["emails"] = sorted(set(r.get("emails", [])) | e)
                r["telegrams"] = sorted(set(r.get("telegrams", [])) | t)
                if e or t:
                    r["source"] = (r.get("source","") + "+setka").strip("+")
        with open(ENRICHED_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Сетка обработана.")

    elif args.phase == "sheets":
        from storage.sheets import write_rows
        write_rows(_load(ENRICHED_JSON))

    elif args.phase == "send":
        from mailer.sender import send_all
        send_all(_load(ENRICHED_JSON), dry_run=not args.send_real)

    elif args.phase == "apply":
        from crawlers.hh_tool import apply_vacancies
        if not args.search:
            raise SystemExit("Укажи --search 'запрос'")
        apply_vacancies(args.search, total_pages=args.pages, ai=args.ai, dry_run=not args.apply_real)

    elif args.phase == "fetch":
        from crawlers.hh_tool import fetch_negotiations
        fetch_negotiations()

    elif args.phase == "pipeline":
        from crawlers.hh_tool import apply_vacancies, fetch_negotiations
        from crawlers.company_site import enrich
        from storage.sheets import write_rows
        if args.search:
            apply_vacancies(args.search, total_pages=args.pages, ai=args.ai, dry_run=not args.apply_real)
        resp = fetch_negotiations()
        enriched = enrich(resp, limit=args.limit or None)
        try:
            write_rows(enriched)
        except Exception as e:
            print("Sheets skipped:", e)

    elif args.phase == "all":
        from crawlers.responses import scrape_responses
        from crawlers.company_site import enrich
        from storage.sheets import write_rows
        resp = scrape_responses()
        enriched = enrich(resp, limit=args.limit or None)
        write_rows(enriched)


if __name__ == "__main__":
    main()
