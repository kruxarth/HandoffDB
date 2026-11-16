## Handoff note

**Issue:** Simplify migration serialization paths for expressions so re-exported classes deconstruct as `django.db.models.X()` instead of `django.db.models.expressions.X()`. `F` was already changed to `django.db.models.F()` in PR #14047; the task is to apply the same treatment to other expressions.

**Key files/lines:**
- `django/db/models/expressions.py`: `Expression` is decorated with bare `@deconstructible` at lines 393–394; `F` uses `@deconstructible(path='django.db.models.F')` at lines 581–582. `Value` is at line 734.
- `django/db/models/__init__.py` lines 13–17: re-exports `Case`, `Exists`, `Expression`, `ExpressionList`, `ExpressionWrapper`, `F`, `Func`, `OrderBy`, `OuterRef`, `RowRange`, `Subquery`, `Value`, `ValueRange`, `When`, `Window`, `WindowFrame`.
- `django/utils/deconstruct.py`: the `path` fallback only applies when `type(obj) is klass`, so adding `path` to the base `Expression` decorator will **not** affect subclasses.
- `tests/expressions/tests.py`: `FTests.test_deconstruct` at 986–991 already expects `django.db.models.F`; `Value` deconstruct tests at 1763–1776 still expect `django.db.models.expressions.Value`.
- `tests/migrations/test_writer.py` (`WriterTests`, line 200+) exercises migration serialization and is the relevant integration test.
- No documentation references to expression deconstruct paths were found under `docs/`.

**Ruled out:** `django/db/models/functions/*.py` and `django/db/models/aggregates.py` contain no `deconstruct` overrides; they inherit `Func`. A base-class-only fix is insufficient because of the `type(obj) is klass` check.

**Conclusion:** `F` is already correct; no code changes were made in this session. Implementing the issue requires per-class `@deconstructible(path='django.db.models.X')` decorators on re-exported expression classes and updating `Value` expectations in `tests/expressions/tests.py`.
