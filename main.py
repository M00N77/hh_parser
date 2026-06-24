"""Оркестратор пайплайна HH Outreach Parser."""
import argparse, json, logging, os
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
                    choices=["auth", "responses", "contacts", "setka", "sheets", "send", "all"])
    ap.add_argument("--send-real", action="store_true", help="реальная отправка писем")
    args = ap.parse_args()

    if args.phase == "auth":
        from auth.hh_session import login_and_save
        login_and_save()

    elif args.phase == "responses":
        from crawlers.responses import scrape_responses
        scrape_responses()

    elif args.phase == "contacts":
        from crawlers.company_site import enrich
        enrich(_load(RESPONSES_JSON))

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

    elif args.phase == "all":
        from crawlers.responses import scrape_responses
        from crawlers.company_site import enrich
        from storage.sheets import write_rows
        resp = scrape_responses()
        enriched = enrich(resp)
        write_rows(enriched)


if __name__ == "__main__":
    main()
