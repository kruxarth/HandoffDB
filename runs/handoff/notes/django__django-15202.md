## Handoff: URLField raises `ValueError` instead of `ValidationError`

**Issue:** `forms.URLField().clean('////]@N.AN')` leaks `ValueError: Invalid IPv6 URL` from `urllib.parse.urlsplit()` instead of raising `ValidationError`.

**Key files/lines:**
- `django/core/validators.py:110-142` — `URLValidator.__call__`. A `ValueError` from `urlsplit()` is caught only in the IDN fallback at `117-119`. The later calls at `130` (`urlsplit(value).netloc`) and `142` (`urlsplit(value).hostname`) are unguarded. If the regex accepts a malformed bracketed host, these raise `ValueError`.
- `django/forms/fields.py:671-711` — `URLField`; `to_python()` at `695-710` rewrites missing scheme/netloc and passes the rebuilt URL into validation, so the validator must handle malformed URLs defensively.

**Tests/docs:**
- `tests/validators/tests.py:30-147` (`VALID_URLS`), `148+` (`INVALID_URLS`), and `539-540` — add a malformed IPv6/bracket URL as invalid.
- `tests/forms_tests/field_tests/test_urlfield.py` — `test_urlfield_clean` (~line 29) should assert `ValidationError` for `'////]@N.AN'`.
- `tests/forms_tests/tests/test_validators.py` — validator error aggregation.
- Docs: `docs/ref/validators.txt` (`URLValidator`), `docs/ref/forms/fields.txt` (`URLField`).

**Ruled out:** `URLField.to_python()` is not the direct source; the traceback ends in `URLValidator.__call__`. The existing `117-119` catch is insufficient because it only covers the fallback path. Python 3.14 did not reproduce the same `urlsplit()` failure for the rewritten forms, but the validator still has unguarded `urlsplit()` calls.

**Conclusion:** Wrap every `urlsplit()` call in `URLValidator.__call__` (`130`, `142`, and ideally `117`) and convert `ValueError` into `ValidationError(self.message, code=self.code, params={'value': value})`. Add regression tests. Environment note: Django import failed due missing `asgiref`, so tests were not run.
