## Handoff: Add `escapeseq` template filter

**Issue:** Add a new `escapeseq` template filter — the escaping counterpart to `safeseq`. It should apply `escape` to each element of a sequence so that, e.g., `{{ some_list|escapeseq|join:"," }}` escapes every item before `join`, which matters when autoescape is off.

**Key code:** `django/template/defaultfilters.py`
- Import of `escape`/`conditional_escape` at line 17.
- `escape_filter` lines 440–445 and `force_escape` lines 447–456 are string-only, not sequence-aware.
- `safe` at 486–489 and `safeseq` at 491–498 are the model to mirror; the new filter belongs immediately after `safeseq` (~line 499), registered `@register.filter(is_safe=True)`, yielding `escape(item)` for each element.

**Docs:**
- `docs/ref/templates/builtins.txt`: `safeseq` entry at 2361–2375; `force_escape` at 1968–1985; `escape` around 1824. Add an `escapeseq` entry next to `safeseq`.
- `docs/releases/5.0.txt`: `Templates` section around line 345 currently has a `* ...` placeholder; add a bullet.

**Tests:** `tests/template_tests/filter_tests/test_safeseq.py` (lines 7–14) is the pattern; create `tests/template_tests/filter_tests/test_escapeseq.py` rendering a list like `["&", "<"]` and asserting escaped joined output.

**Ruled out:** Repo-wide `grep` for `escapeseq` returned nothing — no prior implementation exists. `escape`/`force_escape` cannot be reused directly on sequences (they stringify the whole value), and `safeseq` only marks elements safe without escaping.

**Conclusion:** Implement `escapeseq` beside `safeseq` in `defaultfilters.py`, document it in `builtins.txt` and the 5.0 release notes, and add the dedicated test module.
