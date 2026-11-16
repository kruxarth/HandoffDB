## Handoff: SelectDateWidget OverflowError

**Issue.** `SelectDateWidget` crashes with `OverflowError` when a user submits a year larger than `sys.maxsize` (e.g. `?my_date_day=1&my_date_month=1&my_date_year=1234567821345678`). `form.is_valid()` reaches the widget's `value_from_datadict`, which calls `datetime.date(int(y), int(m), int(d))`; the `int()` is fine but the date constructor overflows. Because only `ValueError` is caught, the `OverflowError` propagates and yields a 500.

**Files/lines.**
- `django/forms/widgets.py` — `SelectDateWidget` class begins line 1010; `value_from_datadict` at line 1149; the offending `datetime.date(int(y), int(m), int(d))` is line 1159. The surrounding `try/except ValueError` must also handle `OverflowError` (returning the raw `"%s-%s-%s"` string so field validation produces a `ValidationError` instead of crashing).
- `django/forms/fields.py:568` — `DurationField.to_python` already catches `OverflowError` and raises `ValidationError`; use as the precedent pattern.

**Tests/docs.** Add regression tests in `tests/forms_tests/widget_tests/test_selectdatewidget.py` (a `value_from_datadict` test with an oversized year, asserting no exception and invalid-data behavior). Update `docs/ref/forms/widgets.txt` (SelectDateWidget section) only if behavior wording changes; add a `docs/releases/5.0.txt` bugfix note.

**Ruled out.** `django/contrib/admin/templatetags/admin_list.py:394` has a similar `datetime.date(int(...))` but is a separate admin date-hierarchy path, not reached via widget validation. Other `OverflowError` handlers (`django/views/static.py:119`, `django/views/generic/dates.py:213`, template filters/tags) are unrelated.

**Conclusion.** Fix is localized: broaden the `except` at `django/forms/widgets.py:1159` to `(ValueError, OverflowError)`. Verify via the repro URL (GET and POST) and the new widget test.
