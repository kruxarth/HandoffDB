# Handoff: `view_on_site` redirect ignores custom admin site

## Issue
`ModelAdmin.get_view_on_site_url()` reverses `admin:view_on_site` without `current_app`, so custom admin sites fall back to the default admin site for the "View on site" redirect. Every other `reverse()` in `contrib/admin/options.py` passes `current_app=self.admin_site.name` (e.g. lines 1328, 1476, 1494, 1513, 1646); this one does not.

## Files and line ranges
- `django/contrib/admin/options.py:336-350` — `get_view_on_site_url()`. The bug is the `reverse("admin:view_on_site", ...)` at lines 344-350; add `current_app=self.admin_site.name`. Lines 340-341 (callable branch) and 337-338 (False/None branch) return early and are unaffected.
- `django/contrib/admin/options.py:1263` — caller in `changeform_view` (`view_on_site_url = self.get_view_on_site_url(obj)`).
- `django/contrib/admin/helpers.py:350` — caller in `AdminReadonlyField`; rendering only, no fix needed.

## Tests
- `tests/admin_views/tests.py:7873-7931` — `test_check` and the `view_on_site` behavior tests (button shown/hidden, callable, default URL). Extend here with a custom `AdminSite` regression test asserting the URL resolves under the custom site name.
- `tests/admin_views/tests.py:2993` — existing `reverse("admin:view_on_site", ...)`.
- `tests/admin_views/admin.py:220, 1065, 1093-1121` — `view_on_site` fixtures/callables.
- Custom admin site tests: `tests/admin_views/tests.py:1463-1864`.

## Docs
- `docs/ref/contrib/admin/index.rst` (`ModelAdmin.view_on_site`).

## Ruled out
Callable and `False` branches, `check()` validation (admin.E025), helpers rendering, and `contrib/admin/sites.py` — all behave correctly. Only the boolean/`get_absolute_url` reverse path is wrong.

## Conclusion
Add `current_app=self.admin_site.name` to the reverse at `options.py:344-350` (matches PR #15526) and add a regression test using a custom admin site.
