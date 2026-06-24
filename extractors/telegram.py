import re

# t.me/<name> или telegram.me/<name>
TME_RE = re.compile(r"(?:https?://)?(?:t|telegram)\.me/([a-zA-Z0-9_]{4,32})", re.I)
# @nickname (5-32 символа, по правилам тг минимум 5 после @)
NICK_RE = re.compile(r"(?<![\w/@])@([a-zA-Z][a-zA-Z0-9_]{4,31})\b")

# слова-ловушки, которые не являются тг-никами
STOP = {"gmail", "mail", "yandex", "outlook", "icloud", "example", "media", "support"}

def extract_telegrams(text: str) -> set:
    found = set()
    for name in TME_RE.findall(text or ""):
        if name.lower() in ("joinchat", "share", "addstickers"):
            continue
        found.add("@" + name.lower())
    for name in NICK_RE.findall(text or ""):
        if name.lower() in STOP:
            continue
        found.add("@" + name.lower())
    return found
