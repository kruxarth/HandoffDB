## Handoff note

**Issue:** `HashedFilesMixin.post_process()` in `django/contrib/staticfiles/storage.py` yields the same original filename multiple times because of its multi-pass post-processing loop. This inflates `collectstatic`’s “post-processed” count and causes subclasses to repeat expensive work (e.g. WhiteNoise/Brotli, S3 uploads). It also inconsistently yields some intermediate hashed names, related to but distinct from #28604.

**Key code:**
- `django/contrib/staticfiles/storage.py:203` — `HashedFilesMixin.post_process()`: the multi-pass generator responsible for duplicate yields.
- `django/contrib/staticfiles/storage.py:397` — `ManifestStaticFilesStorage.post_process()` wrapper; preserve its behavior.
- `django/contrib/staticfiles/storage.py:180-199` — URL/hash rewriting used during passes; relevant to why multiple passes occur.

**Tests:**
- `tests/staticfiles_tests/test_storage.py:179-205` — `test_post_processing`; asserts post-processed/unmodified stats.
- `tests/staticfiles_tests/test_storage.py:221` — `test_post_processing_failure`.
- `tests/staticfiles_tests/test_storage.py:377` — `test_intermediate_files`.
- `tests/staticfiles_tests/test_storage.py:31-37` — `max_post_process_passes` setup/teardown.

**Docs:** `docs/ref/contrib/staticfiles.txt` covers `collectstatic` and staticfiles storage behavior; update only if output semantics are documented.

**Ruled out:** This is not a `collectstatic` stats-counting bug or fixture issue. Duplicate yields occur even when the final hash is unchanged (`admin/css/dashboard.css`), so it is not solely an intermediate-file/#28604 problem. The generator itself is the source.

**Conclusion:** Fix `HashedFilesMixin.post_process()` so each original path is yielded at most once, after processing settles, while not yielding implementation-only intermediate names. Add a regression test asserting one yield per file and correct `collectstatic` stats.
