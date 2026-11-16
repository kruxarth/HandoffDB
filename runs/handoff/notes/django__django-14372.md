## Handoff note

**Issue:** After Django 3.2.1’s CVE-2021-31542 hardening, assigning `File(open(path, "rb"))` to a `FileField` and saving raises `SuspiciousFileOperation: File name ... includes path elements`. The regression comes from `FileField.pre_save()` passing `file.name` (often a full path) into `FieldFile.save()`.

**Key code:**
- `django/db/models/fields/files.py:298-303` — `FileField.pre_save()` calls `file.save(file.name, file.file, save=False)` with the unmodified `file.name`.
- `django/db/models/fields/files.py:309-322` — `FileField.generate_filename()` calls `validate_file_name(filename)` at line 316, which rejects any path containing directories.
- `django/db/models/fields/files.py:87` — `FieldFile.save()`; confirmed the exception originates before storage commit.
- `django/core/files/utils.py:4-12` — `validate_file_name()` currently requires `name == os.path.basename(name)`.

**Tests/docs:**
- `tests/file_storage/test_generate_filename.py:44-78` covers dangerous paths and explicitly expects `"/tmp/path"` to raise `SuspiciousFileOperation`.
- `tests/model_fields/test_filefield.py` has FileField save/assign tests but no regression for full-path `File` names.
- `tests/model_fields/test_imagefield.py:53-56` avoids the bug by passing explicit basename `name=`.
- Related docs: `docs/releases/3.2.1.txt` CVE-2021-31542 note.

**Ruled out:** `FieldFile.save()` itself and storage backends; `save_form_data()` is unrelated. Simply passing `basename` in `pre_save()` would discard valid relative upload paths.

**Conclusion:** Fix belongs in `validate_file_name()` by allowing safe relative paths (still rejecting absolute paths, `..`, `.`, empty) via an opt-in flag, and have `FileField.generate_filename()` use that mode. Add regression tests for `File(open(path, "rb"))` model save and for `validate_file_name(..., allow_relative_path=True)`.
