## Handoff note

**Issue:** `get_image_dimensions()` crashes when given a nonexistent path instead of returning gracefully.

**Relevant code**
- `django/core/files/images.py:33-48` — `get_image_dimensions()`. For path input, line 47 calls `open(file_or_path, 'rb')` without handling `OSError`, so a missing path raises `FileNotFoundError`.
- `django/core/files/images.py:25-30` — `ImageFile._get_image_dimensions()` opens the file before calling `get_image_dimensions()`, so this path is not the direct crash source for missing filenames.
- `django/db/models/fields/files.py:425-475` — `ImageFieldFile.update_dimension_fields()` reads `.width`/`.height`; it depends on this helper but is not where the missing-path failure originates.

**Tests**
- `tests/files/tests.py:260-330` — `DimensionClosingBug` covers file closing behavior (`test_not_closing_of_files`, `test_closing_of_filenames`) but not nonexistent paths. Add a regression test here or in a nearby image-dimensions test class.
- Other `get_image_dimensions` references are only in `tests/files/tests.py` and `django/core/files/images.py`.

**Docs:** No docs referencing `get_image_dimensions()` were found; no docs change appears necessary.

**Ruled out**
- `ImageFile.width`/`height` and `ImageField` dimension updates are downstream consumers, not the source.
- Existing tests verify closing semantics, not missing-file behavior.
- The crash is not Pillow parser failure; it happens before parsing at the `open()` call.

**Conclusion:** The missing-path crash is caused by the unguarded `open()` at `django/core/files/images.py:47`. The fix should catch `OSError` there and return `None` for nonexistent/unopenable paths, matching the function’s existing behavior for unreadable/non-image data. Add a regression test asserting `get_image_dimensions()` returns `None` for a nonexistent path rather than raising.
