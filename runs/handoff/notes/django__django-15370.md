# Handoff: empty `__slots__` for `SafeString` / `SafeData`

## Issue
`SafeString` instances carry a `__dict__` that they never use (both classes define only methods), costing ~104 bytes each. Proposal: add `__slots__ = ()` to `SafeData` and `SafeString` so instances match `str` memory behavior, while still letting third-party subclasses add attributes.

## Files and line ranges
- `django/utils/safestring.py:11-18` — `SafeData` class body; add `__slots__ = ()` as the first statement.
- `django/utils/safestring.py:21-37` — `SafeString(str, SafeData)`; add `__slots__ = ()`. Keep `__add__` (26-34) and `__str__` (36-37) unchanged.
- `django/utils/safestring.py:40` — `SafeText = SafeString` alias; unaffected.
- `django/utils/safestring.py:63` — `mark_safe` returns `SafeString(s)`; unaffected.

All other consumers only do `isinstance(..., SafeData)` checks, not attribute access: `django/template/base.py:730,835,978`, `django/template/defaultfilters.py:45,215,416`, `django/utils/translation/trans_real.py:364,376`, `django/templatetags/i18n.py:93`. No changes needed there.

## Tests
- `tests/utils_tests/test_safestring.py` — main coverage (`test_mark_safe`, `test_mark_safe_str` at lines 27-32 asserts `str(s)` keeps type, `test_mark_safe_object_implementing_dunder_html` at 34-39).
- Related: `tests/i18n/tests.py:299-302`, `tests/messages_tests/test_session.py:56-62`, `tests/messages_tests/test_cookie.py:174`.
- Docs: `docs/ref/utils.txt` (`SafeString`/`mark_safe` section) — no API change, but note the new restriction if desired.

## Ruled out
- Subclasses adding attributes: still allowed, since subclasses without `__slots__` regain a `__dict__`.
- Attribute binding on `SafeString` itself (e.g. `s.test = 1`) now raises `AttributeError` — this is the intended, `str`-like behavior, not a bug.
- No measurable performance regression expected; only methods exist.

## Conclusion
Apply `__slots__ = ()` to both classes at the lines above; run the safestring, i18n, and messages test suites.
