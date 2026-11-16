# Handoff: durable atomic blocks inside TestCase

## Issue
`transaction.atomic(durable=True)` nested inside `TestCase` silently skips the `RuntimeError` raised under `TransactionTestCase`, because `TestCase` globally disables `Atomic._ensure_durability`. Durability errors therefore surface only in staging/production.

## Key files and lines
- `django/db/transaction.py:161-182` — `Atomic` docstring, `_ensure_durability` (168-170), `__init__` (172-175), and the durability check in `__enter__` (180-184).
- `django/test/testcases.py:1131-1169` — `TestCase`; `_enter_atomics` (1144-1151) opens the wrapper atomics; the comment near line 1169 disables the durability check for the class.
- `django/db/backends/base/base.py:72-87` — transaction state (`in_atomic_block`, `savepoint_ids`, `needs_rollback`), reset in `connect()` at 195-203. No stack of active `Atomic` objects exists.

## Tests and docs
- `tests/transactions/tests.py:504-570` — `DurableTests` covers commit, nested outer/inner/both durable, and the existing TestCase exception at 540-548.
- `tests/test_utils/test_testcase.py` exercises TestCase atomic teardown.
- `docs/topics/db/transactions.txt` documents `durable=True`.

## Ruled out
Removing `_ensure_durability` globally is not viable: every `TestCase` wraps tests in an atomic block, so durable blocks would fail immediately. Existing connection state has no per-atomic stack; `in_atomic_block` alone cannot distinguish the TestCase wrapper from user atomics.

## Conclusion
Implement the proposed marker/stack design: add `Atomic._from_testcase = False`; append/pop each `Atomic` on `connection.atomic_blocks` in `__enter__`/`__exit__`; set `_from_testcase = True` on wrappers in `TestCase._enter_atomics`; change the durability check to raise unless the innermost enclosing atomic is the TestCase wrapper. Remove the global disable in `testcases.py`. Add TestCase-specific durable tests and update docs.
