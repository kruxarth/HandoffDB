# Handoff: values()/values_list() crash on combined querysets ordered by unannotated columns

**Issue:** `qs1.union(qs2).values_list('name').first()` emits an invalid `ORDER BY` column in the second combined query: the `__orderbycol2` select references `queries_celebrity.id` instead of `queries_reservedname.id`. Regression introduced by commit `464a4c0c59277056b5d3c1132ac1b4c6085aee08`.

**Relevant code:**
- `django/db/models/sql/compiler.py:272-400` (`get_order_by`). Lines 326 and 368 check `self.query.combinator and self.select`; line 390 builds `__orderbycol{idx}` aliases. The order-by expression (a `Col` bound to the original query's alias) is appended to each combined query's select without relabeling to that combined query's alias — this is the bug.
- `django/db/models/sql/compiler.py:443-492` (`get_combinator_sql`) compiles each combined query; the order-by columns need per-query resolution here or in `get_order_by`.
- `django/db/models/sql/query.py:566+` (`combine`), `:212-213` (`combinator` state) — checked; not the source.
- `django/db/models/expressions.py:817-851` (`Col.relabeled_clone`) — works correctly; ruled out.

**Tests:** `tests/queries/test_qs_combinators.py:154-209` (existing union/values_list/order coverage, esp. `test_union_with_values`, `test_union_with_values_list_and_order`). Models: `tests/queries/models.py:143-150` (`Number`), `:265-271` (`Celebrity`), `:299-305` (`ReservedName`). Docs: `docs/ref/models/querysets.txt` (union/values sections).

**Ruled out:** `Query.combine`, `Query.exists` combined-query handling, `Col.relabeled_clone`, MySQL backend compiler, and `find_ordering_name` (compiler.py:725+).

**Conclusion:** `get_order_by` adds order-by select columns once, using the outer query's table alias; combined queries must relabel these columns to their own alias (or add per-combined-query order-by selects). Git history is a single shallow snapshot (`ac35901`), so the upstream fix couldn't be diffed — verify against current Django master.
