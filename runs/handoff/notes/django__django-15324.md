# Handoff note: null byte in upload extension crashes tempfile creation

## Issue
Uploading a file whose filename contains a raw null byte after the `.` (e.g. `bogus.txt\x00!`) causes `TemporaryUploadedFile.__init__` to pass the null-containing suffix to `tempfile.NamedTemporaryFile`, raising `ValueError: embedded null byte` → HTTP 500 during multipart parsing.

## Key code
- `django/core/files/uploadedfile.py:62-65` — `TemporaryUploadedFile.__init__` splits the name with `os.path.splitext(name)` and builds `suffix='.upload' + ext` for `NamedTemporaryFile`. This is the crash site.
- `django/core/files/uploadedfile.py:41-53` — `UploadedFile._set_name` calls `validate_file_name`, but this only strips path components/length; it does **not** reject null bytes.
- `django/core/files/utils.py:7-24` — `validate_file_name`; candidate place for a null-byte check, though it is also used by storage/FileField where rejection semantics may differ.
- `django/http/multipartparser.py:212-216, 307-328` — `MultiPartParser.sanitize_file_name` only strips separators and `.`/`..`; does not strip nulls.
- `django/core/files/uploadhandler.py:147` — constructs `TemporaryUploadedFile` (only when file exceeds `FILE_UPLOAD_MAX_MEMORY_SIZE`; smaller files use `InMemoryUploadedFile`, which is unaffected).

## Tests/docs
- `tests/files/tests.py:248-260` — `TemporaryUploadedFileTests.test_extension_kept` asserts the `.upload.txt` suffix is preserved; any fix must keep this passing.
- `tests/file_uploads/tests.py:63, 730-746` — filename validation and `sanitize_file_name` tests.
- Docs: no existing mention of null-byte uploads; `docs/releases/2.0.txt:334` covers nulls in model input only.

## Ruled out
`InMemoryUploadedFile` (small uploads never touch tempfile), path-traversal checks (irrelevant here), and `NamedTemporaryFile`/Windows `temp.py` (nulls fail on all platforms at `mkstemp`).

## Conclusion
Fix belongs in `TemporaryUploadedFile` (or `sanitize_file_name`) by stripping/sanitizing null bytes from the derived extension before passing it to `NamedTemporaryFile`, preserving the extension-kept behaviour.
