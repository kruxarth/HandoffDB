## Handoff: MigrationRecorder ignores `allow_migrate`

**Issue:** With a multi-db router returning `False` for non-default DBs, `MigrationRecorder.ensure_schema()` still creates `django_migrations` there, and recorder calls record/unrecord migrations despite routing.

**Key files/lines:**
- `django/db/migrations/recorder.py:54-70` — `has_table()` / `ensure_schema()` creates `django_migrations` unconditionally.
- `django/db/migrations/recorder.py:75-90` — `applied_migrations()` assumes table presence.
- `django/db/migrations/executor.py:19`, `:100`, `:251-253`, `:265-266`, `:283-287` — executor constructs recorder, unconditionally calls `ensure_schema()`, then records/applies via recorder.
- `django/db/utils.py:272-288` — router `allow_migrate()` / `allow_migrate_model()` behavior.
- `django/core/management/commands/migrate.py:12`, `:324` — migrate command uses router for model selection.
- `django/db/backends/base/creation.py:127-128` — serialization already respects router.

**Tests/docs:**
- `tests/migrations/test_multidb.py` — existing multi-db operation tests.
- `tests/migrations/routers.py` — `TestRouter`, `DefaultOtherRouter`, etc.
- `tests/migrations/test_executor.py` — recorder/executor tests.
- `tests/migrations/test_commands.py:129+`, `:1117-1168` — router-aware migrate/makemigrations checks.
- `tests/migrations/test_base.py:28` — recorder cleanup.
- `docs/topics/db/multi-db.txt:176-215` — `allow_migrate()` contract.
- `docs/releases/4.1.txt:213` — migrations release-note placeholder.

**Ruled out:** Router dispatch itself works; `allow_migrate_model()` and serializer paths already honor routers. `makemigrations` consistency checks are already router-aware.

**Conclusion:** Root cause is the executor/recorder path calling `ensure_schema()` and recorder methods without consulting `router.allow_migrate()`. Fix should make recorder/executor skip schema creation and recording when migrations are disallowed for that connection, with tests asserting `django_migrations` is not created on routed-off DBs.
