## Handoff note

**Issue:** Django admin `__in` lookups split query values on commas in `prepare_lookup_value()`, so values containing commas cannot be filtered (e.g. `?username__in=johnny,viola,gordon`).

**Key code:**
- `django/contrib/admin/utils.py:54-64` — `prepare_lookup_value()`; line 60 does `value.split(',')` when the lookup key ends with `__in`. This is the root cause.
- `django/contrib/admin/utils.py:18-20,67-78` — existing admin `quote()`/`unquote()` helpers and maps; potentially relevant if choosing an escaping scheme.
- `django/contrib/admin/views/main.py:215` — applies `prepare_lookup_value()` to changelist query params.
- `django/contrib/admin/filters.py:130` — applies it to list-filter params.

**Tests/docs:**
- `tests/admin_utils/tests.py:96` `UtilsTests`; add regression coverage here. Existing `test_quote` at line 411 is nearby but unrelated.
- `tests/admin_filters/tests.py:1223` covers `__in` parameter handling for `SimpleListFilter`.
- `tests/admin_changelist/tests.py` covers changelist lookup behavior.
- `docs/ref/contrib/admin/index.txt:1051` mentions comma-separated values; release notes are `docs/releases/4.1.txt:51`.

**Ruled out:**
- `django/contrib/admin/widgets.py:221` and `url_params_from_lookup_dict()` at `widgets.py:100-116` are separate raw-ID/limit-choices-to handling.
- `smart_split()` in `django/contrib/admin/options.py:1034` is for search terms, not `__in` filtering.
- `filters.py` expected-parameter logic is not the splitting bug.

**Conclusion:** Fix belongs in `prepare_lookup_value()` in `django/contrib/admin/utils.py`, replacing the unconditional comma split with comma-aware parsing/escaping. Add regression tests under `tests/admin_utils/tests.py`, plus changelist/filter coverage as needed. No files were edited and no tests were run.
