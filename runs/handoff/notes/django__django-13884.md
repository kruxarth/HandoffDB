# Handoff: `set_language` unquotes referer URL

**Issue:** POST to `django.views.i18n.set_language` with `HTTP_REFERER='/someurl/?paramter=some%20%26%20thing'` redirects to `...some%20&%20thing`, because the view unquotes the whole referer URL.

**Files/lines that matter:**
- `django/views/i18n.py:5` imports `unquote`.
- `django/views/i18n.py:31-49` handles `next`/referer selection, validation, and redirect. The bug is `django/views/i18n.py:42`: `next_url = unquote(next_url)`, which decodes reserved `%26` into `&` and changes query semantics. Remove this unquote and the import; keep `url_has_allowed_host_and_scheme` validation at lines 43-48.
- `django/urls/base.py:158-178` (`translate_url`) preserves `parsed.query` with `urlunsplit`; ruled out as the culprit.
- `tests/view_tests/tests/test_i18n.py`, `SetLanguageTests`: existing referer coverage at lines 75-86. Add regression test with `HTTP_REFERER='/someurl/?paramter=some%20%26%20thing'`, asserting `response.url` is unchanged.
- `tests/view_tests/urls.py:68` defines the `with_parameter` route if testing through i18n patterns.
- Docs: `docs/ref/views.txt`, `set_language` section.

**Conclusion:** The referer must not be unquoted; decoding reserved characters corrupts the redirect URL. Remove `unquote()` from `set_language` and add the regression test.
