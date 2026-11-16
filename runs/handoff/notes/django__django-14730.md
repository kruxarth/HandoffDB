## Handoff note

**Issue:** `ManyToManyField` silently ignores a user-supplied `related_name` when the relation is symmetrical (including self-referential fields, where `symmetrical` defaults to `True`). Add a system check so developers get an explicit error instead of confusion.

**Code to change — `django/db/models/fields/related.py`:**
- L1162–1200: `ManyToManyField.__init__`. `symmetrical` defaults at L1180–1181 (`to == RECURSIVE_RELATIONSHIP_CONSTANT`), so self-referential fields are symmetrical unless overridden. `related_name` is passed into `rel_class` at L1191–1198.
- L1220–1260: `_check_unique_for_related_field` / `_check_ignored_options` — the pattern to follow. `_check_ignored_options` already emits `fields.W340`, `W341`, `W343`; the new check belongs in that method (or a sibling check method) and should fire only when `self.remote_field.symmetrical` and the user explicitly passed `related_name` (not the internal `_related_name` default).
- L1630–1635: the comment about related names on symmetrical relations being set internally — do not flag this path; it is intentional.

**Ruled out:** `_check_related_name_is_valid` (L120–131) only validates identifier syntax, not applicability. `related_descriptors.py` symmetrical logic (L827–880, L953–955) needs no change. Existing tests create symmetrical self-M2Ms without `related_name` (`tests/invalid_models_tests/test_models.py` L108, 208, 254, 441), so they are unaffected.

**Tests:** add to `tests/invalid_models_tests/test_relative_fields.py` (M2M check tests around L98–127, alongside W340/W341/W343). Related suites: `tests/many_to_many/tests.py`, `tests/model_fields/test_manytomanyfield.py`.

**Docs:** `docs/ref/checks.txt` — `fields.E330`–`E340` (L281–307) and `fields.W340`–`W344` (L308–315). Use the next free ID (`fields.W345`; `E340`/`W344` are taken), and add a release note in `docs/releases/4.0.txt` (repo is 4.0 alpha).
