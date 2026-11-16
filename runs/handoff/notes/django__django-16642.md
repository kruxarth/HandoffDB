# Handoff: FileResponse MIME guessing for `.Z` / `.br`

**Issue** — `FileResponse(open('test.html.Z','rb'))` and `FileResponse(open('test.html.br','rb'))` send `Content-Type: text/html`, because stdlib `mimetypes.guess_type()` strips the compression suffix and reports the *inner* type plus a separate encoding.

**Code that matters**
- `django/http/response.py:4` — `import mimetypes`.
- `django/http/response.py:548-561` — `FileResponse.__init__`; tracks `_no_explicit_content_type`.
- `django/http/response.py:575-615` — `set_headers()`; **line 608** `content_type, encoding = mimetypes.guess_type(filename)` is the bug site. `encoding` is discarded, so `.Z`/`.br`/`.gz`/`.bz2` responses keep the inner type and emit no `Content-Encoding`.
- `django/views/static.py:57-62` — `serve()` uses the same guess but *does* set `Content-Encoding` from `encoding`; it still sends `text/html` as content type.

**Verified** — `mimetypes.guess_type` returns `('text/html','compress')` for `.Z`, `('text/html','br')` for `.br`, `('text/html','gzip')` for `.gz`, `('text/html','bzip2')` for `.bz2`. The stdlib is behaving as documented.

**Ruled out** — Python stdlib `mimetypes` bug. Unrelated call sites: `django/test/client.py:342`, `django/core/mail/message.py:324`, `django/core/management/templates.py:343`. `tests/test_client_regress/tests.py:1227` only asserts multipart `encode_file` output (`application/x-compress`) and is unrelated.

**Tests/docs to update** — `tests/httpwrappers/tests.py` (FileResponse tests), `tests/view_tests/tests/test_static.py` (`serve`), `docs/ref/request-response.txt` (`FileResponse`). Add cases for `.html.Z` and `.html.br`.

**Conclusion** — Fix belongs in `FileResponse.set_headers` around `response.py:608`: decide how the encoding suffix is reflected (set `Content-Encoding`, and/or derive `application/x-compress` / `application/x-brotli`), aligned with `static.serve`. No fix applied yet.
