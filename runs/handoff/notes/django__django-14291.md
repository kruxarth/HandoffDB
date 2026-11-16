## Handoff: `caches.W002` fails with tuple `STATICFILES_DIRS`

**Issue:** `check_cache_location_not_exposed()` in `django/core/checks/caches.py` (lines 22–55) assumes every `STATICFILES_DIRS` entry is a path string. At lines 29–33 it calls `pathlib.Path(staticfiles_dir)` directly. Django documents `STATICFILES_DIRS` entries as either strings or `(prefix, path)` tuples, so tuple entries raise `TypeError: expected str, bytes or os.PathLike object, not tuple`.

**Relevant code:** `django/core/checks/caches.py:22-55`, especially `:29-33`. Normalize tuple entries before constructing `pathlib.Path`, using the tuple’s path element (typically index `1`). `MEDIA_ROOT`/`STATIC_ROOT` handling at `:34-35` is unaffected.

**Tests:** `tests/check_framework/test_caches.py`. Existing coverage around lines 54 and 59–92 parametrizes settings but passes `STATICFILES_DIRS` as `[setting_path]`, so tuple entries are not exercised. Add a regression test with `STATICFILES_DIRS=[('prefix', setting_path)]` and assert no `TypeError` plus expected `caches.W002` behavior when the cache path overlaps.

**Related code/docs:** `django/contrib/staticfiles/finders.py:49-104` already handles string and tuple `STATICFILES_DIRS` entries, confirming the checker is the inconsistent component. Documentation is in `docs/ref/settings.txt` under `STATICFILES_DIRS` (prefixes optional).

**Ruled out:** The staticfiles finder is not the source of the failure; it supports tuples. The check’s `MEDIA_ROOT` and `STATIC_ROOT` branches are string-only by design. The problem is isolated to tuple normalization in `check_cache_location_not_exposed()`.

**Conclusion:** This is a real bug in `caches.W002`. Fix by extracting the path from tuple entries before calling `pathlib.Path()`, and add tuple-specific regression coverage in `tests/check_framework/test_caches.py`.
