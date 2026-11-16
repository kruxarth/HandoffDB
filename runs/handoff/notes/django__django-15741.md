## Handoff: lazy `format_type` in `get_format()`

**Issue:** `some_date|date:_('Y-m-d')` raises `TypeError: getattr(): attribute name must be string` from `django.utils.formats.get_format`. Regression from commit `659d2421c7adb` (#20296).

**Key files/lines:**
- `django/utils/formats.py:63–95` — `get_format()` uses `format_type` directly as the cache key and as the attribute name in `getattr(module, format_type, None)`. A lazy proxy reaches this code unchanged, causing the `TypeError`.
- `django/utils/formats.py:97–105` — `get_format_lazy()` returns a lazy proxy; it is not itself the defect.
- `django/template/defaultfilters.py:759–764` — `date()` passes its `arg` into `formats.date_format()`.
- `django/utils/dateformat.py:36–50` — `Formatter.format()` already coerces with `str(formatstr)`, so lazy format strings are handled here.

**Tests/docs:**
- `tests/i18n/tests.py` — `FormattingTests` (around line 529); add a regression test using `gettext_lazy()`/`get_format()` or the `date` filter with a lazy argument.
- `tests/template_tests/filter_tests/test_date.py` — date-filter coverage.
- Docs: `docs/ref/utils.txt` (`django.utils.formats`), `docs/ref/templates/builtins.txt` (`date`/`time`), `docs/topics/i18n/formatting.txt`.

**Ruled out:** `django/utils/dateformat.py` — `Formatter.format()` already stringifies its format argument, so the lazy proxy is safe there. The failure is specifically `getattr()` inside `get_format()`.

**Conclusion:** Normalize `format_type` to a concrete string at the start of `get_format()` (e.g. `format_type = str(format_type)`) before building the cache key or calling `getattr()`. Add the regression test in `tests/i18n/tests.py`; no change is needed in `dateformat.py`.
