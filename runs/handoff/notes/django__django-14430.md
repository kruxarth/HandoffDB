## Handoff: Coalesce in aggregation with EmptyResultSet

**Issue:** `filter(pk__in=[]).aggregate(test=Coalesce(Sum('quantity'), Value(0)))` returns `{'test': None}` instead of `0`. The empty `__in` produces `EmptyResultSet`, and `Query.get_aggregation()` converts every aggregate result to `None`, bypassing `Coalesce`.

**Code that matters**
- `django/db/models/sql/query.py:419` — `get_aggregation()`; the `except EmptyResultSet` branch (method end, originally cited as L439–445) is the blanket `None` conversion. This is the primary fault site.
- `django/db/models/lookups.py:399` — raises `EmptyResultSet` for empty `__in`; `django/db/models/sql/where.py:217` also raises it. This behavior is expected.
- `django/db/models/sql/compiler.py:1177-1178` — catches `EmptyResultSet` and returns no rows; `:264` and `:494-501` also handle it, but do not map aggregate aliases.
- `django/db/models/functions/comparison.py:59` — `Coalesce`; it has no empty-result-set fallback hook.
- `django/db/models/expressions.py:1082` — `Case.as_sql()` handles `EmptyResultSet` internally, an analogous but local pattern; no general `empty_result_set_value` mechanism exists in this snapshot.
- `django/db/models/aggregates.py:16,143` — `Aggregate`/`Sum`; no relevant empty-result handling.

**Tests/docs**
- `tests/aggregation/tests.py:104` (`test_empty_aggregate`), `:11` and `:1252` (`Coalesce` usage); no empty-`__in` + `Coalesce` aggregate regression test.
- `tests/db_functions/comparison/test_coalesce.py:13` — `CoalesceTests`; no aggregate/empty-result coverage.
- `tests/annotations/tests.py:202` — empty `pk__in` with `ExpressionWrapper`, not aggregation.
- `tests/postgres_tests/test_aggregates.py:47,487` — backend-specific empty result set tests.
- Related docs: `docs/topics/db/aggregation.txt`, `docs/ref/models/database-functions.txt`.

**Ruled out:** `Coalesce`/`Sum` implementations and `EmptyResultSet` raising in lookups/where are not directly faulty; compiler handling is correct. The defect is the unconditional `None` mapping in `get_aggregation()`.

**Conclusion:** Confirmed bug. Fix `get_aggregation()` to honor expression-level fallback values (e.g. `Coalesce(..., Value(0))`) when `EmptyResultSet` occurs, and add regression tests. No code change was made.
