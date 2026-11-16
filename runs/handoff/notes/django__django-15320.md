**Handoff note — Subquery.as_sql() invalid SQL**

**Issue:** `Subquery.as_sql()` returns SQL with the first and last characters stripped, e.g. `(ELECT ... FROM "apps_app)` instead of `(SELECT ... FROM "apps_app")`. Manually setting `Subquery(...).query.subquery = True` fixes it.

**Relevant code:**
- `django/db/models/expressions.py:1141-1210` — `Subquery` class. `__init__()` at `1150-1154` stores `self.query` but never marks it as a subquery. `as_sql()` at `1177` assumes the inner query SQL is already parenthesized and slices it, so unwrapped SQL loses its first/last characters.
- `django/db/models/sql/query.py:176` — `Query.subquery` defaults to `False`.
- `django/db/models/sql/query.py:1079-1090` — `Query.as_sql()` only wraps SQL in parentheses when `self.subquery` is true. This explains why the slice is wrong for a plain `Subquery(QuerySet)`.
- `django/db/models/sql/query.py:446`, `1049` — other internal subquery paths set `subquery = True`, so they do not expose the bug.

**Tests/docs:**
- `tests/expressions/tests.py` — `BasicExpressionsTests.test_subquery` at `449`, `test_subquery_eq` at `521`, `test_in_subquery` at `540`, and `test_subquery_in_filter` at `769` exercise subquery behavior but not direct `Subquery.as_sql()` with an unmarked query.
- Add a regression test around `tests/expressions/tests.py:449`.
- Release note belongs in `docs/releases/4.1.txt`; `docs/ref/models/expressions.txt` documents `Subquery`.

**Ruled out:** `Query.as_sql()` parenthesization and compiler behavior are correct; the failure is the missing `subquery` flag on the `Subquery`-owned query combined with `Subquery.as_sql()`’s unconditional slicing.

**Conclusion:** Set `self.query.subquery = True` in `Subquery.__init__()` (or stop slicing in `Subquery.as_sql()`).
