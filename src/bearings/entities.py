"""Entity extraction from task text. Plain code, no model calls.

An entity is a typed, normalised key:

* ``path:django/db/models/query.py`` - a file path mentioned in the text
  (tracebacks, prose)
* ``mod:django.db.models.query``   - a dotted module path
* ``err:fielderror``               - an exception / warning class name
* ``sym:queryset``                 - an identifier: CamelCase, snake_case,
  ``dotted.attr`` parts, ``call()`` names
* ``word:migrat``                  - a distinctive plain word (light stemming)

Keys are lowercase and deterministic, so the node id for an entity is a hash
of its key and needs no text search in the database.
"""

from __future__ import annotations

import hashlib
import re

STOP = set(
    """a about above after again against all also am an and any are aren as at be
    because been before being below between both but by can cannot could did do does
    doing don down during each few for from further had has have having he her here
    hers him his how i if in into is isn it its itself just me more most my no nor not
    now of off on once only or other our ours out over own same she should so some such
    than that the their theirs them then there these they this those through to too
    under until up very was we were what when where which while who whom why will with
    would you your yours yourself however instead using used use uses currently
    still since though thus therefore would like seems seem example following
    something anything nothing everything someone thing things way ways case cases
    work works working worked make makes made making get gets got getting see seen
    want wants need needs needed know think thought issue issues problem problems
    bug bugs ticket fix fixed fixes fixing report reported thanks thank patch
    django python code line lines file files test tests tested testing true false
    none null self return returns returned value values new old possible currently
    expected actual behavior behaviour result results error errors raise raises raised
    added adding add removed remove removing changed change changes changing
    support supported allow allows allowed doesn didn isn wasn won shouldn couldn
    one two three first second last time times may might must shall well even
    much many already always never sometimes often would rather quite
    http https www com org html github master main commit pull request""".split()
)

PATH_RE = re.compile(r"(?<![\w./-])((?:[\w-]+/)+[\w-]+\.(?:py|js|html|txt|css|json|cfg|toml))")
MOD_RE = re.compile(r"\b([a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*){2,})\b")
ERR_RE = re.compile(r"\b([A-Z][A-Za-z0-9]*(?:Error|Exception|Warning))\b")
CAMEL_RE = re.compile(r"\b([A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+|[a-z]+(?:[A-Z][a-z0-9]*)+)\b")
SNAKE_RE = re.compile(r"\b(_{0,2}[a-z][a-z0-9]*(?:_[a-z0-9]+)+_{0,2})\b")
DOTTED_RE = re.compile(r"\b([A-Za-z_][\w]*(?:\.[A-Za-z_]\w*)+)\b")
CALL_RE = re.compile(r"\b([A-Za-z_]\w{2,})\(")
WORD_RE = re.compile(r"[a-z]{4,}")

TRAILER_RE = re.compile(
    r"^(?:git-svn-id|co-authored-by|signed-off-by|reviewed-by|backport of|refs?|thanks|review).*$",
    re.I | re.M,
)
THANKS_RE = re.compile(r"\bthanks?\b[^.\n]*[.\n]?", re.I)
TICKET_RE = re.compile(r"\b(?:fixe[sd]|refs?|close[sd])\s+#\d+\s*(?:--)?", re.I)
URL_RE = re.compile(r"https?://\S+")


def _stem(w: str) -> str:
    for suf in ("ations", "ation", "ings", "ing", "ies", "ers", "ed", "es", "er", "s"):
        if suf == "s" and (w.endswith("ss") or w.endswith("us") or w.endswith("is")):
            continue
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


def clean(text: str) -> str:
    """Remove commit trailers, credits, ticket refs and URLs."""
    text = URL_RE.sub(" ", text)
    text = TRAILER_RE.sub(" ", text)
    text = THANKS_RE.sub(" ", text)
    text = TICKET_RE.sub(" ", text)
    return text


def extract(text: str) -> dict[str, int]:
    """Return ``{entity_key: count}`` for a task text."""
    text = clean(text)
    out: dict[str, int] = {}

    def add(key: str) -> None:
        out[key] = out.get(key, 0) + 1

    for p in PATH_RE.findall(text):
        # tracebacks give absolute paths; keep from the first package dir on
        parts = p.lstrip("./").lower().split("/")
        # an absolute traceback path names the repo file by one of its suffixes;
        # only the suffix that is a real file links structurally
        for i in range(max(0, len(parts) - 6), len(parts) - 1):
            add("path:" + "/".join(parts[i:]))
    for m in MOD_RE.findall(text):
        if not re.search(r"\.(py|js|html|txt|com|org)$", m):
            add("mod:" + m)
    for e in ERR_RE.findall(text):
        add("err:" + e.lower())
    syms: list[str] = []
    syms += CAMEL_RE.findall(text)
    syms += SNAKE_RE.findall(text)
    syms += CALL_RE.findall(text)
    for d in DOTTED_RE.findall(text):
        syms += [part for part in d.split(".") if len(part) > 2]
    for s in syms:
        s = s.strip("_").lower()
        if len(s) > 2 and s not in STOP:
            add("sym:" + s)
    for w in WORD_RE.findall(text.lower()):
        if w not in STOP:
            add("word:" + _stem(w))
    return out


def node_id(kind: str, key: str) -> int:
    """Deterministic 62-bit non-negative node id for ``kind:key``."""
    h = hashlib.blake2b(f"{kind}\x00{key}".encode(), digest_size=8).digest()
    return int.from_bytes(h, "big") >> 2


def path_candidates(entity: str) -> list[str]:
    """Files an entity names directly (``path:`` and ``mod:`` entities)."""
    kind, _, key = entity.partition(":")
    if kind == "path":
        return [key]
    if kind == "mod":
        base = key.replace(".", "/")
        return [base + ".py", base + "/__init__.py"]
    return []
