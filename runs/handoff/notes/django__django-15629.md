## Handoff: db_collation not propagated to foreign keys

**Issue:** A primary key declared with `db_collation` (e.g. `ShortUUIDField(db_collation='utf8_bin')`) produces FK columns without the matching collation. On MySQL, `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY` then fails because the referenced column's collation differs from the FK column's.

**Relevant code:**
- `django/db/models/fields/related.py:1179-1183` — `ForeignKey.db_type()` delegates to `target_field.rel_db_type()`, but `ForeignKey.db_parameters()` returns only `{"type", "check"}`, dropping the target's `collation`. This is the root cause.
- `django/db/models/fields/related.py:496-507` — `target_field` property (source of the collation that should be copied).
- `django/db/backends/base/schema.py:278-283` — `_iter_column_sql()` yields `self._collate_sql(field_db_params.get("collation"))`; since FK params carry no collation, FK columns never get `COLLATE`.
- `django/db/backends/base/schema.py:917-922` and `1185-1192` — `alter_field` / `_alter_column_collation_sql` only handle a field's own collation change, not collations inherited through relations.
- `django/db/backends/base/schema.py:46-66` (`_related_non_m2m_objects`) — used to propagate changes to related fields; a natural hook for fixing FKs.

**Tests:** `tests/schema/tests.py:4520-4700` (`test_db_collation_charfield`, `_textfield`, `test_add_field_db_collation`, `test_alter_field_db_collation`, `test_alter_primary_key_db_collation`, `test_alter_field_type_and_db_collation`, `test_ci_cs_db_collation`); helpers at `tests/schema/tests.py:265-268` (`get_column_collation`). Models in `tests/schema/models.py`.

**Docs:** `docs/ref/models/fields.txt` (`db_collation`), `docs/ref/databases.txt` (MySQL collation requirements).

**Ruled out:** Backend schema editors — `grep db_collation django/db/backends/` returns nothing; MySQL templates (`django/db/backends/mysql/schema.py:12`, `sql_alter_column_collate`) already emit `%(collation)s` correctly. Collation storage on `Field`/`CharField` (`django/db/models/fields/__init__.py:1120-1122`, `1187`) is fine.

**Conclusion:** Fix belongs in `ForeignKey.db_parameters()` — propagate `collation` from `target_field.db_parameters()` — so schema SQL generation emits `COLLATE` for FK columns.
