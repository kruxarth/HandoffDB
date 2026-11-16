## Handoff: get_admin_url ignores custom AdminSite

**Issue:** Readonly ForeignKey/OneToOne fields in a custom AdminSite render links to `/admin/...` instead of `/custom-admin/...`. Cause: `reverse()` in `AdminReadonlyField.get_admin_url()` omits `current_app`.

**Key code:**
- `django/contrib/admin/helpers.py:206-214` — `get_admin_url()`; line 212 `url = reverse(url_name, args=[quote(remote_obj.pk)])` lacks `current_app`. `self.model_admin` is available on the instance (set in `__init__`, ~line 193).
- `django/contrib/admin/helpers.py:246` — call site in `contents()` for `ForeignObjectRel`/`OneToOneField` values.
- `django/contrib/admin/helpers.py:119` — `AdminReadonlyField` constructed with `model_admin=self.model_admin`, so the site name is reachable.

**Established patterns (fix should mirror these):**
- `django/contrib/admin/widgets.py:270-271` (`get_related_url`) and `:143` pass `current_app=self.admin_site.name`.
- `django/contrib/admin/sites.py:476,481` do the same.
- `django/contrib/admin/options.py:1310,1323,1340` reverse admin URLs without `current_app`; not investigated, likely unrelated (they operate within the active site context).

**Ruled out / out of scope:** `django/contrib/admin/models.py:147` (`LogEntry.get_admin_url`) also omits `current_app`, but has no `model_admin`/site context — separate concern, do not change here. No `current_app` exists in `widgets.py` beyond the two sites above.

**Tests:** `tests/admin_views/tests.py` — `ReadonlyTest` (line 4988), `test_readonly_onetoone_backwards_ref` (5156), `AdminFieldExtractionMixin` (82); custom-site tests at 1447-1510 using `admin2`/`admin3`. Custom site defined in `tests/admin_views/customadmin.py`, routed at `tests/admin_views/urls.py:17,19`. Readonly FK fixtures: `tests/admin_views/admin.py:426,479`. `tests/admin_utils/test_logentry.py:159` covers LogEntry only.

**Docs:** `docs/ref/contrib/admin/index.txt` (custom AdminSite, `current_app` usage) — not yet reviewed.

**Conclusion:** The reporter's patch is correct and side-effect free; pass `current_app=self.model_admin.admin_site.name` at `helpers.py:212`, preserving the `NoReverseMatch` fallback. No regression test added yet — add one under `ReadonlyTest` exercising a readonly FK through `customadmin`/`admin2`.
