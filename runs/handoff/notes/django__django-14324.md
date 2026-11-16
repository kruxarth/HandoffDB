# Handoff: self-referential M2M `related_name` regression

## Issue
Migration autodetector emits `related_name='field_3_rel_+'` for `ManyToManyField('self')` instead of the expected hidden name `'_mymodel2_field_3_+'`. Regression from `aa4acc164d1247c0de515c959f7b09648b57dc42` (#29899).

## Where the code matters
- `django/db/models/fields/related.py:1600-1620` — `ManyToManyField.contribute_to_class` computes the auto `related_name`. Line ~1611 assigns `"%s_rel_+" % name`; line ~1617 assigns the hidden `'_%s_%s_%s_+'` form. The issue is these two branches producing different results for the same symmetrical self-referential field.
- `django/db/models/fields/related.py:1471-1525` — `ManyToManyField.deconstruct()` writes the resolved `related_name` into kwargs, so whatever `contribute_to_class` computed is baked into migration state.
- `django/db/models/fields/related.py:289-320` — `default_related_name` `%`-formatting in `contribute_to_class`.
- `django/db/migrations/autodetector.py:49-101` (`deep_deconstruct`, `only_relation_agnostic_fields`) and `:820-840` — comparison of deconstructed fields, where the `related_name` mismatch surfaces.
- `django/db/migrations/state.py:300-560` — `StateApps` / `ModelState.from_model` clone fields after `contribute_to_class` has run.

## Tests/docs
- `tests/migrations/test_autodetector.py` (M2M models ~257-273; rename m2m through ~1077) — add regression test here.
- `tests/migrations/test_state.py:1409-1455` — existing `test_direct_m2m_self`.
- `tests/model_meta/tests.py:230-290`, `tests/model_meta/results.py:324-411` — assert `*_rel_+` names; will need review.
- `tests/schema/fields.py:42` mirrors the `_rel_+` pattern.
- Docs: `docs/releases/4.0.txt:425` (autodetector uses model states), `docs/releases/1.7.1.txt:62`.

## Ruled out
`grep related_name` over `django/db/migrations/autodetector.py` and `state.py` returns nothing — no explicit handling; the value flows through `deconstruct()`.

## Conclusion
Fix likely belongs in `related.py` around lines 1600-1620 (branch ordering for symmetrical self-referential fields), not in the autodetector. Repository has a single `snapshot` commit, so the regression commit could not be inspected.
