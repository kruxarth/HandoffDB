# Handoff: Drop Python 3.6 & 3.7 support

**Issue:** Django 4.0 should drop Python 3.6 and 3.7 (Django 3.2 LTS was the last to support them).

**Config:**
- `setup.cfg:20-21` classifiers for 3.6/3.7; `:37` `python_requires = >=3.6` → `>=3.8`.
- `tox.ini` deps `py{3,36,37,38,39}` → `py{3,38,39}`.

**Code (version gates/shims):**
- `django/utils/version.py:12-15` `PY36`/`PY37` constants — remove; keep `PY38`/`PY39`.
- `django/test/runner.py:544-554` `if PY37:` guard around `-k` option — always add.
- `django/utils/http.py:346-430` `parse_qsl` backport + TODO — remove; `django/http/request.py:26-30` conditional import — import from `urllib.parse` directly.
- `django/db/backends/sqlite3/base.py:183` `str()` TODO (PY36), `:209` PY38 check; `client.py:11` `str()` TODO (PY37).
- `django/db/migrations/questioner.py:47` getattr PY36; `django/utils/module_loading.py:77` PY36 comment; `django/utils/autoreload.py:234,240` `str()` PY37; `django/http/cookie.py:6` SameSite PY37; `django/db/backends/postgresql/base.py:265-268` `current_task` branch; `django/utils/functional.py:14` obsolete `name` arg.

**Tests:** `tests/test_runner/test_discover_runner.py:14,86` (PY37 skipUnless); `tests/test_runner/test_parallel.py:5,83` (PY37); `tests/utils_tests/test_http.py:336+` backport tests; `tests/runtests.py` PY37 import.

**Docs:** `docs/faq/install.txt:53-56` table; `docs/internals/contributing/writing-code/unit-tests.txt:92-99`; `docs/ref/utils.txt:498`.

**Ruled out:** GEOS `geos_version < (3, 7)` checks (`django/contrib/gis/geos/coordseq.py:201`, `prototypes/io.py:239,250`) and `sqlite_version_info` comparisons are library versions, not Python. `docs/releases/4.0.txt:18-22` already states 3.8–3.10, so no release-note change needed.

**Conclusion:** Docs already claim 3.6/3.7 unsupported; remaining work is removing `PY36`/`PY37` and all dependent branches/shims plus metadata/tests. Not yet applied (working tree clean).
