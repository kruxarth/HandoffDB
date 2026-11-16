**Handoff: enable cached template loader in development**

**Issue:** Make Django use `django.template.loaders.cached.Loader` by default even when `DEBUG=True`, relying on template autoreload to reset caches. Users can still opt out by specifying `loaders`.

**Key code:** `django/template/engine.py:37-43` in `Engine.__init__` builds default loaders. Lines 41-42 currently wrap them in `cached.Loader` only when `not debug`. Remove that `debug` condition so the cached wrapper is always used for defaults; the explicit `loaders` branch at line 43 must remain unchanged. `django/template/backends/django.py:22` defaults engine `debug` from `settings.DEBUG`, so this affects normal project setup. `django/template/loaders/cached.py:30-60` already handles debug-mode missing-template exceptions correctly. `django/template/autoreload.py:33-38` calls `reset()` on every `engine.template_loaders` entry, and `:41-53` watches template dirs, so cached templates reload in development.

**Tests:** Update `tests/template_backends/test_django.py` around `test_non_debug_default_template_loaders` / `test_debug_default_template_loaders` (~lines 180-200): both should expect the cached wrapper. Check `tests/template_tests/test_engine.py:18-20` (repr expectation), `:107` (debug engine), and `test_cached_loader_priority` from `:123`. Autoreload/reset behavior is covered in `tests/template_tests/test_autoreloader.py:27-28,79-82,139-142`. Cached-loader behavior also appears in `tests/template_tests/test_loaders.py`, `test_extends.py`, and `syntax_tests/test_include.py`.

**Docs:** `docs/ref/templates/api.txt` (cached loader/loaders) and `docs/ref/settings.txt` (`TEMPLATES` `OPTIONS.loaders`).

**Ruled out:** Missing autoreload reset logic; cached-loader debug exception handling; backend debug defaulting; any `global_settings` loader override.

**Conclusion:** Change `engine.py:41-42` to always wrap default loaders in `cached.Loader`; autoreload already invalidates caches.
