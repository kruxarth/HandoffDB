## Handoff note: ASGI/Hypercorn docs don't cover static files

**Issue.** The Hypercorn deployment page never says static files won't be served, so users follow `manage.py runserver` → deploy → discover missing static files. Reporter asks whether WhiteNoise guidance belongs in Django docs.

**Docs that matter.**
- `docs/howto/deployment/asgi/hypercorn.txt:1-36` — the page in question; setup/run only, no static-files section.
- `docs/howto/deployment/asgi/daphne.txt` and `uvicorn.txt` — same omission (grep for "static" returns nothing).
- `docs/howto/deployment/asgi/index.txt:1-20` — toctree listing the three ASGI server pages.
- `docs/howto/deployment/index.txt:26` — already links to `/howto/static-files/deployment`.
- `docs/howto/static-files/deployment.txt` — the canonical static-files-in-production guidance to cross-reference.
- `docs/howto/deployment/wsgi/modwsgi.txt:178-212` — WSGI precedent: explicitly discusses serving static files, which ASGI pages lack.
- `docs/ref/contrib/staticfiles.txt` — staticfiles app reference.

**Code that matters.**
- `django/contrib/staticfiles/handlers.py:15` (`StaticFilesHandlerMixin`), `:64` (`StaticFilesHandler`, WSGI), `:80` (`ASGIStaticFilesHandler`). An ASGI static handler already exists.
- `django/contrib/staticfiles/management/commands/runserver.py:31` — `runserver` wraps only the WSGI `StaticFilesHandler`, explaining the dev/prod gap.

**Tests.** `tests/staticfiles_tests/test_handlers.py` (`TestASGIStaticFilesHandler`, lines 1-24) and `tests/asgi/tests.py:108` both exercise `ASGIStaticFilesHandler`; `tests/staticfiles_tests/test_liveserver.py` covers runserver serving.

**Ruled out.** No `whitenoise`/`WhiteNoise` reference anywhere in the tree. `ASGIStaticFilesHandler` is implemented and tested, so this is not a code bug and needs no handler change. No relevant entry in `docs/releases/4.0.txt`; grep found no existing ASGI/static docs to amend.

**Conclusion.** Documentation-only fix: add a "Serving static files" section to `hypercorn.txt`, `daphne.txt`, and `uvicorn.txt` pointing to `/howto/static-files/deployment`, noting `ASGIStaticFilesHandler` and third-party options (e.g. WhiteNoise). No core code change.
