## Handoff note

**Issue:** Moving a single-field `unique_together` to `Field(unique=True)` autogenerates `AlterField(unique=True)` before `AlterUniqueTogether(unique_together=set())`. On MySQL this fails with `Duplicate key name ..._uniq` because the old unique_together constraint still exists when `AlterField` tries to add the field-level unique index.

**Key code:**
- `django/db/migrations/autodetector.py:150-195` — operation generation order. `generate_altered_fields()` runs before `generate_altered_unique_together()` (line 187), producing the bad order.
- `django/db/migrations/autodetector.py:1131-1170` — `_generate_altered_foo_together()` correctly detects the removed `unique_together`; the problem is ordering/dependencies, not detection.
- `django/db/migrations/autodetector.py:409-423` — existing `foo_together_change` dependency handling covers field removal but not this `AlterField`/`AlterUniqueTogether` interaction.
- `django/db/backends/base/schema.py:415-430` — `alter_unique_together()` correctly deletes/creates composed unique constraints when called in the right order.
- `django/db/backends/base/schema.py:621-690` — `_alter_field()` handles unique removal/creation; it does not avoid recreating an existing equivalent unique constraint.

**Tests:**
- `tests/migrations/test_autodetector.py:1522-1540` — add/remove `foo_together` detection.
- `tests/migrations/test_operations.py:1883-1930` — `AlterUniqueTogether`.
- `tests/migrations/test_operations.py:1333-1410` — `AlterField`.
- `tests/schema/tests.py:2101-2168` — `unique_together` schema behavior.

**Docs:** `docs/ref/migration-operations.txt` (`AlterField`, `AlterUniqueTogether`) and `docs/topics/migrations.txt`; not yet updated.

**Ruled out:** Incorrect `unique_together` state detection and a broken `alter_unique_together()` implementation. The failure is generated operation ordering/dependency.

**Conclusion:** Fix the autodetector so removal of `unique_together` is ordered before `AlterField` when the field becomes `unique=True` (or teach the schema editor to skip the duplicate unique index). Add an autodetector regression asserting `AlterUniqueTogether` precedes `AlterField` for this transition.
