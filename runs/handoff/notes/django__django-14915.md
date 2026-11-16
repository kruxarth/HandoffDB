# Handoff: ModelChoiceIteratorValue is not hashable

## Issue
`ModelChoiceIteratorValue` (`django/forms/models.py`, lines 1161–1172) defines `__eq__` but not `__hash__`. In Python 3, defining `__eq__` implicitly sets `__hash__ = None`, making the object unhashable. This broke custom `create_option()` overrides that use the option `value` as a dict key or in a set (e.g. `if value in self.show_fields` where `show_fields` is a dict). Membership in a list works because lists use `__eq__`, not hashing.

## Files and line ranges
- `django/forms/models.py:1161-1172` — class `ModelChoiceIteratorValue`; `__init__` stores `self.value`/`self.instance`, `__str__` returns `str(self.value)`, `__eq__` unwraps other `ModelChoiceIteratorValue` to `.value` and compares `self.value == other`. The fix belongs here: add `__hash__` that hashes the underlying `self.value` (consistent with `__eq__`, so equal objects hash equally).
- `django/forms/models.py:1201` — construction site: `ModelChoiceIteratorValue(self.field.prepare_value(obj), obj)`, confirming the wrapped value is the hashable PK/prepared value.
- `django/forms/utils.py:161` — `ErrorList.__eq__`; investigated and ruled out as unrelated.

## Tests
- `tests/model_forms/test_modelchoicefield.py` — existing tests `test_overridable_choice_iterator` (line 265), `test_choice_iterator_passes_model_to_widget` (line 282), and `test_custom_choice_iterator_passes_model_to_widget` (line 308) cover the iterator/value plumbing. Add a regression test asserting `hash(ModelChoiceIteratorValue(1, obj)) == hash(1)` and that the value works as a dict key.
- No existing tests reference `ModelChoiceIteratorValue` directly (grep across `tests/` found only unrelated hashable tests in `tests/utils_tests/test_hashable.py`).

## Ruled out
`ErrorList.__eq__` in `django/forms/utils.py` (unrelated); unhashable-int handling in `tests/lookup/tests.py`; `make_hashable` in `django/utils/hashable.py` (not applicable).

## Conclusion
Add `def __hash__(self): return hash(self.value)` to `ModelChoiceIteratorValue` so it remains hashable and consistent with `__eq__`.
