## Handoff note

**Issue:** `ModelAdmin` for a proxy-of-proxy (`SpecialJournalist`) with an inline whose model has an FK to the intermediate proxy superclass (`Journalist`) raises `admin.E202`: `fk_name 'journalist' is not a ForeignKey to 'SpecialJournalist'`.

**Key files/lines**
- `django/forms/models.py:997-1030` — `_get_foreign_key()`. The failing check is around line 1014: it tests `fk.remote_field.model not in parent_model._meta.get_parent_list()`.
- `django/db/models/options.py:629-639` — `Options.get_parent_list()`. It builds ancestors from `self.parents` (`Options.parents` initialized at line 119). For proxy chains, `parents` does not include the intermediate proxy, so `SpecialJournalist._meta.get_parent_list()` returns only `[Reporter]`, omitting `Journalist`.
- `django/db/models/options.py:328-334` — `setup_proxy()` sets `proxy_for_model`/`concrete_model` but does not add proxy superclasses to `parents`.
- `django/contrib/admin/checks.py:1057,1074-1076` — calls `_get_foreign_key()` and converts the resulting `ValueError` into `admin.E202`. The admin check is only surfacing the metadata bug.
- `django/contrib/admin/helpers.py:387` — another `get_parent_list()` consumer; worth considering if changing semantics.

**Tests/docs**
- `tests/model_meta/tests.py:272-276` — existing `ParentListTests.test_get_parent_list()`; best place for a regression test.
- `tests/model_formsets/tests.py` — inline formset/`_get_foreign_key()` coverage.
- `tests/admin_checks/tests.py` — `admin.E202` checks, especially around `test_inline_self_check`.
- `tests/modeladmin/test_checks.py:1080-1130` — related inline check coverage.
- `tests/proxy_models/tests.py:258-259` — existing `proxy_for_model` assertion.
- `tests/admin_inlines/models.py:311-323`, `tests/admin_inlines/admin.py:304-375` — related #30231 proxy-inline coverage, but not this proxy-of-proxy/FK-to-intermediate-proxy case.
- No docs references to `get_parent_list` or proxy-inline `E202` were found under `docs/`.

**Ruled out:** The admin check and `fk_name` selection are not independently wrong; this is not fixed by changing `admin.E202`. #30231-style tests cover inlines registered on a proxy itself, not an FK to an intermediate proxy superclass.

**Conclusion:** Fix `get_parent_list()` (or make `_get_foreign_key()` proxy-aware) so proxy superclasses appear in the ancestor chain. Add regression coverage in `tests/model_meta/tests.py`, with an admin-check test if desired. No files were edited and no tests were run.
