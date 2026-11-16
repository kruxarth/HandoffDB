# Handoff: SQLite unique-constraint column order introspection

**Issue:** `get_constraints()` on SQLite omits the `orders` key for unique constraints (e.g. `unique_together` / `UniqueConstraint`), so introspection can't report ASC/DESC per column.

**Key code:**
- `django/db/backends/sqlite3/introspection.py`
  - `get_constraints()` ~lines 380–425: constraints parsed from `CREATE TABLE` SQL; the loop at 415–421 attaches `type`/`orders` only to entries coming from `PRAGMA index_list`/`index_info`, not to unique constraints parsed from the table definition. This is the gap.
  - `_get_index_columns_orders()` line 440: parses ASC/DESC from index SQL; reuse it for unique-constraint SQL.
  - `_parse_column_or_constraint_definition()` lines 241+ collects `unique_columns` but no orders.
- `django/db/backends/sqlite3/schema.py:18` — unique constraints are emitted as `CREATE UNIQUE INDEX`, so order info exists in `sqlite_master`.

**Tests/docs:**
- `tests/introspection/tests.py:201` `test_get_constraints_indexes_orders` (guarded by `supports_index_column_ordering`); model `Comment` unique_together at `tests/introspection/models.py:29`.
- `tests/schema/tests.py:203` `assertIndexOrder`, `test_order_index` at 2414.
- `docs/releases/4.0.txt`; base API doc in `django/db/backends/base/introspection.py:188`.

**Ruled out:** schema-emission path (`sql_create_unique` already produces ordered unique indexes); feature flag `supports_index_column_ordering` (defaults True at `base/features.py:151`).

**Conclusion:** Fix is in SQLite introspection: populate `orders` for unique constraints parsed from table SQL, not only for `index_list` entries. Add/extend the introspection test to assert orders on a multi-column unique constraint.
