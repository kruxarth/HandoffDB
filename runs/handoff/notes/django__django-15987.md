# Handoff: FIXTURE_DIRS duplicate detection with `Path` instances

## Issue
`loaddata`'s duplicate validation of `settings.FIXTURE_DIRS` silently fails when entries are `pathlib.Path` objects, because comparisons mix `Path` and `str`.

## Key code — `django/core/management/commands/loaddata.py`
- **`Command.fixture_dirs` (lines 355–381)**: the cached property holding the bug.
  - **Line 364**: `fixture_dirs = settings.FIXTURE_DIRS` — raw entries, un-normalized.
  - **Line 365–366**: `len(fixture_dirs) != len(set(fixture_dirs))` — a `Path` and its string form hash/compare unequal, so `[Path(d), d]` is not flagged; raises `ImproperlyConfigured("settings.FIXTURE_DIRS contains duplicates.")` only for true duplicates.
  - **Line 370–373**: `app_dir in fixture_dirs` — same `Path`-vs-`str` mismatch, so a default `app/fixtures` dir given as `Path` also escapes the "default fixture directory" check.
  - **Line 381**: `dirs.extend(fixture_dirs)` — feeds un-normalized values downstream to `get_fixture_name_and_dirs` (lines 284–289) and `find_fixtures` (lines 315–342).
- No `pathlib`/`os.fspath` usage exists anywhere in the file (confirmed by grep). Module imports are lines 1–25.

## Fix direction
Normalize entries once at the top of `fixture_dirs` (e.g. `[os.fspath(dir_) for dir_ in settings.FIXTURE_DIRS]`) before the dedupe and default-dir checks; this repairs both checks and keeps downstream string handling consistent.

## Tests — `tests/fixtures_regress/tests.py`
- `test_fixture_dirs_with_duplicates` (lines 542–556): string-based duplicate case; currently passes.
- `test_fixture_dirs_with_default_fixture_path` (lines 558–566).
- **Line 585**: existing `@override_settings(FIXTURE_DIRS=[Path(_cur_dir) / "fixtures_1"])` — nearest `Path` precedent; extend with a `Path`-based duplicate test.
- Other `FIXTURE_DIRS` overrides: lines 196, 475, 573.

## Docs
No docs file referenced `FIXTURE_DIRS` in this session; behavior is documented in the `loaddata` command docs and `django/conf/global_settings.py:619`.

## Ruled out
Downstream fixture lookup (`find_fixtures`, `get_fixture_name_and_dirs`) as the root cause; `global_settings.py` definition.

## Conclusion
Root cause is un-normalized `Path` entries in `Command.fixture_dirs` (lines 364–373). Normalize via `os.fspath` and add a `Path`-duplicate regression test in `tests/fixtures_regress/tests.py`.
