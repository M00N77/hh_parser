# hh_parser

Парсер откликов с hh.ru: сбор контактов компаний, запись в Google Sheets и email-рассылка.

## Установка

```bash
pip install -r requirements.txt
playwright install chromium
```

## Настройка

1. Скопируй `.env.example` в `.env` и заполни секреты
2. Положи Google Service Account JSON в `creds/google_service_account.json`
3. Создай Google Sheet и укажи её ID в `.env`

## Запуск

```bash
python main.py
```

## Структура

```
hh_parser/
├── main.py                 # оркестрация
├── config.py               # конфиг (pydantic-settings)
├── auth/hh_session.py      # логин + cookies
├── crawlers/               # парсинг hh.ru и сайтов
├── extractors/             # email + telegram
├── storage/sheets.py       # Google Sheets
├── mailer/sender.py        # SMTP
└── data/                   # storage_state.json и др.
```
