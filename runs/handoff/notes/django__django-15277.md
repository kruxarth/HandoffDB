## Handoff note

**Issue.** `Value('test')._resolve_output_field()` constructs `fields.CharField()` with no `max_length`, but `CharField.__init__` unconditionally appends `MaxLengthValidator(self.max_length)` — i.e. `MaxLengthValidator(None)`. The validator can never work (calling it raises `TypeError: '>' not supported between 'int' and 'NoneType'`), and its `@deconstructible` construction is pure overhead on a hot path (`annotate(x=Value('test'))`). Roughly 2µs per call.

**Mattering files/lines.**
- `django/db/models/fields/__init__.py:1010-1013` — `CharField.__init__`, the line to guard: `if self.max_length is not None:` before appending the validator.
- `django/db/models/fields/__init__.py:2323-2325` — `BinaryField.__init__` already uses exactly this guard; precedent to copy.
- `django/db/models/expressions.py:781-790` — `Value._resolve_output_field`, the caller that triggers the empty `CharField()`.
- `django/db/models/fields/__init__.py:1015-1035` — `CharField.check()`/`_check_max_length_attribute` still emits `fields.E120` for `max_length is None`, so system-check behaviour is unchanged.

**Tests/docs.** `tests/model_fields/test_charfield.py` (closest home for a `validators`/`max_length=None` assertion), `tests/expressions/tests.py` `ValueTests` (`test_resolve_output_field`, line 1831), `tests/validators/tests.py` (MaxLengthValidator semantics, unchanged), `tests/model_fields/test_binaryfield.py` (guard precedent). Docs: `docs/ref/models/fields.txt` (CharField `max_length`) and `docs/ref/checks.txt` (`fields.E120`).

**Ruled out.** Removing `@deconstructible` from `MaxLengthValidator`/`BaseValidator` (helps but not the root cause, and changes deconstruction semantics). Relying on system checks alone — the bogus validator is still created. `TextField`/`SlugField` are unaffected.

**Conclusion.** Add the `None` guard in `CharField.__init__`; existing tests pass, behaviour for real `CharField(max_length=N)` is identical.
