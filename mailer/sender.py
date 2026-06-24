"""Фаза 6: рассылка одного шаблонного письма через Gmail SMTP.
Лимит ~400/день. Подставляет {company}/{vacancy}."""
import smtplib, time
from email.mime.text import MIMEText
from email.header import Header
from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD

TEMPLATE_SUBJECT = "{vacancy} — готов обсудить"
TEMPLATE_BODY = '''Здравствуйте!

Я откликнулся на вашу вакансию «{vacancy}» в компании {company} и заинтересован в позиции.

Коротко обо мне: [опыт/стек].
Резюме: [ссылка]

Буду рад короткому звонку или ответу здесь.

Спасибо!
[Имя] · [телефон / @telegram]
'''


def send_all(rows, daily_limit=400, dry_run=True):
    sent = 0
    server = None
    if not dry_run:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
    for r in rows:
        if sent >= daily_limit:
            break
        for to in r.get("emails", []):
            subj = TEMPLATE_SUBJECT.format(**r)
            body = TEMPLATE_BODY.format(company=r.get("company",""), vacancy=r.get("vacancy",""))
            if dry_run:
                print(f"[DRY] -> {to} | {subj}")
            else:
                msg = MIMEText(body, "plain", "utf-8")
                msg["Subject"] = Header(subj, "utf-8")
                msg["From"] = GMAIL_ADDRESS
                msg["To"] = to
                server.sendmail(GMAIL_ADDRESS, to, msg.as_string())
                time.sleep(2)
            sent += 1
            if sent >= daily_limit:
                break
    if server:
        server.quit()
    print(f"Отправлено (dry_run={dry_run}): {sent}")
