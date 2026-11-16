## Handoff: showmigrations squash "soft applied" state

**Issue:** `showmigrations` marks a squashed migration `[X]` when all its replaced migrations are recorded applied, even though the squashed migration itself is not in the migration recorder. The command needs to distinguish this "soft applied" state from truly recorded application.

**Key code:**
- `django/db/migrations/loader.py:224-256` — `build_graph()` collects `self.replacements` and merges replacement status into `self.applied_migrations`. Lines 241-247 are the critical logic: if every `migration.replaces` target is applied, `self.applied_migrations[key] = migration`; otherwise it pops the key. This conflates soft-applied and recorded-applied states, so consumers cannot tell them apart.
- `django/core/management/commands/showmigrations.py` — `show_list`/`show_plan` render `[X]` from `loader.applied_migrations`; no separate replacement/soft-applied marker exists.
- `django/db/migrations/executor.py:262-278` — `check_replacements()` records a squashed migration applied when all replaced migrations are applied, explaining why running `migrate` is currently required.

**Tests:**
- `tests/migrations/test_commands.py:299-375` — `test_showmigrations_list`, `test_showmigrations_list_squashed` (squashed output at 338-375).
- `tests/migrations/test_commands.py:545-591` — `test_showmigrations_plan_squashed`.
- `tests/migrations/test_commands.py:908+` — `test_migrate_record_replaced`.
- `tests/migrations/test_loader.py:247-370` and `440-520` — squashed-loading behavior.

**Docs:**
- `docs/ref/django-admin.txt:1136-1170` — `showmigrations` output/`[X]` semantics.
- `docs/topics/migrations.txt:653-686` — migration squashing.
- `docs/releases/4.0.txt:231-247` — Management Commands/Migrations release notes.

**Ruled out:** No existing "soft" marker, option, or documentation reference; grep found no implementation. The behavior is not in the command alone but originates in loader state merging. No code changes were made (snapshot only).

**Conclusion:** Fix requires loader to retain separate soft-applied replacement state (rather than only populating `applied_migrations`) and `showmigrations` to render a distinct indicator, with matching tests/docs updates.
