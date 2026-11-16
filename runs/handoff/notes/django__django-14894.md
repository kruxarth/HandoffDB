# Handoff: empty-queryset Subquery annotation bug

Issue: `Coalesce(Subquery(Comment.objects.filter(author_name__in=[]).annotate(x=Count('content')).values('x')[:1]), 101)` compiles to SQL `0`, so `A` is `0` and `F("A") + F("B")` is `0` instead of `101`/`200`. With a non-empty `__in` list the expected values appear.

Key paths:
- `django/db/models/lookups.py:388-408`: `In.process_rhs` raises `EmptyResultSet` for empty direct RHS; this is correct.
- `django/db/models/sql/compiler.py:260-271` (`get_select`): catches `EmptyResultSet` around each select expression and replaces the entire annotation with SQL `0`. This is the poisoning point.
- `django/db/models/expressions.py:150-156` (`empty_aggregate_value`), `:654-726` (`Func`), `:728-800` (`Value`), `:1110+` (`Subquery`).
- `django/db/models/functions/comparison.py:59-74`: `Coalesce.empty_aggregate_value`.
- `django/db/models/aggregates.py:24,29-30,120`; `django/db/models/sql/query.py:491-499` (`elide_empty`); `django/contrib/postgres/aggregates/statistics.py:39`.

Tests/docs: `tests/expressions/tests.py` subquery tests ~460-611; `tests/db_functions/comparison/test_coalesce.py`; `tests/annotations/tests.py:201-214` and `:866`; `tests/queries/tests.py:2467-2470,3059-3105`. Docs: `docs/ref/models/expressions.txt:417-422,962`; `docs/releases/4.0.txt:321`.

Ruled out: empty `__in` raising `EmptyResultSet`; non-empty-list SQL path; normal `Coalesce` NULL handling; `Value`/`F` arithmetic. No files edited; no tests run.

Conclusion: root cause is the blanket SQL `0` substitution in `get_select` for an empty subquery. Generalize `empty_aggregate_value` to an empty-result-set value and honor it in `Func`/`Coalesce`/`Subquery` compilation as `NULL`, so `Coalesce` fallback works while aggregate behavior stays consistent. Add regression tests for both `Coalesce(Subquery(...), 101)` and `F("A") + F("B")`.
