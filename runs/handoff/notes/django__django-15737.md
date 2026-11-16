# Handoff: Avoid unnecessary cache clear in `_prepare_related_fields_for_save`

## Issue
When a child is saved with an unsaved-but-then-saved parent, `Model._prepare_related_fields_for_save()` syncs `parent_id` from the parent's pk. The assignment goes through `ForeignKeyDeferredAttribute.__set__`, which deletes the cached parent instance because `parent_id` changed from `None` to the pk. A later `child.parent` triggers an unwanted SELECT. Ticket asks to preserve the cache in this narrow case.

## Key code
- `django/db/models/base.py:1074-1126` — `_prepare_related_fields_for_save()`; line **1105** is `setattr(self, field.attname, obj.pk)`, the line to change. Called from `save()` (line 787) and `bulk_create()` (`django/db/models/query.py:682, 863`).
- `django/db/models/fields/related_descriptors.py:75-81` — `ForeignKeyDeferredAttribute.__set__`: clears the cache when `attname` changes.
- `django/db/models/fields/related_descriptors.py:221-298` — `ForwardManyToOneDescriptor.__set__`: sets `attname` values via `related_fields` and re-sets the cached instance (line ~294). This is why the suggested `setattr(self, field.name, obj)` avoids the clear.

## Tests / docs
- `tests/many_to_one/tests.py:580` (`test_fk_assignment_and_related_object_cache`), `:657` (`test_save_nullable_fk_after_parent`), `:665` (with `to_field`), `:674` (non-numeric pk), `:740` (`test_relation_unsaved`), `:834` (`test_cached_relation_invalidated_on_save`).
- `tests/one_to_one/tests.py:296`, `:329` (`test_save_nullable_o2o_after_parent`), `:452`.
- Models: `tests/many_to_one/models.py:70-97`.
- Docs: `docs/releases/4.2.txt` (Cache section, line ~98) for a release note.

## Ruled out / caveats
- Not bulk_create-specific; `save()` shows the same behavior.
- The unsaved-related-object guard (`base.py:1118-1126`) must still fire; `field.name` assignment raises the same `ValueError` via the descriptor.
- Direct `child.parent_id = ...` assignments must still invalidate the cache (`test_cached_relation_invalidated_on_save`), so do not weaken `ForeignKeyDeferredAttribute`.

## Conclusion
Replace line 1105 with `setattr(self, field.name, obj)`; this sets the FK attname and re-caches the related instance. The change was untested in the ticket and unverified in this session — add a regression test asserting zero queries after `child.parent` following `parent.save(); child.save()`, plus a release note.
