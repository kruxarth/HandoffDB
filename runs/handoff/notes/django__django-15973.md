# Handoff note

## Issue
`ManyToManyField(..., through="app.Model")` where the through model lives in a *different* app raises `AttributeError: 'str' object has no attribute '_meta'` at migrate time. The generated `CreateModel` for the M2M field carries no dependency on the through model's app, so the through model is still a string when schema code accesses `remote_field.through._meta`.

## Root cause (conclusion)
`django/db/migrations/autodetector.py`, `_get_dependencies_for_foreign_key` (~line 1423). For fields with a `through`, it computes the dependency from `field.remote_field.model` (the *target* app) instead of `field.remote_field.through`. This omits the cross-app dependency on the through model's app. Related autodetector code: `_prepare_field_lists` (210–232), `_generate_through_model_map` (233–248), `_generate_added_field` (1026–1046). `resolve_relation` lives in `django/db/migrations/utils.py:27`.

## Ruled out
- `django/db/migrations/state.py`: `StateApps` (597–710), `render_multiple` (651), `render` (933) — pending operations correctly empty; state simply never receives the through model.
- `django/apps/registry.py:386–432` (`lazy_model_operation`/`do_pending_operations`) — not the culprit.
- `django/db/models/fields/related.py`: `_check_relationship_model` (1478–1592) and `contribute_to_class` — checks are fine; failure is in migration state, not model definition.
- `django/db/backends/base/schema.py`: 453–461, 633–634, 707–708, 760–773 — these `through._meta` accesses are the crash site, not the cause.

## Files/tests/docs
- Fix: `django/db/migrations/autodetector.py` (~1423, through-model dependency resolution).
- Tests: `tests/migrations/test_autodetector.py` (add a cross-app through-model dependency case); `tests/migrations/test_state.py` for state rendering.
- Docs: `docs/ref/models/fields.txt` (`ManyToManyField.through`), `docs/topics/migrations/`.
