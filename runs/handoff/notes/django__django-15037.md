# Handoff: inspectdb drops `to_field` for FKs to non-PK unique columns

**Issue:** `inspectdb` emits `ForeignKey` to the referenced table's PK even when the actual DB constraint targets a different unique column (e.g. `foo(other_id)`). The generated `to_field` is missing.

**Key files / line ranges:**
- `django/core/management/commands/inspectdb.py`
  - L74: `relations = connection.introspection.get_relations(...)` — this is the data source for FKs.
  - L97/L110: `column_to_field_name` mapping.
  - L173: `get_meta` call; `get_meta` defined at L266.
  - `get_field_type` (~L229+) builds the `models.ForeignKey(...)` params — needs to append `to_field=` when the referenced column isn't the target PK.
- `django/db/backends/base/introspection.py`
  - L147 `get_relations()` returns `{field: (other_field, other_table)}` — no referenced column, so it can't carry `to_field`. This is the root cause.
  - L158 `get_key_columns()` already returns `(column, ref_table, ref_column)` — useful reference, and confirms backend data exists.
- Backend overrides: `django/db/backends/{postgresql,mysql,sqlite3,oracle}/introspection.py` (`get_relations` implementations) — all would need to return the referenced column.

**Tests / docs:**
- `tests/inspectdb/tests.py` — FK tests around L180–203 (`can_introspect_foreign_keys` block) are the model for a new test.
- `tests/inspectdb/models.py` — add a model with a FK to a unique non-PK field.
- `docs/ref/django-admin.txt` (inspectdb section) and any backend `get_relations` docstrings.

**Ruled out:** `get_key_columns` is not the gap — it already exposes the referenced column; the defect is that `get_relations` discards it and `inspectdb` never reads a referenced column.

**Conclusion:** extend `get_relations` to return the referenced column (across all backends) and have `get_field_type` emit `to_field=<col>` when it differs from the target PK.
