# Handoff: `through_fields` unhashable in `ManyToManyRel`

## Issue
`ForeignObjectRel.identity` feeds `__hash__`, so every element must be hashable. `ManyToManyRel.identity` includes `self.through_fields` raw, but `through_fields` is often a list (e.g. `through_fields=['child', 'parent']`), causing `TypeError: unhashable type: 'list'` in `ForeignObjectRel.__hash__`. It surfaces during `Model.check()` → `_check_field_name_clashes` when a proxy model is present (proxy models run extra checks, so they reach the clash check that hashes rels).

## Key files/lines
- `django/db/models/fields/reverse_related.py`
  - L14: `make_hashable` already imported.
  - L120–126: `ForeignObjectRel.identity` — precedent: wraps `limit_choices_to` in `make_hashable`.
  - L139: `__hash__` returns `hash(self.identity)`.
  - L290–304: `ManyToManyRel.__init__` stores `self.through_fields` unnormalized.
  - **L309–315: the bug** — `identity` returns `self.through_fields` without `make_hashable`.
  - L317–324: `get_related_field` indexes `through_fields[0]` (list indexing is fine; don't change storage).
- `django/db/models/base.py` L1440–1470: `_check_field_name_clashes` does `if f not in used_fields`, triggering the hash.

## Tests/docs
- `tests/invalid_models_tests/test_models.py` — `OtherModelTests.test_m2m_to_concrete_and_proxy_allowed` (L1505–1522) and proxy-related tests near L1513; `FieldNamesTests` (L623+) for clash checks.
- `tests/invalid_models_tests/test_relative_fields.py` — `through_fields` validation tests (L1605–1710).
- `tests/check_framework/test_model_checks.py` L123 (`test_no_collision_for_proxy_models`).
- `tests/m2m_through/`, `tests/m2m_through_regress/` for M2M-through behavior.
- Docs: `docs/ref/checks.txt`, `docs/ref/models/fields.txt` (`through_fields`), `docs/releases/3.2.txt` (identity/hash change).

## Ruled out
- `limit_choices_to` handling (already wrapped).
- Storage normalization to tuple — unnecessary and would alter `get_related_field` semantics.
- Missing import — already present.

## Conclusion
Fix: wrap `self.through_fields` in `make_hashable(...)` inside `ManyToManyRel.identity` (L309–315), matching L126. Add a regression test covering a proxy model plus a `through_fields` list; then run `tests/invalid_models_tests`, `tests/check_framework`, `tests/m2m_through`.
