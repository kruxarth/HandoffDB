# Handoff: ImageField post_init signal overhead

## Issue
`ImageField.contribute_to_class()` unconditionally connects `update_dimension_fields` to `post_init`, even when neither `width_field` nor `height_field` is set. The receiver then returns immediately, so it is a no-op — but signal dispatch still costs 30–40% of model init time for affected models.

## Code that matters
- `django/db/models/fields/files.py:390` — `ImageField` class.
- `django/db/models/fields/files.py:~440-445` — `contribute_to_class()`; line 445 is the unconditional `signals.post_init.connect(self.update_dimension_fields, sender=cls)`.
- `django/db/models/fields/files.py:451-502` — `update_dimension_fields()`; early-returns with no width/height fields, otherwise sets them at 499-502.
- `django/db/models/fields/files.py:359-379` — `ImageFileDescriptor.__set__`; calls `update_dimension_fields(..., force=True)` on assignment. The comment at 369-375 documents that `post_init` exists to cover the `Model.__init__()` path (bug #11084). Do not remove this descriptor logic.

## Conclusion / fix
Guard the connection in `contribute_to_class()` with `if self.width_field or self.height_field:`. Behaviour is identical (the receiver was a no-op without them) and the dispatch overhead disappears. The handler must still be registered when dimension fields are declared, since it populates them after DB fetch.

## Tests
- `tests/model_fields/test_imagefield.py` (dimension assertions around lines 98-103)
- `tests/model_fields/models.py`
- `tests/signals/tests.py`
- `tests/invalid_models_tests/test_models.py`
- `tests/model_forms/models.py`
- `tests/field_deconstruction/tests.py`

## Docs
`docs/ref/signals.txt:94-120` (`post_init`).

## Ruled out
`django/forms/fields.py:692` (`forms.ImageField`) is unrelated. GIS `_post_init` occurrences are unrelated. Removing the signal unconditionally is wrong; only the no-field case should skip it.
