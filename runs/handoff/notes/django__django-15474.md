# Handoff: contenttypes 0002 backward migration ignores DB alias

## Issue
Reverse-migrating `contenttypes` to `0001` on a non-default database (`--database=other`) leaves `name` NULL. The `RunPython` reverse function `add_legacy_name` populates the legacy `name` field, but it never honors the alias of the connection being migrated.

## Files and line ranges that matter
- `django/contrib/contenttypes/migrations/0002_remove_content_type_name.py`
  - **lines 4–10**: `add_legacy_name(apps, schema_editor)` — the bug. `ContentType.objects.all()` and `ct.save()` use the default DB, not `schema_editor.connection.alias`. Must use `ContentType.objects.using(alias)` / `db_manager(alias)`.
  - **lines 31–37**: `RunPython(migrations.RunPython.noop, add_legacy_name, hints={"model_name": "contenttype"})` — reverse direction is the failing path.
- `django/contrib/auth/migrations/0011_update_proxy_permissions.py` — reference implementation: it reads `alias = schema_editor.connection.alias` and uses `ContentType.objects.db_manager(alias)`. This is the pattern to mirror.
- `django/contrib/contenttypes/migrations/0001_initial.py` — the state being rolled back to (`name` non-null, `ordering=("name",)`).

## Tests and docs
- `tests/contenttypes_tests/test_operations.py` — closest existing multidb migration test harness (`databases = {"default", "other"}`, uses `MIGRATION_MODULES`, `database="other"` around lines 11–13, 101, 111). Natural home for a regression test.
- `tests/contenttypes_tests/test_models.py:273` — `ContentTypesMultidbTests` (`databases = {"default", "other"}`).
- `tests/auth_tests/test_migrations.py` — pattern for invoking migration callables directly with a `schema_editor`.
- `docs/releases/4.1.txt` — `django.contrib.contenttypes` bugfix section (currently `* ...`) is where a release note belongs.

## Ruled out
- Not a `ContentTypeManager` cache problem (`django/contrib/contenttypes/models.py:8–130`); `_cache` is per-`self.db`.
- Not `RemoveStaleContentTypesTests` (`tests/contenttypes_tests/test_management.py`) — unrelated.
- No existing test references `add_legacy_name` or migration 0002 directly (`grep` over `tests/` returned nothing).

## Conclusion
Root cause is the missing database alias in `add_legacy_name`. Fix by deriving `alias = schema_editor.connection.alias` and routing both the queryset and `save()` through it, matching `0011_update_proxy_permissions.py`. Add a multidb reverse-migration regression test in `tests/contenttypes_tests/`.
