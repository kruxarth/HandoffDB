# Handoff: logical XOR for `Q()` / `QuerySet`

## Issue
Add logical XOR (`^`) to `Q()` and `QuerySet`, analogous to `&`/`|`. No XOR exists in the ORM; only bitwise XOR (`F().bitxor()`, Postgres `BitXor`).

## Key files
- `django/db/models/query_utils.py:32-73` — `Q(tree.Node)`: connector constants `AND`/`OR` (39-40), `_combine` (51-65), `__or__`/`__and__`/`__invert__` (67-73). Add `XOR` connector and `__xor__`.
- `django/db/models/query.py:368-396` — `QuerySet.__and__`/`__or__` call `query.combine(..., sql.AND/OR)`. Add `__xor__`.
- `django/db/models/sql/where.py:10-11` — only `AND`/`OR` constants; `WhereNode` renders connector at ~83-114; `split_having` (33-68) special-cases `OR` for HAVING pushdown.
- `django/db/models/sql/__init__.py` — exports only `AND, OR` (must add `XOR`).
- `django/db/models/sql/query.py` — `combine` (588-700), `build_filter` (1516-1565), `JoinPromoter` (2574-2640) all assume binary `AND`/`OR`; join-promotion logic (`617`, `679`, `2624-2637`) needs care.
- `django/db/backends/base/features.py` — no `supports_logical_xor`; only `supports_boolean_expr_in_select_clause` (301, Oracle False at `oracle/features.py:65`).

## Tests
- `tests/queries/test_q.py` — `QTests` combine/empty/TypeError tests.
- `tests/queries/tests.py:2383` — `QuerySetBitwiseOperationTests` (setup/fixtures reusable).

## Docs
- `docs/topics/db/queries.txt:686-692` (bitwise only), `docs/releases/4.1.txt:96` (`BitXor` aggregate). No logical-XOR docs.

## Ruled out
`expressions.py:57,110` `BITXOR` and Postgres `BitXor` are bitwise, unrelated. No existing `__xor__`/XOR in ORM; SQLite lacks native XOR, so portable expansion is needed.

## Conclusion
Implement XOR by expanding to `(a OR b) AND NOT (a AND b)` in `WhereNode`/`Query.combine` (or a `supports_logical_xor` feature flag for native backends), adding `Q.__xor__`, `QuerySet.__xor__`, and the `XOR` constant/export. Verify join promotion and `split_having`.
