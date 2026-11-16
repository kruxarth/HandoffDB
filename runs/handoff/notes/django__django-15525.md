# Handoff: loaddata natural keys on non-default DB

## Issue
`loaddata --database other` fails when a model's `natural_key()` dereferences a foreign key. The temp instance built during deserialization has `_state.db = None`, so the FK lookup routes to the default DB and raises `DoesNotExist` (or silently uses wrong-DB data).

## Root cause / files
- `django/core/serializers/base.py:325-342` — `build_instance()`. Line 339 constructs `Model(**data)` and immediately calls `.natural_key()`; line 342 then queries the correct DB via `db_manager(db)`. The instance used for `natural_key()` never gets `_state.db = db`.
- `django/db/models/fields/related_descriptors.py:121` (`get_queryset`) → `:158-168` (`get_object`): FK access passes `instance=` as a hint.
- `django/db/utils.py:235-237` (`_router_func`): only uses `instance._state.db` when truthy; `None` falls back to default. This explains why it works when rows exist in the default DB.
- `django/core/serializers/python.py:174` calls `build_instance`.

## Fix
Set `instance._state.db = db` on the temp instance before invoking `natural_key()` in `build_instance()`.

## Tests
- `tests/serializers/test_natural.py` — `natural_key_serializer_test()`; no multi-DB coverage yet. Add `databases = {"default", "other"}` and a case where the FK target exists only in `other`.
- Models: `tests/serializers/models/natural.py` (`NaturalKeyAnchor`, `FKDataNaturalKey`).
- Related: `tests/fixtures/tests.py::test_db_loading` (~line 893), `tests/fixtures/models.py` (`Person`, `Book`).

## Ruled out
- `deserialize_fk_value()` (`base.py:383-410`) already passes `using` correctly via `db_manager(using)`.
- Serializer output, `natural_key.dependencies` ordering, and DB routing configuration are not at fault.

## Docs
`docs/topics/serialization.txt` (natural keys, multi-db), `docs/ref/django-admin.txt` (`loaddata --database`).
