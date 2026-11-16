# Handoff: Model instance with conflicting args and kwargs

## Issue
`Model.__init__` accepts a positional value and a keyword value for the same field without raising `TypeError`. Expected: `TypeError: __init__() got multiple values for argument 'headline'`. Repro uses `tests.basic.models.Article` with `(None, 'args based headline', headline='kwargs based headline', pub_date=...)`.

## Key code
- `django/db/models/base.py:406-470` — `Model.__init__`. This is the only relevant code path.
  - `django/db/models/base.py:424-426` — arity check (`IndexError` if too many positional args).
  - `django/db/models/base.py:428-445` — the branch split on `if not kwargs:`. When kwargs are present, positional args and kwargs are applied in separate passes, so a duplicate field is silently overwritten by kwargs instead of detected. The fix belongs here: track fields already consumed from `args` and raise `TypeError` with Python's message when the same field also appears in `kwargs`.

## Tests
- `tests/basic/tests.py:20` — `ModelInstanceCreationTests`.
- `tests/basic/tests.py:36-79` — existing positional/kwargs/mixed tests; the new regression test fits beside `test_can_mix_and_match_position_and_kwargs` (line 64).
- `tests/basic/models.py:11-19` — `Article` (`headline`, `pub_date`); no custom `__init__`, so the bug is purely in `Model.__init__`.

## Docs
- `docs/ref/models/instances.txt` (model instantiation section) describes positional/kwargs usage and should note the `TypeError`.

## Ruled out
- Model/field definitions in `tests/basic/models.py` — no custom `__init__` or metaclass involved.
- Existing duplicate-argument handling: `grep -rn "got multiple values for argument" django tests` returns nothing, confirming no prior detection.
- `django/db/models/base.py:176` (`parent._meta.fields`) and `:1249` are unrelated (inheritance/field iteration), not initialization.

## Conclusion
Genuine bug in `Model.__init__` (`base.py:406-470`): duplicate field specification via args+kwargs is not detected. Fix there, add the regression test in `tests/basic/tests.py`, and update `docs/ref/models/instances.txt`.
