# Handoff: prefetch_related() ignored by QuerySet.iterator()

## Issue
`QuerySet.iterator()` silently drops prior `prefetch_related()` lookups. The docs claim "these two optimizations do not make sense together," but chunked iteration could prefetch per chunk. Django version is 4.1 alpha (`django/__init__.py`).

## Key code (`django/db/models/query.py`)
- `_iterator` (line 358) and `iterator` (lines 361–368): delegates to `_iterable_class`; never consults `_prefetch_related_lookups`.
- `_prefetch_related_objects` (lines 922–925): only works after `_result_cache` is filled, and sets `_prefetch_done`.
- `_prefetch_related_lookups` initialized at line 186; propagated on clone at lines 938 and 1445.
- `_fetch_all` (lines 1454–1455): the only place prefetch is triggered, so the iterator path bypasses it entirely.
- `prefetch_related_objects` (from line 1773) accepts a list of instances, so it is reusable per chunk.
- `RawQuerySet.iterator` (line 1620) is a separate, unrelated implementation.

## Tests
- `tests/queries/test_iterator.py` — chunk-size tests; no prefetch coverage yet. Add a test here asserting query count with `.prefetch_related(...).iterator(chunk_size=N)`.
- `tests/prefetch_related/tests.py` — `PrefetchRelatedTests` (line 45); `test_in_bulk` (~line 1246) documents that in_bulk works because it does *not* use `.iterator()`.

## Docs
- `docs/ref/models/querysets.txt` line 1218 (note that prefetch is ignored with `iterator()`) and lines 2341–2358 (`iterator()` section) must be updated if support is added.

## Ruled out
`RawQuerySet.iterator`, `in_bulk`, and parallel-iterator tests (`tests/queries/tests.py:1775`) are unrelated.

## Conclusion
No fix applied. Root cause: `iterator()` never invokes `_prefetch_related_objects`; the fix requires chunking `_iterable_class` output and calling `prefetch_related_objects(chunk, *self._prefetch_related_lookups)` per batch.
