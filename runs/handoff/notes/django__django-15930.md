## Handoff: `Case()` crashes with `~Q(pk__in=[])`

**Issue.** `User.objects.annotate(_a=Case(When(~Q(pk__in=[]), then=Value(True)), default=Value(False), output_field=BooleanField()))` compiles to invalid SQL: `CASE WHEN THEN true ELSE false END`. Expected: every row is true, since negating an empty set is always true.

**Cause / key files.**
- `django/db/models/lookups.py:415-460` — `In.process_rhs()` raises `EmptyResultSet` when the RHS is empty (`~445`). This is correct.
- `django/db/models/sql/where.py:81-133` — `WhereNode.as_sql()` catches `EmptyResultSet`; a negated empty node returns `("", [])`. This is intentional for WHERE clauses.
- `django/db/models/expressions.py:1245-1318` — `When.as_sql()` uses `"WHEN %(condition)s THEN %(result)s"`; it does not guard against an empty compiled condition, producing `WHEN THEN`.
- `django/db/models/expressions.py:1319+` — `Case` compiles each `When`; no empty-condition handling.
- Supporting context: `django/db/models/query_utils.py:35+` (`Q`), `django/db/models/sql/query.py:1144` (annotation resolution), `:1349` (`build_filter`), `:1546` (`_add_q`).

**Tests/docs.**
- `tests/expressions_case/tests.py:411` and `:1645` cover empty `pk__in=[]` in `When`/`Case`.
- `tests/annotations/tests.py:263-292` (`test_empty_expression_annotation`, full-expression tests).
- `tests/queries/tests.py:3531+` (`WhereNodeTest`, empty-node semantics).
- Docs: `docs/ref/models/conditional-expressions.txt`, `docs/ref/models/querysets.txt` (`annotate`).

**Ruled out.** `In.process_rhs()` raising `EmptyResultSet` and negated `WhereNode` returning `("", [])` are by design (`NothingNode`); not lookup/WHERE bugs. Could not execute tests: Django 4.2 alpha imports `asgiref`, absent in the environment; no edits made.

**Conclusion.** Fix belongs in conditional-expression handling (`When`/`Case` in `expressions.py`): detect an empty compiled condition and treat it as always-true (or resolve/skip the `When`) instead of emitting `WHEN THEN`.
