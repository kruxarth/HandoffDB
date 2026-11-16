# Handoff: `bulk_update()` ignores `db_for_write`

**Issue** — `QuerySet.bulk_update()` dereferences `self.db` before setting `self._for_write = True`. The router therefore returns `db_for_read()`, and the `transaction.atomic(using=self.db, ...)` block is created on the read alias, so updates are neither routed to nor atomic on the write database. Found via ticket 33501, comment 3.

**Code** — `django/db/models/query.py:704-760` (`QuerySet.bulk_update`). The `self._for_write = True` assignment currently sits after the first `self.db` access and the atomic-block creation. Move the flag to the top of the method (after the batch-size/field/pk validation) so every subsequent `self.db` lookup resolves via `db_for_write()`. Note `django/db/migrations/state.py:618` also defines `bulk_update`, but that is an unrelated `StateApps` context manager — do not touch it.

**Tests** — `tests/queries/test_bulk_update.py` (`BulkUpdateNoteTests:28`, `BulkUpdateTests:109`) contains no routing coverage; grepping it for `_for_write`/`db_for_write`/`router`/`atomic` returns nothing, so it is the wrong place for the regression test. Use `RouteForWriteTestCase` in `tests/multiple_database/tests.py:2276-2300`, whose `WriteCheckRouter.db_for_write()` (line 2291) raises `RouterUsed`. Add a `test_bulk_update` there asserting `e.mode == RouterUsed.WRITE`, `e.model`, and `e.hints`. Router fixtures live in `tests/multiple_database/routers.py`.

**Docs** — `docs/ref/models/querysets.txt` (`bulk_update` section) and `docs/topics/db/multi-database.txt` (routers / write DB selection).

**Ruled out** — `migrations/state.py` `bulk_update`; `tests/postgres_tests/test_bulk_update.py` (backend-feature only); existing `tests/queries/test_bulk_update.py` tests.

**Conclusion** — Root cause confirmed: flag ordering in `query.py`. Fix by setting `_for_write` before any `self.db` use, and add the `RouteForWriteTestCase` regression test.
