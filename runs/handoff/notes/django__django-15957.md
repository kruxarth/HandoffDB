# Handoff: `Prefetch()` with sliced querysets

**Issue:** `Prefetch("post_set", queryset=Post.objects.all()[:3], to_attr="example_posts")` raises `AssertionError: Cannot filter a query once a slice has been taken.` The prefetch machinery combines the user-supplied queryset with a filter over the parent instances, which is illegal once the queryset is sliced.

**Key files/lines:**
- `django/db/models/query.py:2142` — `Prefetch.__init__`; rejects raw/values/values_list (2148-2157) but has no slice guard.
- `django/db/models/query.py:1440-1442` — `_filter_or_exclude` raises the `TypeError`/assertion path for sliced querysets.
- `django/db/models/fields/related_descriptors.py:124` (reverse FK), `:711` (reverse FK manager), `:1047` (M2M) — `get_prefetch_queryset` implementations that apply `filter(...)`/`extra(...)` to the supplied queryset.
- `django/contrib/contenttypes/fields.py:174` and `:623` — `GenericForeignKey` prefetch paths; `:623` also filters.

**Tests/docs:**
- `tests/prefetch_related/tests.py` — existing `Prefetch` usage around 295+, 539+, 630+; add slice coverage here.
- `tests/prefetch_related/test_prefetch_related_objects.py`.
- `tests/queries/tests.py:2822` — existing assertion for the slice error message.
- `docs/ref/models/querysets.txt:1089+` — `prefetch_related` docs; slicing limitation is undocumented.
- `docs/releases/4.2.txt`.

**Ruled out:** raw/values/values_list are already blocked in `Prefetch.__init__`. Window-function machinery (`RowNumber` in `django/db/models/functions/window.py`, `qualify` handling in `django/db/models/sql/compiler.py:590-656`) was explored as a possible efficient per-parent limit but no change was made.

**Conclusion:** Root cause is that every `get_prefetch_queryset` filters the supplied queryset, impossible once sliced. A fix needs either special handling of sliced querysets in `Prefetch`/`get_prefetch_queryset`, or per-instance limiting via window functions. No fix applied; tree left clean at `3501e31`.
