# Handoff: `Apps.clear_cache()` doesn't clear `get_swappable_settings_name` cache

## Issue
`Apps.clear_cache()` claims to "Clear all internal caches, for methods that alter the app registry," but the `@functools.cache`-decorated `get_swappable_settings_name` cache survives. django-stubs relies on `clear_cache()` to reset registry state between mypy runs and is bitten by stale swappable-model lookups.

## Relevant code
- `django/apps/registry.py:283-294` — `get_swappable_settings_name`, decorated with `@functools.cache` (performance-critical for migrations; assumes swappable settings don't change after settings load).
- `django/apps/registry.py:370-379` — `clear_cache`; currently only calls `self.get_models.cache_clear()` (line 378). This is the fix site: add `self.get_swappable_settings_name.cache_clear()`.
- `django/apps/registry.py:168-169` — the other cached method, `get_models`, already handled at line 378.

## Tests / docs
- `tests/apps/tests.py` (`AppsTests`, `ClearCacheTests` region) — add/extend a test asserting the swappable-name cache is cleared (e.g. monkeypatch registry to return a value, call `clear_cache()`, confirm re-evaluation).
- `docs/ref/applications.txt` — documents `clear_cache()` semantics; verify wording still accurate after fix.
- `django/test/utils.py:772-778` (`isolate_lru_cache`) and `django/test/signals.py` clear caches individually on setting changes — useful precedent, but not a substitute for fixing `clear_cache`.

## Ruled out
Other `functools.cache`/`lru_cache` uses (`django/conf/urls/i18n.py:23`, `django/core/management/color.py:99`, `django/forms/renderers.py:13`, etc.) are unrelated to the app registry and correctly left alone.

## Conclusion
Confirmed bug. The one-line addition in `clear_cache` is the correct, minimal fix; no behavioral change beyond cache invalidation since swappable settings are re-read on demand.
