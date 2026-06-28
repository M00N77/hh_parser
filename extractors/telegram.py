import re

TME_RE = re.compile(r"(?:https?://)?(?:t|telegram)\.me/([a-zA-Z0-9_]{4,32})", re.I)
NICK_RE = re.compile(r"(?<![\w/@])@([a-zA-Z][a-zA-Z0-9_]{4,31})\b")

# CSS at-rules, html-атрибуты и прочий технический мусор — не телеграм-ники
STOP = {
    "gmail", "mail", "yandex", "outlook", "icloud", "example", "media", "support",
    "keyframes", "context", "supports", "container", "forms", "graph", "import",
    "charset", "namespace", "font", "page", "media", "screen", "print", "layer",
    "property", "scope", "starting", "viewport", "abcdefghijklmnopqrstuvwxyz",
    "false", "true", "null", "function", "return", "string", "object",
}

def extract_telegrams(text: str) -> set:
    found = set()
    for name in TME_RE.findall(text or ""):
        if name.lower() in ("joinchat", "share", "addstickers"):
            continue
        found.add("@" + name.lower())
    for name in NICK_RE.findall(text or ""):
        low = name.lower()
        if low in STOP:
            continue
        # отсеять «алфавитные» последовательности типа abcdef
        if low in "abcdefghijklmnopqrstuvwxyz":
            continue
        found.add("@" + low)
    return found
