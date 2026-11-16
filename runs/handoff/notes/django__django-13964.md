## Handoff note

**Issue:** Assigning an unsaved related object with a non-auto, non-numeric PK (e.g. `Product(sku=CharField(primary_key=True))`) to a child, then setting/saving the parent PK, leaves the child FK attname as `""`. The child saves with `product_id=""`, causing deferred FK violation/data loss.

**Relevant code:**
- `django/db/models/base.py:911` `_prepare_related_fields_for_save()`, called from `save()` at `:682`. It only rejects related objects whose `obj.pk is None`; an empty-string PK passes, and the stale FK attname is not refreshed.
- `django/db/models/fields/related_descriptors.py`: forward descriptor assignment caches the FK value when the relation is set. `get_forward_related_filter()` at `:408` was inspected but is not the root cause.
- `django/db/models/fields/related.py:330` `get_forward_related_filter()`, `:950` `get_attname()`, `:965-976` `get_db_prep_save()`/`get_prep_value()` were reviewed; PK preparation is not the failure point.

**Tests/docs:**
- `tests/many_to_one/tests.py:518-528` covers unsaved related-object save errors; `:604` `test_relation_unsaved`.
- `tests/many_to_one/models.py:80` has `ToFieldChild`/`Parent` with non-auto PK patterns.
- Docs to update/check: `docs/ref/models/fields.txt` (`ForeignKey`, `primary_key`) and `docs/ref/models/instances.txt` (`save()`).

**Ruled out:** `get_forward_related_filter()`, `get_reverse_related_filter()`, `get_db_prep_save()`, and `get_prep_value()` as primary causes; auto-vs-non-auto PK handling alone does not explain it.

**Conclusion:** Fix belongs in `_prepare_related_fields_for_save()`: after confirming `obj.pk is not None`, if `getattr(self, field.attname)` is in `field.empty_values`, re-assign `setattr(self, field.name, obj)` so the FK attname is refreshed from the now-saved related object. Add a regression test with a `CharField(primary_key=True)` assigned before its PK is set.
