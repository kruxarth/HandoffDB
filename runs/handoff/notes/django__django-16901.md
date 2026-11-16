# Handoff: `Q() ^ Q() ^ Q()` fallback is exactly-one, not parity

## Issue
On backends without logical XOR (PostgreSQL, SQLite, Oracle — `supports_logical_xor = False`), `WhereNode.as_sql()` compiles an N-way XOR into `(a OR b OR c) AND (a + b + c) = 1`, i.e. *exactly one* true. Native XOR (MySQL, `django/db/backends/mysql/features.py:58`) and the correct semantics require *odd* parity: `a ^ b ^ c` is true for 1 or 3 true args. Regression from #29865.

## Key code
- `django/db/models/sql/where.py:128-150` — the fallback branch in `WhereNode.as_sql()`. Builds `lhs` = `WhereNode(children, OR)` and `rhs` = `Exact(Sum(Case(When(child, then=1), default=0) ...), 1)`. The `= 1` comparison is the bug; it must be `MOD(sum, 2) = 1` (see `Mod` in `django/db/models/functions/math.py:124`, or emit `% 2` directly).
- `django/db/models/sql/where.py:114-127` — surrounding `full_needed`/`empty_needed` logic; unaffected but read for context.
- `django/db/models/query.py:485-501` and `django/db/models/query_utils.py:74-75` — only combine nodes, no SQL; not the cause.

## Tests / docs
- `tests/queries/test_q.py` — `test_xor` (and related `Q` combination tests) is where to add 3+ argument parity cases and negation cases.
- `tests/expressions/tests.py` — bitwise-XOR tests; unrelated.
- Docs: `docs/ref/models/querysets.txt` (Q objects / `^` operator) and `docs/topics/db/queries.txt` describe the operator semantics.

## Ruled out
Bitwise paths: `Combinable.BITXOR "#"` / `bitxor()` (`django/db/models/expressions.py:59-125`), SQLite `BITXOR` (`django/db/backends/sqlite3/_functions.py:330`), PostgreSQL `has_bit_xor` (`postgresql/features.py:135`), Oracle `NotSupportedError` (`oracle/operations.py:644`). None participate in `Q` logical XOR.

## Conclusion
Bug is confined to the fallback in `where.py:128-150`; replace the `= 1` count with a modulo-2 parity check, keeping the existing `OR`/empty-result short-circuits intact.
