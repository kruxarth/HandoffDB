## Handoff note: deferred fields clobbered by nested prefetch back to parent

**Issue:** In `User.objects.only("email").prefetch_related(Prefetch("profile", queryset=Profile.objects.prefetch_related(Prefetch("user", queryset=User.objects.only("kind")))))`, accessing `user.profile.user.kind` issues an extra query and `user.profile.user.get_deferred_fields()` reports `{'kind'}` even though the inner query fetched `kind`. The inner `User.objects.only("kind")` queryset is correct (query 3 correctly selects `kind`); the fetched instance is then overwritten.

**Root cause:** In `django/db/models/fields/related_descriptors.py`, `ReverseOneToOneDescriptor.get_prefetch_queryset` (starts line 633) unconditionally does `setattr(rel_obj, self.field.name, instance)` in its loop (around lines 680-690), assigning the outer `User` instance (with `kind` deferred) to `profile.user`, clobbering the correctly nested-prefetched object. `ReverseManyToOneDescriptor.get_prefetch_queryset` (line 928) has the same pattern for the FK case (`user.profile_set.all()[0].user.kind`).

**Related code:** `django/db/models/query.py` `prefetch_related_objects` (1680) and `prefetch_one_level` (1876); `get_prefetcher`/`is_fetched` (~1830-1866) shows cached relations are skipped. `ForwardManyToOneDescriptor.get_object` (lines 290-301) uses `get_deferred_fields()` and is not at fault.

**Tests/docs:** Add regression coverage in `tests/prefetch_related/tests.py` (see `CustomPrefetchTests`, nested-prefetch tests at ~803-814, `test_filter_deferred` at 859); models in `tests/prefetch_related/models.py`; deferred behavior covered by `tests/defer/tests.py`. Docs: `docs/ref/models/querysets.txt` (`Prefetch`, `only`/`defer`).

**Ruled out:** deferred-field computation itself and the inner queryset's SQL are correct; the outer queryset is correct; the forward descriptor is correct.

**Conclusion:** Bug is the unconditional `setattr` in the reverse descriptors' `get_prefetch_queryset`, which must not overwrite an already-cached/prefetched related object.
