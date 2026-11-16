## Handoff: `exists()` adds constant to `GROUP BY`

**Issue:** `Manager.values('field').annotate(cnt=Count('id')).filter(cnt__gt=1).exists()` generates `GROUP BY field, (1)`. `Query.exists()` replaces SELECT with a constant via `add_extra({"a": 1})`, producing a `RawSQL("1")`. `get_group_by()` then includes every SELECT expression, and `RawSQL.get_group_by_cols()` returns itself, adding `(1)` to GROUP BY.

**Key code:**
- `django/db/models/sql/query.py:563` (`Query.exists()`) uses `add_extra`/`set_extra_mask`; see also `clear_select_clause()` at `2097-2107`, `add_extra()` at `2279`, `set_extra_mask()` at `2377`.
- `django/db/models/sql/compiler.py:65-77` (`pre_sql_setup()`) passes `self.select + extra_select` into `get_group_by()` at line 76.
- `django/db/models/sql/compiler.py:79-150` (`get_group_by()`) builds GROUP BY from SELECT expressions.
- `django/db/models/expressions.py:990-991`: `Value.get_group_by_cols()` already returns `[]`.
- `django/db/models/expressions.py:1022-1035`: `RawSQL.get_group_by_cols()` returns `[self]`, causing the constant.

**Tests/docs:**
- `tests/queries/tests.py:2218-2261` (`ExistsSql`) is the natural regression-test location; use `CaptureQueriesContext` and assert no constant appears in GROUP BY.
- `tests/aggregation/tests.py:1409-1435`, `1589-1603`, and `2044-2063` cover related annotation/GROUP BY/`Exists()` behavior.
- `docs/releases/4.1.txt` has no entry yet; `docs/releases/2.0.6.txt:18` is a historical related GROUP BY regression note.

**Ruled out:** Changing `Value.get_group_by_cols()` (already correct); `get_extra_select()` (`compiler.py:466-474`) only handles distinct/order-by extras, not this path; changing the hardcoded value to `2` is invalid due GROUP BY ordinal ambiguity.

**Conclusion:** Fix `Query.exists()` to use an annotation with `Value(1)` instead of `add_extra({"a": 1})`, so GROUP BY excludes the constant. No files were edited and no tests were run.
