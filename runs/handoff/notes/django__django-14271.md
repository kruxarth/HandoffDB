# Handoff: Combined queryset in subquery fails (Django 3.2)

## Issue
A queryset using OR-combination (`qs1 | qs2`) inside a `Subquery()` generates invalid SQL on Django 3.2 when one branch has an `exclude()` on a reverse relation. The `split_exclude()` rewrite emits an `EXISTS` subquery referencing `V0.user_id`, but `V0` is never defined in scope (`sqlite3.OperationalError: no such column: V0.user_id`). Worked in 3.1.8, where `exclude()` compiled to a `NOT IN` subquery.

## Files/line ranges
- `django/db/models/sql/query.py`
  - `Query.combine()` (~line 566) — merges RHS into LHS; suspect it doesn't relabel RHS base-table alias references, so the `Exists()` subquery retains a stale alias after OR-merge.
  - `Query.change_aliases()` (848–867) and `Query.bump_prefix()` (887–930) — alias relabeling/prefix machinery.
  - `Query.resolve_expression()` (1047–1065) — sets `clone.subquery = True`, bumps prefix.
  - `split_exclude()` (1770–1835) — builds the `Exists(query)` at line 1822; source of the `V0` reference.
- `django/db/models/sql/compiler.py`
  - `get_combinator_sql()` (449) — combinator SQL.
  - Subquery extra-select wrapping (~631–651).
- `django/db/models/expressions.py` — `Subquery` class ~1106; `Exists`/`relabeled_clone` (~338, 635, 650).
- `django/db/models/sql/where.py` — `WhereNode.relabel_aliases()` (~134).

## Tests/docs
- `tests/queries/tests.py` — likely home for regression test; see `test_subquery_exclude_outerref` (~2765), `test_combine_join_reuse` (~1314), combine tests (~1290–1345).
- `tests/queries/test_qs_combinators.py` — covers `union`/`intersection`/`difference` set operations (not the `|` OR path).
- `tests/queries/models.py` — models: `Number` (143), `Celebrity`/`Fan` (265/277), `Job`/`JobResponsibilities`/`Responsibility` (506–518).
- Docs: `docs/ref/models/querysets.txt`, `docs/ref/models/expressions.txt` (Subquery/Exists).

## Ruled out
- Compiler `get_combinator_sql()` — set-operation path; reproducer uses `|` OR, not `union`.
- QuerySet-level combine validation in `django/db/models/query.py`.

## Conclusion
Root cause is `Query.combine()` failing to relabel RHS alias references into the merged query, leaving `Exists` subqueries pointing at an undefined alias. Fix belongs in `Query.combine()` in `django/db/models/sql/query.py`. Reproduction blocked: `asgiref` is not installed in this environment.
