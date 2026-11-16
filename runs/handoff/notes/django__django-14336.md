## Handoff note

**Issue:** Subquery aliases are generated with inconsistent casing: `Col%d` vs `col%d`. On case-sensitive databases, outer references to lowercase aliases fail when inner SELECTs expose uppercase aliases.

**Key files/lines:**
- `django/db/models/sql/compiler.py`
  - L513: `SQLCompiler.as_sql(..., with_col_aliases=False)` entry point.
  - L556–557: emits `AS Col%d` when `with_col_aliases` is true.
  - L650–651: `get_select()` emits alias `col%d`.
  These two alias-generation paths must use identical casing.
- `django/db/models/sql/query.py`
  - L407: `__col%d` internal alias.
  - L469: relabels subquery aliases to `subquery`.
  Relevant context, but not the direct mismatch.
- `django/db/models/sql/compiler.py` L1653: calls `as_sql(with_col_aliases=True)` for subqueries.

**Tests:**
- `tests/queries/tests.py`
  - `Queries6Tests` starts L1749.
  - L1837: `test_distinct_ordered_sliced_subquery_aggregation`, the reported reproduction.
  - L2099: `test_subquery_aliases`, related nested subquery coverage.
- `tests/queries/test_query.py` L1–140: `alias_cols=False`/`Col` behavior, but no SQL-casing assertion.

**Docs:** No documentation references these generated aliases; no docs update appears needed.

**Ruled out:** Other `Col%d`/`col%d` hits in `django/contrib/postgres/indexes.py` L77 and `django/db/models/sql/query.py` L407 are unrelated to subquery output aliases. Existing tests exercise query behavior, not generated alias casing, so they would not catch this directly.

**Conclusion:** Confirmed a real inconsistency between `compiler.py` L557 and L651. Normalize both generated aliases to the same casing, preferably one consistent scheme such as `col%d`, and add a regression test asserting generated subquery SQL/aliases rather than only result behavior.
