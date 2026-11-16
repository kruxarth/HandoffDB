# Handoff: robust `on_commit` handlers

## Issue
`transaction.on_commit()` callbacks are run serially; if one raises, the remaining callbacks never execute (see `tests/transaction_hooks/tests.py::test_error_in_hook_doesnt_prevent_clearing_hooks`, line 184). No way to mark individual handlers as robust, unlike signals' `send_robust`. Proposal: add `robust=False` kwarg to `on_commit`.

## Relevant code
- `django/db/transaction.py:128-133` — public `on_commit(func, using=None)` wrapper; needs `robust` param passed through.
- `django/db/backends/base/base.py:726-739` — `BaseDatabaseWrapper.on_commit`; validates callable, appends `(set(self.savepoint_ids), func)` to `self.run_on_commit`. Must accept `robust` and store it in the tuple.
- `django/db/backends/base/base.py:741-747` — `run_and_clear_commit_hooks`; unpacks `sids, func = ...pop(0)` and calls `func()` with no error handling. Must unpack the new robust flag and wrap robust callbacks in try/except.
- `django/db/backends/base/base.py:419-421` — savepoint rollback filters `run_on_commit` by unpacking `(sids, func)`; tuple shape change requires updating this.
- `django/db/backends/base/base.py:109,268,344,350` — `run_on_commit` initialization/resets.

## Tests and docs
- `tests/transaction_hooks/tests.py` — add coverage for robust vs non-robust ordering and exception isolation; existing validation tests at lines 233-242.
- `docs/topics/db/transactions.txt:297-309` — document the new `robust` argument.

## Ruled out
Not a transaction-clearing bug (`run_on_commit` is reset before execution at lines 743-744). Not savepoint filtering. No existing `robust` mechanism anywhere.

## Conclusion
Implement `robust` kwarg (default `False`) in both `on_commit` layers, store the flag in `run_on_commit` tuples, update the savepoint-filter unpacking, and guard robust callbacks in `run_and_clear_commit_hooks` so failures don't halt remaining handlers.
