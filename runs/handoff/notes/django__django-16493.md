# Handoff: callable `FileField` storage returning `default_storage`

**Issue:** `FileField(storage=get_storage)` where `get_storage` can return `default_storage` deconstructs inconsistently, so `makemigrations` randomly includes/omits `storage=...`. The deconstruct check inspects the evaluated `self.storage`, not the original callable.

**Key code:**
- `django/db/models/fields/files.py:235-253` — `FileField.__init__`: sets `self.storage = storage or default_storage`; if callable, saves `self._storage_callable` at line 243 then evaluates it into `self.storage` at line 244.
- `django/db/models/fields/files.py:293-299` — `FileField.deconstruct`: line 298 checks `self.storage is not default_storage`. When the callable returned `default_storage`, this is false and the `storage` kwarg is omitted. Line 299 only uses `_storage_callable` after that check passes.

**Tests/docs:**
- `tests/file_storage/tests.py:95-106` — storage deconstruction tests.
- `tests/file_storage/tests.py:986-999` — `FileField` callable-storage tests.
- `tests/file_storage/models.py:24-27` — `callable_storage` helper; related `Storage` model fields nearby.
- Docs: `docs/ref/models/fields.txt` (`FileField.storage`), `docs/howto/custom-file-storage.txt`, `docs/topics/migrations.txt`.

**Ruled out:** base `Field.deconstruct` (`django/db/models/fields/__init__.py:515`), `ImageField.deconstruct` (`django/db/models/fields/files.py:430-438`), and storage-backend deconstruct methods in `django/core/files/storage/filesystem.py` / `memory.py`. No relevant tests in `tests/model_fields/test_filefield.py` or `tests/migrations`.

**Conclusion:** Fix the condition in `FileField.deconstruct` to account for `_storage_callable`, e.g. include `storage` when `hasattr(self, "_storage_callable") or self.storage is not default_storage`. Add a regression test for a callable returning `default_storage` (including mixed return values) and verify explicit non-callable `default_storage` remains omitted.
