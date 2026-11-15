"""The "vague report" variant of an issue: what a user who does not know the code
would write. Fixed before any vague run, applied identically to every issue:

- drop fenced code blocks, indented code lines and tracebacks;
- drop inline `code` spans, file paths, dotted names and URLs;
- drop identifiers that look like code (snake_case, CamelCase, called with "(").

What is left is the prose: the symptom and the context in plain words.
"""

from __future__ import annotations

import re

from .anchors import names

FENCE = re.compile(r"```.*?```|~~~.*?~~~", re.S)
TICK = re.compile(r"`[^`\n]*`")
URL = re.compile(r"https?://\S+")
PATH = re.compile(r"\b[\w.-]*[/\\][\w./\\-]+")
DOTTED = re.compile(r"\b\w+(?:\.\w+)+\b")
TRACE = re.compile(r"^(Traceback|\s*File \"|\s*raise |\w+(Error|Exception|Warning):).*$", re.M)


def vague(text: str) -> str:
    t = FENCE.sub(" ", text)
    t = "\n".join(line for line in t.splitlines() if not re.match(r"^(\t| {4,}|>>>|\.\.\.|\$ )", line))
    t = TRACE.sub(" ", t)
    t = TICK.sub(" ", t)
    t = URL.sub(" ", t)
    t = PATH.sub(" ", t)
    t = DOTTED.sub(" ", t)
    for n in sorted(names(t, limit=1000), key=len, reverse=True):
        t = re.sub(rf"(?<![\w]){re.escape(n)}(?![\w])", " ", t)
    # lines that were code and are now mostly punctuation, plus leftover code statements
    keep = []
    for line in t.splitlines():
        words = re.findall(r"[A-Za-z]{3,}", line)
        if re.match(r"^\s*(from|import|class|def|return|opts|if|for)\b", line) or len(words) < 3 and len(line.strip()) > 0 and not line.strip().endswith((".", ":")):
            continue
        keep.append(line)
    t = "\n".join(keep)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    return t.strip()
