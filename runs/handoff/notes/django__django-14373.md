# Handoff: DateFormat.Y() zero-padding

**Issue:** `Y` (four-digit year) in `django.utils.dateformat.DateFormat` returned unpadded values for years < 1000 (e.g. `476` instead of `0476`).

**Key code:**
- `django/utils/dateformat.py:315-317` — `Y()` returns `self.data.year` (an `int`). Root cause: no `%04d` padding. Contrast with `y()` at `:311-313`, which correctly uses `'%02d'`.
- `django/utils/dateformat.py:33-45` — `Formatter.format()`; line 42 does `str(getattr(self, piece)())`, so the int is stringified without padding. The `Y` char is already matched by `re_formatchars` (`:28`), so dispatch is fine.

**Tests:** `tests/utils_tests/test_dateformat.py`
- `test_year_before_1000` (`:169-180`) covers only `y`, not `Y` — the gap that hid this bug.
- Existing `Y` assertions (`:105`, `:111`, `:117`) use 1979/2100 only.
- Add `Y` cases here (e.g. years 4, 42, 476 → `'0004'`, `'0042'`, `'0476'`).

**Docs:** `docs/ref/templates/builtins.txt`, the `date` filter `Y` specifier (states four-digit year) — confirms intended behavior; no doc change needed, though check the `dateformat` reference if it lists return types.

**Ruled out:** `y()` padding (already correct), regex dispatch for `Y` (present at `:28`), and `Formatter` string coercion (it merely exposes the unpadded int). No other callers depend on `Y()` returning an int; `django/template/defaultfilters.py:12` consumes `format()` which returns a joined string.

**Conclusion:** Change `Y()` to return `'%04d' % self.data.year` (string, matching `y()`), and extend `test_year_before_1000` to assert padded `Y` output. Verify no internal code expects an integer from `Y()`.
