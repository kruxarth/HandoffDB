# Handoff: CSRF 403 masks file-upload storage errors

## Issue
When `FILE_UPLOAD_TEMP_DIR`/`MEDIA_ROOT` is missing or unwritable, uploading a file larger than `FILE_UPLOAD_MAX_MEMORY_SIZE` returns "Forbidden (403) CSRF verification failed… CSRF token missing or incorrect." The real cause is a filesystem/`OSError` raised while writing the temporary upload file; it gets swallowed and misreported as a CSRF failure.

## Root cause and files
- `django/middleware/csrf.py:325` (`_check_token`) and `:433` (`process_view`): reading `request.POST` is wrapped in `except OSError`, which catches every `OSError`, including upload-storage failures, then rejects with `REASON_CSRF_TOKEN_MISSING` (`:32`). This is the bug: only client-disconnect errors should be tolerated.
- `django/http/request.py:291-306` (`body`), `:308-310` (`_mark_post_parse_error`), `:312-340` (`_load_post_and_files`): only `MultiPartParserError` is caught here; raw read errors become `UnreadablePostError` (`:29`, a subclass of `OSError`, raised at `:304`, `:359`, `:366`). Storage errors propagate out of here as plain `OSError`.
- `django/core/files/uploadhandler.py:138-165` (`TemporaryFileUploadHandler`): `new_file` creates the temp file, `receive_data_chunk` writes; only `upload_interrupted` (`:163`) catches `FileNotFoundError`.
- `django/http/multipartparser.py:~230-300`: drives the handlers; no `OSError` handling.

## Tests / docs
- `tests/csrf_tests/tests.py:702` `test_post_data_read_failure` raises a bare `OSError` from `_load_post_and_files` and asserts it is ignored — must be updated to raise `UnreadablePostError` to keep the intended behavior.
- `tests/requests/tests.py:504-560` covers `UnreadablePostError` wrapping.
- Related docs: `docs/ref/request-response.txt` (`UnreadablePostError`, `HttpRequest.POST`), `docs/ref/settings.txt` (`FILE_UPLOAD_TEMP_DIR`).

## Ruled out
Multipart parsing, the upload handlers' own error handling, and `request.body` are not at fault; `TemporaryFileUploadHandler.upload_interrupted` already tolerates a vanished temp file.

## Conclusion
Narrow the `except OSError` in `csrf.py` to `except UnreadablePostError`, letting genuine storage/filesystem errors surface instead of producing a misleading 403 CSRF failure. Repo is Django 4.0.0 alpha.
