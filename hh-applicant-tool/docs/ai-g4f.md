# Бесплатный keyless-LLM провайдер через g4f

Библиотека [g4f](https://github.com/xtekky/gpt4free) предоставляет бесплатный
доступ к различным LLM через публичные API (народные провайдеры).

## Способ 1. Встроенный провайдер (рекомендуемый)

В настройках (секция `openai_cover_letter`, `openai_vacancy_filter` или
`openai_captcha`) укажите:

```yaml
# config.yml
openai_cover_letter:
  provider: g4f
  model: gpt-4o-mini     # или deepseek-v3, gemini-2.5-flash
```

Либо в UI настройках:
- **Эндпоинт**: `g4f`
- **Ключ**: оставить пустым
- **Модель**: `gpt-4o-mini` / `deepseek-v3` / `gemini-2.5-flash`

### Установка

```bash
pip install -U g4f
```

## Способ 2. Локальный OpenAI-совместимый сервер

Запустите локальный прокси-сервер, который будет маршрутизировать запросы
через g4f:

```bash
pip install -U "g4f[all]"
python -m g4f.cli api --port 1337
```

В настройках укажите эндпоинт и модель как для обычного OpenAI:

```yaml
openai_cover_letter:
  base_url: http://localhost:1337/v1/chat/completions
  model: gpt-4o-mini
```

## Предупреждение

g4f использует неофициальные/народные провайдеры, поэтому:
- Стабильность не гарантируется — провайдеры могут падать или закрываться
- Не предназначен для production-нагрузки
- Возможны задержки и лимиты
- При ошибках попробуйте сменить модель (например, `deepseek-v3` или `gemini-2.5-flash`)
