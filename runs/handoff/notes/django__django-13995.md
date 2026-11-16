## Handoff: admindocs omits `@cached_property`

**Issue:** The admindocs model detail page lists fields, properties, and methods, but attributes decorated with `@cached_property` are silently omitted.

**Root cause / files:**
- `django/contrib/admindocs/views.py`, `ModelDetailView.get_context_data`, lines ~250–272. The method-gathering loop iterates `model.__dict__.items()` and only accepts an entry when line 253's test `inspect.isfunction(func) or isinstance(func, property)` passes. A `cached_property` instance is neither a plain function nor a `property` subclass, so it is skipped before the property branch at lines 266–271 that appends to `fields`.
- `django/utils/functional.py`, line 7 (`class cached_property`) and its `__set_name__`/`__get__` (lines ~22–44): it is a descriptor, confirming `isinstance(..., property)` cannot match.
- `get_return_data_type` at views.py ~356–363 is used for the displayed data type; reuse it.
- No template change needed: `templates/admin_doc/model_detail.html` already renders the `fields` list.

**Tests/models:**
- `tests/admin_docs/models.py` lines 55–57 define `a_property` (`@property`). Add an analogous `@cached_property` attribute here.
- `tests/admin_docs/test_views.py` lines 231–233 (`test_instance_of_property_methods_are_displayed`) assert `<td>a_property</td>`; mirror this for the cached property. `test_method_excludes` (~line 190) covers `MODEL_METHODS_EXCLUDE` and is unaffected.

**Docs:** `docs/ref/contrib/admin/admindocs.txt` (models section) promises "properties, properties, and methods"; update wording if broader descriptor support is added.

**Ruled out:** `inspect.isfunction` cannot catch descriptors; the existing `property` check is too narrow; the exclude-prefix logic and template are not at fault. Broader "all descriptors" support was not implemented—scope limited to `cached_property`.

**Conclusion:** Import `cached_property` from `django.utils.functional` in views.py and extend line 253's condition (e.g. `isinstance(func, (property, cached_property))`), routing it through the existing field-display branch, plus a model attribute and test.
