# Handoff: default value for `Sum` aggregation

**Issue:** `Sum()` annotations/aggregates yield `NULL` when there is nothing to sum; users want `0` (or a configurable default).

**Key finding:** The repo (Django 4.0 alpha) already implements this via `empty_aggregate_value`.

- `django/db/models/aggregates.py`: `Aggregate.empty_aggregate_value = None` (line 23); `Sum.empty_aggregate_value = 0` (line 111). `Aggregate.__init__` (lines 25–30) accepts only `distinct` and `filter` — there is no `default=` kwarg.
- `django/db/models/sql/query.py` lines 487–495: the empty-result-set optimization substitutes `expression.empty_aggregate_value` (returned at line 494) instead of hitting the DB.
- `django/db/models/expressions.py`: `BaseExpression.empty_aggregate_value = NotImplemented` (line 156); `Value.empty_aggregate_value` returns `self.value` (lines 799–801).
- `django/db/models/functions/comparison.py` lines 59–74: `Coalesce.empty_aggregate_value` picks the first non-null/non-`NotImplemented` source value — the current documented workaround.
- `django/contrib/postgres/aggregates/statistics.py` line 39: `RegrCount.empty_aggregate_value = 0`.

**Tests:** `tests/aggregation/tests.py` — `test_empty_aggregate` (line 105), `test_empty_result_optimization` (line ~1348 onward, incl. `Coalesce` cases at 1375–1399); `tests/aggregation_regress/tests.py:974` (`test_empty_filter_aggregate`). No test references a `default=` argument.

**Docs:** `docs/ref/models/expressions.txt` lines 421–425 and 969 (`empty_aggregate_value`); `docs/releases/4.0.txt` lines 282–283; `docs/ref/models/querysets.txt` lines 3664–3681 (`Sum`); `docs/ref/models/database-functions.txt` lines 73–76 (`Coalesce` example).

**Ruled out:** No `default=`/`allow_default` support exists anywhere in `django/` or `tests/`; the monkeypatch `COALESCE` approach is unnecessary for the empty-result-set case.

**Conclusion:** Empty-result-set behaviour is fixed (`Sum` → `0`). Remaining gap is a per-aggregate user-specified default (e.g. `Sum('x', default=...)`); otherwise `Coalesce(Sum(...), Value(0))` is the sanctioned pattern.
