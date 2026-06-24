import re
import dns.resolver
from config import EMAIL_BLACKLIST_DOMAINS, EMAIL_BLACKLIST_PREFIX, VALIDATE_MX

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

_mx_cache = {}

def _has_mx(domain: str) -> bool:
    domain = domain.lower()
    if domain in _mx_cache:
        return _mx_cache[domain]
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        ok = len(answers) > 0
    except dns.resolver.NXDOMAIN:
        ok = False
    except dns.resolver.NoAnswer:
        ok = False
    except Exception:
        ok = True
    _mx_cache[domain] = ok
    return ok

def extract_emails(text: str, validate_mx: bool | None = None) -> set:
    do_mx = VALIDATE_MX if validate_mx is None else validate_mx
    found = set()
    for m in EMAIL_RE.findall(text or ""):
        e = m.lower().strip(".")
        domain = e.split("@")[-1]
        prefix = e.split("@")[0]
        if domain in EMAIL_BLACKLIST_DOMAINS:
            continue
        if any(prefix.startswith(p) for p in EMAIL_BLACKLIST_PREFIX):
            continue
        # отсеять явный мусор от хешей картинок/файлов
        if any(e.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
            continue
        if do_mx and not _has_mx(domain):
            continue
        found.add(e)
    return found
