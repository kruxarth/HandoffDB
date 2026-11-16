# Handoff: AppAdmin for customizing app listing in admin index

## Issue
Add an `AppAdmin` options class so the admin index/app listing can be customized per app (name, description, CSS classes, ordering, and explicit model ordering) via `admin.site.register(FooAppAdmin)`, rather than only global alphabetical sorting.

## Where the behavior lives
- `django/contrib/admin/sites.py`
  - `get_app_list()` at **533–547**: currently sorts apps alphabetically by `name` and models by `name`. This is the core hook to override.
  - `_build_app_dict()` at **~440–531**: builds each app dict (`app_label`, `app_url`, `has_module_perms`, `models`); no per-app options are consulted.
  - `index()` at **549–568** and `app_index()` at **570–590** both call `get_app_list()`.
  - `each_context()` at **337** supplies `available_apps` from `get_app_list()`.
  - `register()`/`unregister()` and `_registry` (~**80–130**): only `ModelAdmin` instances are stored; there is no app-level registration path.
- `django/contrib/admin/options.py`: `ModelAdmin` hierarchy (~**1–60+**), natural home for an `AppAdmin` options base.
- `django/contrib/admin/__init__.py`: public exports (`__all__`) must add `AppAdmin`.
- `django/contrib/admin/templates/admin/app_list.html`: consumes `app.name`, `app.app_label`, `app.models`; needs to honor style/description if added.

## Tests
- `tests/admin_views/test_adminsite.py` (`SiteEachContextTest`) — asserts `available_apps` structure.
- `tests/admin_views/tests.py`: `test_app_index_context` (~**1349**), `test_app_list_permissions` (~**2972**), plus app_list URL tests (~**1242–1255**).
- `tests/admin_registration/tests.py`: registration semantics.

## Docs
- `docs/ref/contrib/admin/index.txt`: `AdminSite` attributes (~**2775**), methods/each_context (~**2861–2960**), templates (~**2679**).
- `docs/releases/4.1.txt` admin section (~**51–66**) for the changelog entry.

## Ruled out
- No existing `AppAdmin`, `app_order`, or app-ordering hooks anywhere (`grep` clean).
- No `get_app_list` tests or release notes; behavior is purely alphabetical, so nothing to preserve beyond default ordering.
- Docs release notes contain no related precedent.

## Conclusion
Feature is unimplemented. Work centers on a new `AppAdmin` in `options.py`, registration support and `get_app_list()` ordering in `sites.py`, export in `__init__.py`, template updates, and regression tests in the files above.
