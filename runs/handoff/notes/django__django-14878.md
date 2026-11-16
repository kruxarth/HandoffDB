# Handoff: SQLite introspection — PK/type detection

**Issue:** `inspectdb` against SQLite fails to detect primary keys declared with table-level `PRIMARY KEY(pId)`, and mistypes `DOUBLE` and `UNSIGNED INTEGER` columns (repro table in issue).

**Files that matter:**
- `django/db/backends/sqlite3/introspection.py`
  - L80–112 `get_table_description`: runs `PRAGMA table_info` (L85–86), consumes the `pk` flag (L108), and calls `get_primary_key_column` (L112).
  - L202–225 `get_primary_key_column`: deliberately avoids `PRAGMA` (see comment L204) and parses the `CREATE TABLE` SQL. It only recognizes column-level `PRIMARY KEY`, not the table-constraint form — **root cause of the PK bug**.
  - L361–423 `get_constraints`; `pk_column` at L423.
  - L26–40 `FlexibleFieldLookupDict.base_data_types_reverse`: has `smallint/integer/bigint unsigned` but no `double` and no `unsigned integer` spelling — **root cause of type bugs**.
- `django/core/management/commands/inspectdb.py` L78, L81 consume the above.
- `django/db/backends/sqlite3/base.py` L338, L360 also call `get_primary_key_column`.

**Tests:** `tests/backends/sqlite/test_introspection.py` L11–29 (only quoted identifiers today — add a table-level PK case); `tests/introspection/tests.py` L77–131 and L180–183; `tests/inspectdb/tests.py` L68 and L151+.

**Docs:** no entry in `docs/releases/4.1.txt`; add a release note if behavior changes.

**Ruled out:** Using `PRAGMA table_info`'s `pk` flag inside `get_primary_key_column` — the code explicitly avoids `PRAGMA` there due to transaction issues (L204), so fixing `get_table_description` alone won't help.

**Conclusion:** Fix the SQL parsing in `get_primary_key_column` to accept table-level `PRIMARY KEY(...)`, and add `'double': 'FloatField'` plus an `'unsigned integer'` mapping to `base_data_types_reverse`.
