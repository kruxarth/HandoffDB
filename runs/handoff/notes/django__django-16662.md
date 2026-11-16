## Handoff: migration import ordering

**Issue:** Generated migration files sort imports only by module name, so `from ... import ...` lines can precede plain `import ...` lines, violating Django's coding style and isort defaults.

**Code:** `django/db/migrations/writer.py`, `MigrationWriter.as_string()` lines 161–179. Line 178 is the culprit: `sorted(imports, key=lambda i: i.split()[1])` sorts every import by module name regardless of style. Lines 170–174 merge `models` into the `migrations` import and should be preserved. The fix belongs here: partition imports into plain `import` statements and `from ... import ...` statements, sort each group by module, and emit plain imports first. `MigrationWriter` is the only place migration import text is generated.

**Tests:** `tests/migrations/test_writer.py` covers `MigrationWriter.as_string()` and is the place to add/adjust an assertion for mixed plain/`from` imports. Search for existing `as_string`/import-order assertions.

**Docs:** `docs/internals/contributing/writing-code/coding-style.txt` (import ordering guidance) and `docs/howto/writing-migrations.txt` relate conceptually. No doc change is needed because the documented style is already correct; the generator is what diverges.

**Ruled out:** `django/db/migrations/serializer.py` only contributes import strings (e.g. lines 100, 306); it does not order them. `migration_imports` (lines 161–164, 180–186) is a separate comment block of migration module paths and is not the import list being sorted. The `sorted()` at line 97 is unrelated (operation kwargs signature order). No changes needed in `django/apps`, `django/conf`, or `loader.py`.

**Conclusion:** Single localized defect in `writer.py:178`; fix by style-aware grouping while retaining module-name sorting within each group.
