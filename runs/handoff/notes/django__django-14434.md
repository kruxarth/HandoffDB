## Handoff: `_create_unique_sql` makes `references_column` always false

**Issue:** Statements returned by `SchemaEditor._create_unique_sql()` pass a `Table` object where `Columns` expects a plain table-name string, so `Statement.references_column()` never matches.

**Root cause / files:**
- `django/db/backends/base/schema.py:1225-1268` — `_create_unique_sql`. At line 1246 it builds `table = Table(model._meta.db_table, self.quote_name)`. At line 1254 it calls `self._index_columns(table, columns, ...)`, passing that `Table` instance.
- `django/db/backends/base/schema.py:1068-1069` — `_index_columns` forwards its `table` argument straight into `Columns(table, ...)`.
- `django/db/backends/ddl_references.py:17-20` (`Table`), `:60-75` (`TableColumns.references_column`, compares `self.table == table`), `:77+` (`Columns`). Because `Table.__init__` runs the quoting callable, `Columns.table` becomes a *quoted* string while callers pass unquoted names — comparison fails, hence always `False`.

Contrast: `_create_index_sql` (schema.py:1050-1054) passes the raw string `table`, which is correct.

**Fix direction:** In `_create_unique_sql`, pass `model._meta.db_table` (the string) to `_index_columns` at line 1254, or otherwise construct `Columns` with the string; keep the `Table` instance only for the `Statement`'s `table=` argument. Note `_create_unique_sql` is called from schema.py:156, 412, 793, 1204 and `django/db/models/constraints.py:205`.

**Related tests:**
- `tests/schema/tests.py:2202-2400` — `test_func_unique_constraint*` tests assert `sql.references_column(table, ...)`; these exercise the path and are the natural regression tests.
- `tests/backends/test_ddl_references.py:42-57` — direct `Columns.references_column` unit tests.
- `tests/constraints/tests.py:34-40` — `BaseConstraint.create_sql` stubs.

**Ruled out:** `IndexName`/naming (uses the string table correctly); `Expressions` branch (schema.py:1256) already passes `model._meta.db_table`; PostgreSQL override `django/db/backends/postgresql/schema.py:212-215` simply delegates and is unaffected.

**Conclusion:** One-line argument-type bug at schema.py:1254; fix by passing the table name string.
