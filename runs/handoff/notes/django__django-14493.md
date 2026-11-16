# Handoff: `ManifestStaticFilesStorage` crash with `max_post_process_passes = 0`

**Issue:** A subclass of `ManifestStaticFilesStorage` with `max_post_process_passes = 0` crashes during `collectstatic` with `UnboundLocalError: local variable 'substitutions' referenced before assignment` at `django/contrib/staticfiles/storage.py:251`.

**Relevant code:** In `django/contrib/staticfiles/storage.py`, `HashedFilesMixin.max_post_process_passes = 5` is at line 46. The post-processing logic around lines 246-257 reads `substitutions` at line 251, but it is only assigned inside the loop at line 264: `for i in range(self.max_post_process_passes):`. With `0`, the loop body never runs, leaving `substitutions` unbound. `ManifestStaticFilesStorage.post_process()` at line 403 only delegates via `super()`, so it is not the origin. `stored_name()` at line 381 uses `max_post_process_passes + 1` and is a separate path, not involved here.

**Tests:** Add regression coverage in `tests/staticfiles_tests/test_storage.py`, near `TestHashedFiles` (line 27) and/or `TestCollectionManifestStorage` (line 333). Existing post-processing tests at lines 220-248 and failure test at lines 288-301 are useful models.

**Docs:** Check `docs/ref/contrib/staticfiles.txt` for `ManifestStaticFilesStorage` / `collectstatic`; `docs/howto/static-files/deployment.txt` is also related.

**Ruled out:** `collectstatic` command dispatch, the dry-run path, `ManifestStaticFilesStorage.post_process()` delegation at line 403, and the `stored_name()` hashing loop at line 381.

**Conclusion:** Fix `HashedFilesMixin` by initializing `substitutions = False` before the `range(self.max_post_process_passes)` loop, or otherwise avoiding an unbound read when the pass count is zero. Add a test with `max_post_process_passes = 0`.
