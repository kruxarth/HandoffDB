# Handoff Note: `edit_only` for model formsets

## Issue
Model formsets have no supported way to build an "edit only" view. Users misuse `extra=0`, but `extra` only controls the number of blank forms rendered; additional forms can still be injected via POST data or JavaScript, allowing unintended object creation. A dedicated opt-in flag is needed.

## Files and line ranges that matter
- `django/forms/models.py`
  - `BaseModelFormSet` (line 566): add a class-level `edit_only = False` alongside `model`/`unique_fields` (lines 570–573).
  - `BaseModelFormSet.save_new_objects()` (lines 814+): this is where new objects are constructed/saved. When `edit_only` is true, it must raise a validation error instead of saving (or return an empty list), preventing creation even if extra forms are posted.
  - `save_existing_objects()` (lines 788+): leave unchanged; editing existing rows must still work.
  - `modelformset_factory()` (line 872): accept and pass through `edit_only=False` to the generated formset class, following the pattern of other factory kwargs (`can_delete`, `extra`, etc.).
- Existing per-form count logic (`initial_form_count`, line 581) is unrelated and should not be touched.

## Tests
- `tests/model_formsets/tests.py`
  - Add cases near `ModelFormsetTest` (line 136), including with `extra` > 0 and with forged POST data containing extra forms, asserting no objects are created and a `ValidationError`/non-form error is raised.
  - Existing `extra=0`/`max_num` tests (lines ~387–419) document why `extra=0` is insufficient.

## Docs
- `docs/topics/forms/modelforms.txt` — document `edit_only` in the `modelformset_factory` argument list and explain it is the supported alternative to `extra=0`.

## Ruled out
`extra=0` as the mechanism: it does not prevent extra POSTed forms. No existing `edit_only` references anywhere in `django/` or `tests/`.

## Conclusion
Add an `edit_only` factory/class flag enforced in `save_new_objects()`; wire through `modelformset_factory`; cover with tests and docs.
