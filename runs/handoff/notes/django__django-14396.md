# Handoff: Sitemap protocol default to HTTPS

**Issue:** Change `Sitemap.protocol` default from HTTP to HTTPS with a clear deprecation timeline.

**Code that matters:**
- `django/contrib/sitemaps/__init__.py:59-61` — `protocol = None`; comment says request protocol is used.
- `django/contrib/sitemaps/__init__.py:123-125` — `get_protocol()` hard-codes fallback `'http'`.
- `django/contrib/sitemaps/__init__.py:143-155` and `:176-183` — build `<loc>` URLs from protocol.
- `django/contrib/sitemaps/views.py:36` — index view uses `req_protocol` when `site.protocol is None`, so changing the default affects index URLs too.
- `django/contrib/sitemaps/__init__.py:202-207` — `GenericSitemap.__init__` sets protocol.

**Tests/docs:**
- `tests/sitemaps_tests/base.py:10-23` — HTTP base and `base_url`.
- `tests/sitemaps_tests/test_http.py` — expected HTTP URLs; `test_https.py` covers HTTPS request detection; `test_generic.py:23-29` covers explicit `protocol='https'`.
- `docs/ref/contrib/sitemaps.txt:229-235` — documents current request/default behavior.
- `docs/releases/4.0.txt:132` — empty sitemaps section; `docs/internals/deprecation.txt` has 4.1/5.0 sections.

**Ruled out:** unrelated `protocol` references in sessions, DB fields, and `runserver`; no existing sitemap-specific deprecation warning. Existing tests do not assert a deprecation for sitemap protocol.

**Conclusion:** The change is confined to sitemap protocol default/fallback and documentation. Implement HTTPS fallback, preserve/request-scheme behavior as needed, add a `RemovedInDjango50Warning`-style deprecation path if retaining old behavior, and update HTTP/HTTPS test expectations plus release/deprecation docs.
