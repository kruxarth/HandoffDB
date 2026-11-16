## Handoff: sitemaps `get_latest_lastmod` ValueError on empty items

**Issue:** When a sitemap yields no items (`items()` returns empty) but defines a *callable* `lastmod`, `get_latest_lastmod()` calls `max()` on an empty list and raises `ValueError: max() arg is an empty sequence`. This surfaces at `/sitemap.xml` via `django/contrib/sitemaps/views.py:76` (`site_lastmod = site.get_latest_lastmod()`), 500-ing the sitemap index.

**Relevant code:**
- `django/contrib/sitemaps/__init__.py`, `get_latest_lastmod()` at **lines 165–172**. Line 168 checks `callable(self.lastmod)`; line 170 does `max([self.lastmod(item) for item in self.items()])`; line 171 catches only `TypeError`. That narrow except is the bug — an empty `items()` produces `ValueError`, which escapes.
- `django/contrib/sitemaps/__init__.py` **lines 185–192** show the parallel in-loop `lastmod` accumulation in `_urls`; it guards with `all_items_lastmod`, so it does not raise. Useful for confirming intended semantics (return `None` when no latest lastmod is determinable).
- Non-callable `lastmod` path returns `self.lastmod` directly and is unaffected.

**Fix:** Change line 171 to `except (TypeError, ValueError):` so empty item sequences (and non-comparable lastmods) return `None`.

**Tests:** `tests/sitemaps_tests/test_http.py` — `GetLatestLastmodTests` (covers callable/non-callable `lastmod`, `TypeError`, and no-`lastmod` cases). Add a case with a callable `lastmod` and empty `items()`.

**Docs:** `docs/ref/contrib/sitemaps.txt` — `lastmod` / `get_latest_lastmod` descriptions; note behavior with no items.

**Ruled out:** The `_urls` loop path (lines 185–192) already handles empty/None correctly; no change needed there. The `views.py` caller is correct and needs no guard.

**Conclusion:** Single-line fix in `get_latest_lastmod()` catching `ValueError` alongside `TypeError`.
