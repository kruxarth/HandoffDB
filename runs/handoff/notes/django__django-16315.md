# Handoff: bulk_create() conflict clause uses field names, not db_column

## Issue
`QuerySet.bulk_create(..., update_conflicts=True, update_fields=[...], unique_fields=[...])` generates an `INSERT` with correct `db_column` names, but the `ON CONFLICT`/`DO UPDATE SET` clause uses model field names. On PostgreSQL this raises `column "blacklistid" does not exist`; expected `"BlacklistID"`.

## Where it matters
- `django/db/models/sql/compiler.py:1688-1698` builds the INSERT column list correctly via `f.column`.
- `django/db/models/sql/compiler.py:1725-1730` passes `self.query.unique_fields`/`update_fields` to the backend; these are field-name strings, not columns.
- `django/db/backends/postgresql/operations.py:352-364` quotes those names directly for `ON CONFLICT(...)` and `EXCLUDED....`.
- `django/db/backends/sqlite3/operations.py:415-429` has the same bug.
- `django/db/backends/mysql/operations.py:436-459` also uses `update_fields` names (MySQL ignores `unique_fields`).
- `django/db/models/query.py:688-741, 786-788` validates/converts names to fields but stores/returns names.
- `django/db/models/sql/subqueries.py:145-153` holds the raw lists.

## Tests/docs
- `tests/bulk_create/tests.py:448-546` covers conflict options but never uses `db_column`; add a regression case here.
- `docs/ref/models/querysets.txt:2282-2353` documents `bulk_create` options.

## Ruled out
INSERT column generation is correct; MySQL/PostgreSQL/SQLite all share the defect; base `operations.py:773-774` returns empty. No existing `db_column` conflict tests.

## Conclusion
Fix belongs in each backend's `on_conflict_suffix_sql` (and/or its callers in compiler.py) so conflict/update columns resolve via `field.column` rather than `quote_name(field_name)`. Repo is Django 4.2.0 alpha (`django/__init__.py:3`).
