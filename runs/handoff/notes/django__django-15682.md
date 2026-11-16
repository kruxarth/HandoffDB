# Handoff: Deprecate `False` for `OrderBy`'s `nulls_first`/`nulls_last`

## Issue
`OrderBy.__init__` defaults both `nulls_first` and `nulls_last` to `False`, so passing `nulls_first=False` is indistinguishable from omitting it; SQL falls back to the database default and nulls still sort first. Passing `False` should be deprecated in favour of `None`.

## Files and lines
- `django/db/models/expressions.py:1500-1510` — `OrderBy.__init__`; defaults `False`/`False`, mutual-exclusion check at 1507-1508, attribute assignment at 1509-1510. This is the core change site: default to `None`, warn (`RemovedInDjango50Warning`) when `False` is explicitly passed.
- `django/db/models/expressions.py:1520-1545` — `as_sql`; branches on `self.nulls_last`/`self.nulls_first` (1530-1532) and `order_by_nulls_first` feature (1535-1541). Must treat `None` as "unset" and only emit `NULLS FIRST/LAST` when explicitly `True`.
- `django/db/models/expressions.py:1575-1577` — `reverse_ordering` toggles both flags when either is truthy; this is wrong once `None` is possible and needs rework.
- `django/db/models/expressions.py:417-421, 799-803` — `asc()`/`desc()` forward `**kwargs` to `OrderBy`; no change needed but they are the public entry points.
- `django/db/models/sql/compiler.py:320-400` — all internal `OrderBy(...)` constructions omit nulls args, so they are unaffected.

## Tests and docs
- `tests/ordering/tests.py:111-165` — `test_order_by_nulls_first_and_last`, `test_order_by_nulls_last`, `test_order_by_nulls_first`; add `assertWarnsMessage` cases here.
- `tests/expressions/tests.py` — `OrderByTests` (around line 2540, `test_equal`).
- `docs/ref/models/expressions.txt:248-256, 1036-1047` — signatures showing `nulls_first=False, nulls_last=False`.
- `docs/releases/4.1.txt` — add deprecation note.

## Ruled out
No other Django code passes `nulls_first`/`nulls_last`; `compiler.py` calls use `descending` only. No existing deprecation warning covers this. Repo is 4.1.0 alpha; `RemovedInDjango50Warning` (`django/utils/deprecation.py:12`) is the right warning class.

## Conclusion
Confirmed bug. Deprecate explicit `False`, default to `None`, fix `as_sql` and `reverse_ordering`, update tests and docs.
