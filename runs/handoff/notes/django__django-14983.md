## Handoff: makemigrations numbering with squashed migrations

**Issue.** With `0001_initial`, `0002_auto_...` and a squashed `0001_squashed_0002_auto_...` all present, `makemigrations` emits `0002_...` instead of `0003_...`.

**Key code.**
- `django/db/migrations/autodetector.py:1253-1320` — `arrange_for_graph()` picks each app's leaf node and derives the new migration name/number. This is the likely culprit: the squashed leaf is named `0001_squashed_...`, so numbering restarts at 2 rather than continuing past the still-present `0002`.
- `django/db/migrations/autodetector.py:1330-1339` — `parse_number()` only reads the leading digits of a name; it has no knowledge of `replaces`.
- `django/core/management/commands/squashmigrations.py:165-190` — where `0001_squashed_...` names and `replaces` are produced.
- `django/db/migrations/graph.py:42-62` — `DummyNode`/replacement handling; `executor.py:248-290` (`check_replacements`) and `writer.py:184-186` (`replaces` serialization) are downstream only.

**Tests.** `tests/migrations/test_autodetector.py` (`test_arrange_for_graph`, ~line 592) covers naming but not squashed+original coexistence. Squashed fixtures live in `tests/migrations/test_migrations_squashed*`; command coverage at `tests/migrations/test_commands.py:341-372`, `548-594`, `801`. No regression test currently asserts the expected `0003` name.

**Docs.** `docs/topics/migrations.txt:625-698` (squashing workflow, including "leave the old ones in place"); `docs/releases/4.1.txt` for a release note.

**Ruled out.** Graph loading/`DummyNode` resolution, executor replacement bookkeeping, and writer `replaces` output — all behave correctly; the defect is purely name/number selection in `arrange_for_graph`/`parse_number`.

**Conclusion.** Next-number calculation must account for migrations listed in the squashed migration's `replaces` (or the max number among on-disk files), not just the leaf's leading number. Repo is Django 4.1 alpha at `66e4ec8`.
