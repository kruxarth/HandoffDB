## Handoff note

**Issue:** `MyModel.objects.filter(~Exists(MyModel.objects.none()), name='test')` renders an empty `WHERE` (whole query becomes `EmptyResultSet`). Related to #33018.

**Key code**
- `django/db/models/expressions.py:1199` — `Exists(Subquery)`. Its `as_sql()` compiles the inner query, which raises `EmptyResultSet` for `.none()`; nothing substitutes a constant.
- `django/db/models/expressions.py:153` — `BaseExpression.empty_result_set_value = NotImplemented`; the existing fallback protocol (`Func.as_sql`, ~lines 705-713; `compiler.py:275-281`) shows the intended pattern: on `EmptyResultSet`, compile `Value(empty_result_set_value)` if defined, else re-raise.
- `django/db/models/sql/where.py:69-102` — `WhereNode.as_sql()` propagates `EmptyResultSet` for AND-connected children, which is why the entire `WHERE` block (including `name='test'`) vanishes rather than just the `Exists` term.
- `django/db/models/lookups.py:417` — `In.process_rhs` raising `EmptyResultSet` for empty RHS is the #33018 analogue; not the cause here.

**Tests / docs**
- `tests/expressions/tests.py:1889` — `ExistsTests` (natural home for a regression test); see also `test_exists_in_filter` (~line 770) and `tests/queries/tests.py:1936` `ExistsSql`.
- `tests/annotations/tests.py:234-239` — `test_empty_queryset_annotation` covers empty `Subquery` in SELECT.
- `docs/ref/models/expressions.txt` (`Exists`), `docs/releases/4.1.txt`.

**Ruled out:** `WhereNode` connector logic, `lookups.In` empty-RHS handling, and the `SQLCompiler.get_select` fallback — all behave correctly; the defect is the missing `EmptyResultSet` handling for `Exists`/`Subquery` during compilation.

**Conclusion:** Give `Exists` `empty_result_set_value = False` (and have `Subquery.as_sql` catch `EmptyResultSet` and emit `Value(empty_result_set_value)`), so `~Exists(empty)` compiles to a truthy constant instead of dropping the `WHERE` clause; add a test in `ExistsTests`.
