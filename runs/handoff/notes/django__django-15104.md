# Handoff note

**Issue:** `python manage.py test -v 2` crashes with `KeyError: 'to'` in the migration autodetector. A custom `ForeignKey` hardcodes its `to` target in `__init__()` and removes `to` from `deconstruct()` kwargs.

**Relevant code:**
- `django/db/migrations/autodetector.py:89-100` — `only_relation_agnostic_fields()`; line 99 unconditionally does `del deconstruction[2]['to']` when `field.remote_field.model` is set. A custom FK whose deconstruction lacks `'to'` triggers the `KeyError`.
- Called from `generate_renamed_models()` at `autodetector.py:476-483`, matching the traceback.
- Similar unsafe assumption at `autodetector.py:836-838` (`old_field_dec[2]['to']`) in `generate_renamed_fields()`; audit for the same failure mode.
- `deep_deconstruct()` at `autodetector.py:49-83` explains the `(path, args, kwargs)` tuple and index `[2]`.

**Tests/docs:**
- Primary regression location: `tests/migrations/test_autodetector.py`, especially `AutodetectorTests`; add a custom FK that hardcodes `to` and deletes it from `deconstruct()`.
- Related docs: `docs/topics/migrations/` and `docs/ref/migrations.txt` for autodetection/deconstruction behavior.

**Ruled out:** Test runner, database creation, and syncdb are not the cause. The crash occurs later when `migrate` invokes the autodetector. Standard FKs are unaffected because their deconstruction includes `'to'`.

**Conclusion:** Replace direct deletion with guarded handling (`deconstruction[2].pop('to', None)` or a key check) in `only_relation_agnostic_fields()`, and audit lines 836-838. Add the regression test above. Observed on Django 4.1 alpha, commit `8d4e6a4`.
