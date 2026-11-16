# Handoff: delete signal `origin`

**Issue:** `pre_delete`/`post_delete` receivers cannot tell what initiated a deletion — a `Model.delete()` call (which instance) or a `QuerySet.delete()` (which queryset, hence which related instances cascaded).

**Key files / line ranges**
- `django/db/models/deletion.py`: `Collector.delete()` at line 381 is where both signals fire — `pre_delete` send at 403–406, `post_delete` send at 437. `Collector.collect()` (lines ~250–275) recurses into related/parent objects; it already carries `source`/`source_attr` and is the natural place to thread an `origin` argument through cascades. Signal-listener fast path at 160–161.
- `django/db/models/base.py:983` `Model.delete()` — should pass `origin=self`.
- `django/db/models/query.py:734` `QuerySet.delete()` — should pass `origin=self` (the queryset).
- `django/db/models/signals.py:43-44` — the signal definitions; no change needed since signals accept arbitrary kwargs, but the new kwarg must be documented.

**Tests:** `tests/signals/tests.py` (`test_delete_signals`, ~line 117, receivers at 121–168; also ~206–217), `tests/delete/tests.py` (`test_only_referenced_fields_selected` ~line 597, and cascade tests), plus `tests/multiple_database/tests.py` and `tests/delete_regress/tests.py` which connect delete receivers.

**Docs:** `docs/ref/signals.txt` (`pre_delete`/`post_delete` argument tables) and `docs/topics/signals.txt`; release notes.

**Ruled out:** No change to `ModelSignal`/`signals.py` dispatch, and no new signal — the existing signals just need an extra kwarg. `Collector.collect`'s existing `source`/`source_attr` are for dependency ordering, not a substitute for `origin`.

**Conclusion:** Add `origin` to `Collector.collect()`/`Collector.delete()` and forward it as a signal kwarg, defaulting to the initiating instance (from `Model.delete`) or the queryset (from `QuerySet.delete`); cascaded objects inherit the originating object. Not yet implemented in this session.
