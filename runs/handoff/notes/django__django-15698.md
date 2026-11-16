## Handoff: template crash on built-in method lookup

**Issue:** `{{ foo.count }}` (where `foo` is a `str`) raised `ValueError: no signature found for builtin <built-in method count of str object>` instead of rendering `string_if_invalid` / empty. Triggered via `{% include ... with bar=foo %}` but the include is a red herring — any lookup on a built-in method reproduces it.

**Root cause / files:**
- `django/template/base.py`, `Variable._resolve_lookup` (~lines 867–930). After `current()` raises `TypeError`, the handler calls `inspect.signature(current)` (~line 913) to distinguish "needs arguments" from "call failed". Builtins like `str.count` have no introspectable signature, so `inspect.signature` raises `ValueError`, which escapes the inner `except TypeError` and propagates out of the catch-all.

**Fix:** Wrap the `inspect.signature()` call in its own `try/except ValueError`, and on `ValueError` set `current = context.template.engine.string_if_invalid` rather than re-raising. Keep the existing `signature.bind()` / `TypeError` logic for real argument-required callables.

**Tests:** `tests/template_tests/test_callables.py` (`CallableVariablesTests`) is the closest existing coverage; add a case there for a built-in method (e.g. `{{ value.count }}` on a string) asserting empty/`string_if_invalid`. Related `string_if_invalid` assertions live in `tests/template_tests/syntax_tests/test_basic.py`, `test_include.py`, `test_with.py`, `test_for.py`, `test_exceptions.py`.

**Docs:** `docs/ref/templates/api.txt` documents `string_if_invalid` and silent variable failures; behavior is unchanged for valid callables, so likely no doc change needed.

**Ruled out:** The `include`/`with` path — it only supplies the value; failure occurs during variable resolution. Also not a regression in `Context` lookup order or numpy-style `ValueError` handling in the dictionary-lookup branch (~line 887).

**Conclusion:** One localized fix in `_resolve_lookup`; no engine-wide changes.
