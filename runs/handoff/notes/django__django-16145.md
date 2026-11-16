# Handoff: `runserver 0:8000` prints `http://0:8000/`

**Issue:** `python manage.py runserver 0:8000` should be equivalent to `0.0.0.0:8000` per docs, but the banner prints `http://0:8000/` (unusable link). It should print `http://0.0.0.0:8000/`.

**Key files/lines:**
- `django/core/management/commands/runserver.py`
  - `naiveip_re` lines 14–22 — matches `addr` as IPv4/IPv6/FQDN; bare `0` matches the `fqdn` branch.
  - `handle()` lines 85–110 — parses `addrport`, sets `self.addr` (line 98), `_raw_ipv6` (87, 105, 110); no normalization of `"0"`.
  - `inner_run()` lines ~143–150 — banner uses `self.addr` verbatim, so `"0"` is printed.
- `django/core/servers/basehttp.py` lines 67–76 (WSGIServer), line 231 (`server_address = (addr, port)`) — binding works because socket treats `"0"` as `0.0.0.0`; display is the only bug.
- `django/contrib/staticfiles/management/commands/runserver.py` — subclasses Command; inherits behavior, no separate fix needed.

**Tests:** `tests/admin_scripts/tests.py`, `ManageRunserver` class (~1565–1625): `assertServerSettings` (1572–1578), `test_runserver_addrport` (~1580), default-addr overrides at 1616/1623. Add a case asserting `addrport="0:8000"` yields `addr == "0.0.0.0"` (and banner output).

**Docs:** `docs/ref/django-admin.txt` lines 948–1080 (`runserver` examples); `docs/intro/tutorial01.txt`.

**Ruled out:** basehttp binding logic is correct; staticfiles runserver only inherits; no other references to `naiveip_re`/`default_addr`/`_raw_ipv6` exist outside `runserver.py`.

**Conclusion:** Fix in `runserver.py` `handle()` by normalizing `self.addr == "0"` to `"0.0.0.0"` after parsing (before the banner), plus a regression test in `tests/admin_scripts/tests.py`.
