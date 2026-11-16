## Handoff note

**Issue:** `django-admin startproject` / `startapp` fetching a remote `--template` URL uses urllib’s default User-Agent, causing some hosts (notably GitLab/Cloudflare) to block requests. Desired behavior is `User-Agent: Django/<DJANGO_VERSION>`.

**Code that matters**
- `django/core/management/templates.py:10` — currently imports only `urlretrieve` from `urllib.request`; needs `Request`/`urlopen` or equivalent header-capable API.
- `django/core/management/templates.py:34` — `url_schemes = ['http', 'https', 'ftp']`; confirms remote templates are supported.
- `django/core/management/templates.py:281` — `urlretrieve(url, ...)` is the actual remote download path. This is the line to change: build a `Request` with `headers={'User-Agent': f'Django/{django.get_version()}'}` and fetch via `urlopen`, or otherwise pass the header. `django` is already imported at line 12.

**Tests/docs**
- `tests/admin_scripts/tests.py:1983` — `StartProject(LiveServerTestCase, AdminScriptTestCase)` is the relevant test area. Add a test here asserting the remote template request receives `User-Agent: Django/<version>`, ideally using a local server or mocking `urlopen`/`urlretrieve`.
- `tests/admin_scripts/management/commands/custom_startproject.py` — existing custom startproject test command, useful for template-related coverage.
- `docs/ref/django-admin.txt` — documents `startapp`/`startproject` and `--template`; update if behavior is described.

**Ruled out**
- No existing `urlopen`, `Request`, or `User-Agent` handling in `django/core/management/templates.py`.
- No `urlretrieve`/User-Agent coverage in `tests/admin_scripts/tests.py`.
- Middleware/request User-Agent tests (`tests/middleware/tests.py`, `tests/requests/tests.py`) are unrelated.

**Conclusion:** The fix belongs in `django/core/management/templates.py` around the import and line 281. Add regression coverage under `StartProject` and update the admin docs if needed.
