# Handoff: QuerySet.update() FieldError when ordered by annotation

## Issue
`QuerySet.update()` raises `FieldError` ("Cannot resolve keyword ... into field") when the queryset is ordered by an annotated field. Ordering by real model fields or no ordering works fine; the admin path just exposes it.

## Root cause / files
- `django/db/models/query.py:1161-1183` (`QuerySet.update`) and `:1186-1200` (`_update`): both set `query.annotations = {}` (lines 1173, 1198) but do **not** clear `order_by`. The stale ordering still references the removed annotation.
- `django/db/models/sql/compiler.py:1740-1747` (`SQLUpdateCompiler.as_sql`) calls `pre_sql_setup()`.
- `django/db/models/sql/compiler.py:1828-1864` (`SQLUpdateCompiler.pre_sql_setup`): only calls `query.clear_ordering(force=True)` in the multi-table path (`count_active_tables() != 1`). Single-table updates keep ordering, which `get_order_by` (`compiler.py:410`, `_order_by_pairs` at `:306`) then tries to resolve against the now-cleared annotations, producing the error.
- `django/db/backends/mysql/compiler.py:48-68` intentionally emits `UPDATE ... ORDER BY` (MySQL/MariaDB); ordering matters for unique-constraint updates, so don't blanket-remove it for all backends without thought.

## Tests
- `tests/update/tests.py`: `test_update_annotated_queryset` (175), `test_update_annotated_multi_table_queryset` (197), `test_update_with_joined_field_annotation` (213); ordering tests at 241-283 (`test_order_by_update_on_unique_constraint*`, related field); `MySQLUpdateOrderByTest` (233).
- Models: `tests/update/models.py` (`DataPoint`, `RelatedPoint`, `UniqueNumber`, `UniqueNumberChild`).
- Docs: `docs/ref/models/querysets.txt` (`update()`, `order_by()`).

## Ruled out
Admin code (`django/contrib/admin/options.py:390-417`) is not at fault — it merely passes the user's ordering through. MySQL's `UPDATE ... ORDER BY` support is deliberate. Multi-table updates already clear ordering correctly.

## Conclusion
Bug is in `QuerySet.update()`/`_update` failing to clear ordering before discarding annotations (or vice versa). Fix there (or in the single-table `pre_sql_setup` branch), add a regression test in `tests/update/tests.py`. Could not run tests locally — `asgiref` is not installed in this environment.
