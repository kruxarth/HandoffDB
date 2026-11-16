# Handoff: `Window(order_by=...)` descending-string support

**Issue.** `Window(order_by=...)` wraps its argument verbatim in `ExpressionList`, so `'-field'` strings are treated as field names rather than descending order, unlike `QuerySet.order_by()` and the Postgres aggregates' `ordering=` kwarg. The reporter suggested reusing `OrderableAggMixin.__init__`'s logic in `Window.__init__`.

**Key code.**
- `django/db/models/expressions.py:1289-1392` — `Window` (`__init__`); this is where `order_by` is normalized and wrapped in `ExpressionList`. The fix belongs here.
- `django/contrib/postgres/aggregates/mixins.py:4-14` — `OrderableAggMixin.__init__`; lines 10-12 contain the exact transform to reuse: `OrderBy(F(o[1:]), descending=True)` for strings starting with `'-'`.
- `django/db/models/expressions.py:915` (`ExpressionList`), `:1207` (`OrderBy`), `:600`/`:362-365` (`asc()`/`desc()`) — surrounding API.
- `django/contrib/postgres/aggregates/general.py:37,78,94` — `ArrayAgg`/`JSONBAgg`/`StringAgg`, the mixin's consumers.

**Tests and docs.** `tests/expressions_window/tests.py` (`WindowFunctionTests`; parametrized `order_by` cases at lines 55-58); `tests/postgres_tests/test_aggregates.py:170-200,455-505` show expected behaviour for `'-char_field'`. Docs: `docs/ref/models/expressions.txt` (Window/OrderBy) and `docs/ref/contrib/postgres/aggregates.txt`.

**Ruled out.** No `OrderByList`/`Sort` abstraction exists anywhere in the tree (`grep OrderByList` is empty); introducing one, or renaming `OrderBy` to `Sort`, is a public-API change and unnecessary. Refactoring `OrderableAggMixin` to use `ExpressionList` is out of scope.

**Conclusion.** Patch `Window.__init__` with the same minus-sign normalization used at `mixins.py:10-12` (optionally as a shared helper), then add a `Window` test using `order_by='-salary'` in `tests/expressions_window/tests.py`.
