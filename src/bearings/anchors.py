"""Code anchors: where in the current checkout the identifiers a task names are
defined. Plain `git grep`, no model calls, no index to keep up to date.

The learned graph says which files past work on similar tasks changed; anchors
say which files define what this task talks about, and at which line. The
context pack uses both, and the line numbers let an agent read 40 lines instead
of searching.
"""

from __future__ import annotations

import re
import subprocess
from collections import defaultdict
from pathlib import Path

from .core import is_source

IDENT = re.compile(r"(?<![\w/.-])([A-Za-z_][A-Za-z0-9_]{2,})(?=\s*\(|\b)")
STOP = {"self", "cls", "None", "True", "False", "print", "return", "import", "from", "class", "def", "lambda",
        "Django", "django", "Python", "python", "TestCase", "Exception", "object", "kwargs", "args", "str", "int",
        "dict", "list", "len", "isinstance", "super", "setUp", "test", "tests", "models", "Model", "objects",
        "Ticket", "Traceback", "File", "line"}


WORD = re.compile(r"(?<![\w/.-])([a-z][a-z0-9]{5,})\b")


def plain_words(text: str, limit: int = 60) -> list[str]:
    """Lower-case words that might be identifiers (``floatformat``); only trusted
    when very few files define them."""
    seen: dict[str, int] = {}
    for m in WORD.finditer(text):
        seen[m.group(1)] = seen.get(m.group(1), 0) + 1
    return sorted(seen, key=lambda w: (-seen[w], w))[:limit]


def names(text: str, limit: int = 40) -> list[str]:
    """Identifiers that look like code: snake_case, CamelCase, called, or in backticks."""
    out: dict[str, int] = {}
    tick = set(re.findall(r"`([A-Za-z_][\w.]*)`", text))
    tick = {t.split(".")[-1] for t in tick}
    for m in IDENT.finditer(text):
        w = m.group(1)
        if w in STOP or w.isupper() and len(w) < 4:
            continue
        after = text[m.end():m.end() + 1]
        codey = ("_" in w.strip("_") or re.search(r"[a-z][A-Z]", w) or (w[0].isupper() and any(c.isupper() for c in w[1:]))
                 or after == "(" or w in tick or text[max(0, m.start() - 1)] == ".")
        if codey:
            out[w] = out.get(w, 0) + 1
    return sorted(out, key=lambda w: (-out[w], w))[:limit]


def grep_defs(repo: Path, ns: list[str], commit: str | None = None) -> dict[str, list[tuple[str, int]]]:
    """name -> [(path, line)] of `def name` / `class name` in source files."""
    if not ns:
        return {}
    pat = r"^\s*(async\s+)?(def|class)\s+(" + "|".join(re.escape(n) for n in ns) + r")\b"
    cmd = ["git", "-C", str(repo), "grep", "-n", "-E", pat]
    if commit:
        cmd.append(commit)
    cmd += ["--", "*.py"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    res: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for line in out.splitlines():
        parts = line.split(":", 3 if commit else 2)
        if commit:
            parts = parts[1:]
        if len(parts) < 3:
            continue
        path, ln, src = parts
        m = re.search(r"(?:def|class)\s+(\w+)", src)
        if m and is_source(path):
            res[m.group(1)].append((path, int(ln)))
    return res


PLAIN_MAX_FILES = 2
PLAIN = False  # tried on dev: hurt (hit@5 .778 -> .683), off


def definitions(repo: Path, commit: str | None, text: str, detail: bool = False):
    """file -> anchor score (sum over named identifiers of 1/#files defining it).
    With detail=True also returns file -> [(line, name)]."""
    codey = names(text)
    plain = [w for w in plain_words(text) if w not in codey] if PLAIN else []
    defs = grep_defs(repo, codey + plain, commit)
    score: dict[str, float] = defaultdict(float)
    where: dict[str, list[tuple[int, str]]] = defaultdict(list)
    plain_set = set(plain)
    for n, locs in defs.items():
        files = {p for p, _ in locs}
        if len(files) > 8:  # too generic (e.g. `save`, `__init__`)
            continue
        if n in plain_set and len(files) > PLAIN_MAX_FILES:
            continue
        for p, ln in locs:
            where[p].append((ln, n))
        for p in files:
            score[p] += 1.0 / len(files)
    return (dict(score), dict(where)) if detail else dict(score)


def checkout_root(path: str | Path | None) -> Path | None:
    """The git work tree containing ``path``, or None."""
    if not path:
        return None
    r = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None


def changed_files(repo: Path) -> list[str]:
    """Files modified or added in the work tree (vs HEAD), for automatic reporting."""
    out = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"],
                         capture_output=True, text=True).stdout
    files = []
    for line in out.splitlines():
        path = line[3:].split(" -> ")[-1].strip().strip('"')
        if path:
            files.append(path)
    return files
