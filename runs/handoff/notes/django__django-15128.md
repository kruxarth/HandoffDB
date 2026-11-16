# Handoff note

## Issue
`qs1 | qs2` raises `AssertionError` in `Query.change_aliases()` when the RHS query has sequential aliases (e.g. `T4`, `T5`) and its related table names already exist in the LHS `table_map`. The reverse operation `qs2 | qs1` works, so OR is not alias-commutative.

## Relevant code
- `django/db/models/sql/query.py:557-565` — `Query.combine()` merges RHS and is the entry point for `sql.OR`.
- `django/db/models/sql/query.py:748-` — `table_alias()` creates aliases; collision occurs here.
- `django/db/models/sql/query.py:843-` — `change_aliases()` asserts `change_map` keys/values are disjoint. The failing map is `{'T4': 'T5', 'T5': 'T6'}`.
- `django/db/models/sql/query.py:951-` — `join()` calls alias allocation.
- `django/db/models/sql/query.py:358-361` — `relabeled_clone()` calls `change_aliases()`.
- `django/db/models/query.py:339-351` — `QuerySet.__or__()` calls `query.combine(other.query, sql.OR)`.

## Tests/docs
- `tests/queries/tests.py:2089+` — `QuerySetBitwiseOperationTests`; best place for a regression test.
- `tests/queries/tests.py:1316-1335` — existing combine/join reuse tests, including circular `change_map` case `#26522`.
- `docs/ref/models/expressions.txt:1006-1019` — documents `relabeled_clone(change_map)`.
- `docs/releases/1.11.5.txt:54` — prior `#26522` alias/join note.

## Ruled out
Not a `Q`-combination bug (`tests/queries/test_q.py`), not covered by `test_qs_combinators.py`, and no existing regression test exercises alias collision during `QuerySet.__or__`.

## Conclusion
This is a real alias-allocation bug in `Query.combine()`/`table_alias()`/`join()`: new aliases can collide with aliases already present in the RHS `alias_map`, making the `change_aliases()` assertion fire. Fix should ensure generated aliases avoid RHS aliases (e.g. pass the RHS `alias_map` into join/alias allocation or increment until unused), add a regression test in `tests/queries/tests.py`, and consider documenting OR’s non-commutative alias behavior.
