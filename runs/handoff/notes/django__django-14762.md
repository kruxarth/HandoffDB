# Handoff: `prefetch_related()` nulls `GenericForeignKey` ids for deleted objects

**Issue.** Calling `TaggedItem.objects.prefetch_related('content_object')` when the referenced object has been deleted sets the row's `object_id` and `content_type_id` to `None`. Lazy access (`tags[0].content_object`) correctly returns `None` but leaves both ids intact. This inconsistency is undocumented and destructive for audit-style GFK rows.

**Files that matter.**
- `django/contrib/contenttypes/fields.py`: `GenericForeignKey` (class starts ~L19); `get_prefetch_queryset()` ~L173 defines the prefetch contract (queryset, instance/object attr callables, `single`, cache name, `is_descriptor`). The `GenericRelation` manager factory ~L504-560 is unrelated.
- `django/db/models/query.py`: `prefetch_one_level()` L1867-1970 does the cache assignment and is where a missing related object ends up writing over the concrete id fields; `get_prefetcher()` L1813-1866 selects the descriptor.

**Tests/docs.** `tests/generic_relations/tests.py` (prefetch after create/add/remove/clear/set ~L497-534; cache invalidation ~L480-496) is the right home for a regression test. `tests/contenttypes_tests/test_fields.py` covers `get_prefetch_queryset` argument validation (L23-25). `tests/generic_relations/models.py` defines `TaggedItem`/`Animal`. Docs: `docs/ref/models/querysets.txt` (`prefetch_related`) and `docs/ref/contrib/contenttypes.txt`.

**Ruled out.** The lazy GFK accessor and its cache invalidation (they leave ids untouched); model field definitions; `GenericRelation` manager behavior.

**Conclusion.** The nulling happens in the prefetch cache-assignment path, not in GFK attribute access. The fix should make GFK prefetch set only the `content_object` cache to `None` while preserving `object_id`/`content_type_id`, plus a regression test in `tests/generic_relations/tests.py`; otherwise document the behavior.
