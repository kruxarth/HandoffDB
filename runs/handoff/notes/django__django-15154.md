# Handoff: functional `UniqueConstraint` causes false “already exists” in admin

**Issue:** Admin add form raises a uniqueness `ValidationError` for models using expression-based `UniqueConstraint` (e.g. `UniqueConstraint(Lower('name'))`). `Model.objects.create()` works because it bypasses `full_clean()`.

**Root cause:** `django/db/models/options.py:861-870` (`Options.total_unique_constraints`) returns every `UniqueConstraint` with `condition is None`, including expression-based constraints. Those have an empty `fields` tuple, which downstream validation treats as a uniqueness check over no fields, producing spurious errors.

**Mattering code:**
- `django/db/models/options.py:861-870` — filter must exclude `constraint.contains_expressions` (`django/db/models/constraints.py:16,163`) or empty `fields`.
- `django/db/models/base.py:1047-1085` (`validate_unique`, `_get_unique_checks`), especially `1076-1082` where `total_unique_constraints` is appended; `1120-1160` (`_perform_unique_checks`) builds lookups from `fields`.
- Other consumers: `django/db/models/query.py:705`, `django/contrib/admin/views/main.py:394`, `django/contrib/auth/checks.py:57`, `django/db/models/fields/related.py:562`.
- `django/db/models/constraints.py:92-170` — `UniqueConstraint`; `contains_expressions` at 163.

**Tests/docs:**
- `tests/constraints/tests.py:401-409` — existing validation tests; add expression-constraint regression here.
- `tests/constraints/models.py:45-105` — constraint fixtures; add an expression-based model.
- `tests/validation/test_unique.py` — `_get_unique_checks` coverage.
- `docs/ref/models/constraints.txt:36-41`, `docs/ref/models/instances.txt:338`.

**Ruled out:** admin/ModelForm uniqueness handling, field-level unique checks, partial (`condition`) constraints (already skipped), and the ORM `create()` path.

**Conclusion:** Exclude expression-based `UniqueConstraint`s from `total_unique_constraints` (or have consumers ignore empty `fields`), then add a regression test.
