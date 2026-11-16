# Handoff note: `bulk_update()` drops unsaved-related FK values

## Issue
Assigning an unsaved related object (`parent.child = Child()`, then saving the child) and calling `Parent.objects.bulk_update([parent], fields=["child"])` writes the stale `child_id` (NULL). `bulk_update()` reads only the FK's `attname` column, which is never refreshed after the related instance acquires a PK.

## Relevant code
- `django/db/models/query.py:534-576` — `QuerySet.bulk_update()`. Field resolution/validation at 545-549. The core defect is at **565** (`attr = getattr(obj, field.attname)`) and **572** (`update_kwargs[field.attname] = case_statement`): only `child_id` is consulted, never the cached related object.
- `django/db/models/fields/related_descriptors.py:82-260` — `ForwardManyToOneDescriptor`. `__set__` (from ~208) caches the related object but cannot copy a PK that doesn't exist yet; no back-propagation happens when the child is later saved.
- `django/db/models/base.py:705, 738+` — `Model.save()` calls `_prepare_related_fields_for_save()`, which is exactly the PK-syncing logic `bulk_update()` lacks.

## Tests / docs
- `tests/queries/test_bulk_update.py` (whole file; `Note.tag` FK defined at `tests/queries/models.py:41-44` is the natural fixture). No existing FK/unsaved-related test.
- `tests/postgres_tests/test_bulk_update.py:16-32`.
- `docs/ref/models/querysets.txt:2217-2232` (`bulk_update()` reference).

## Ruled out
- Not a `save()` regression — `_prepare_related_fields_for_save()` handles this correctly.
- Not a descriptor `__set__` bug: at assignment time the child has `pk=None`, so nothing is copyable.
- Not a batching/SQL-compilation issue; single-object reproduction fails identically.

## Conclusion
The fix belongs in `bulk_update()`: for each field where `field.is_relation` and the related object is cached with a PK set, resolve the value from the cached instance (or raise a clear `ValueError` for unsaved related objects) instead of relying on `attname`. No code change was applied; add a regression test to `tests/queries/test_bulk_update.py`.
