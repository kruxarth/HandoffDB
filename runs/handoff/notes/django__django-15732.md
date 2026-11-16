# Handoff: cannot drop `unique_together` on a single field that is itself unique/PK

## Issue
`unique_together = (("id",),)` on a PK (or any field with `unique=True`) can't be removed by `AlterUniqueTogether`. `SchemaEditor` sees two matching unique constraints (`*_pkey` and `*_uniq`) and raises `ValueError: Found wrong number (2) of constraints`.

## Key code
- `django/db/backends/base/schema.py:520-536` — `alter_unique_together()`; the delete path calls `_delete_composed_index(..., {"unique": True}, self.sql_delete_unique)`. It passes only `unique=True`, so the field's own unique/PK constraint also matches.
- `django/db/backends/base/schema.py:559-580` — `_delete_composed_index()`; builds `meta_constraint_names`/`meta_index_names` and excludes only those, then raises at 571-575 when `len(constraint_names) != 1`. This is the crash site. The fix belongs here (or in the caller's `constraint_kwargs`), e.g. also excluding primary keys / the single-column unique constraint when deleting a one-field composed index.
- `django/db/backends/base/schema.py:1647-1700` — `_constraint_names()`; filter logic is correct, it faithfully returns both constraints.
- `django/db/backends/mysql/schema.py:138` — MySQL overrides `_delete_composed_index`; any signature change must stay compatible.

## Tests / docs
- `tests/schema/tests.py:2497` `test_unique_together`; `tests/schema/models.py:58, 74-80, 222-227` (`AuthorWithUniqueName`, `AuthorWithUniqueNameAndBirthday`, `UniqueTest`) — add a model with `unique_together` on a `unique=True`/PK field.
- `tests/migrations/test_operations.py:2730` `test_alter_unique_together`, `:2806` `test_alter_unique_together_remove`, `:3252` `test_alter_index_together_remove_with_unique_together`.
- Docs: `docs/ref/migration-operations.txt` (`AlterUniqueTogether`) — no behavior change needed.

## Ruled out
Migration state handling in `AlterUniqueTogether` is fine (existing operation tests pass). Not PostgreSQL-specific: `postgresql/introspection.py:176-210` reports both constraints accurately; same double-match occurs on any backend. Not caused by the single-field tuple form — the multi-field path works because no per-field unique exists.

## Conclusion
Bug is in `_delete_composed_index`'s uniqueness assertion: it must ignore the primary-key constraint and the field's own `unique=True` constraint.
