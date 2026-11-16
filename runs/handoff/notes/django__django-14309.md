# Handoff: `Q() & ~Exists(...)` un-negates the Exists

## Issue
`Q() & ~Exists(Book.objects.all())` returns an object whose `negated` is `False`, so the negated `Exists` is silently un-negated when ANDed with an empty `Q()`. Reported against 3.2 and main (repo snapshot is 4.0 alpha, `django/__init__.py:3`).

## Relevant code
- `django/db/models/query_utils.py:42` — `Q._combine()`. The empty-`Q` shortcuts are the culprit: when `self` is falsy, it rebuilds the other operand via `other.deconstruct()` and `type(self)(*args, **kwargs)` instead of returning `other`. Line 67 is `Q.__invert__`.
- `django/db/models/expressions.py:1171-1180` — `Exists`. `__invert__()` does `clone = self.copy(); clone.negated = not self.negated`, mutating the clone.
- `django/db/models/expressions.py:1139` (`Subquery.copy`) and `:346` (`BaseExpression.copy`) — `__dict__` copy leaves `_constructor_args` stale.
- `django/utils/deconstruct.py` — `deconstructible` captures `_constructor_args` at `__init__` time only, so `deconstruct()` reports `negated=False` even after inversion. This is where the negation is lost.

## Tests / docs
- `tests/queries/test_q.py` (around `test_combine`, lines ~90-95) is the natural home for the regression test.
- `tests/expressions/tests.py:759-765` (`test_exists_in_filter`) exercises `~Exists()` round-trips; `tests/expressions/tests.py:456-459` covers `~Exists`/`~~Exists` annotations.
- `tests/queries/tests.py:1913` (`ExistsSql`) is SQL-level only.
- Docs: `docs/ref/models/expressions.txt` (`Exists`), `docs/ref/models/querysets.txt` (Q objects), plus a `docs/releases/4.0.txt` note.

## Ruled out
`Exists.__invert__` itself (flips correctly), `BaseExpression`/`Subquery.copy`, `Node.negate`/`Node.add` in `django/utils/tree.py`, and `Exists.as_sql` — none drop the flag.

## Conclusion
Fix in `Q._combine()`: when `self` is empty and `other` is already a resolved expression (`hasattr(other, 'resolve_expression')`), return `other` directly rather than round-tripping through `deconstruct()`/`Q(...)`, preserving `Exists.negated`. Add a regression test in `tests/queries/test_q.py`.
