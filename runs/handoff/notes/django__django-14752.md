## Handoff: AutocompleteJsonView extra result fields

**Issue:** `AutocompleteJsonView.get()` builds autocomplete result dicts inline, forcing subclasses to override the whole `get()` method to add fields. Add a `serialize_result()` extension point.

**Key code:** `django/contrib/admin/views/autocomplete.py`
- `AutocompleteJsonView.get()` at lines 11–32.
- Result dict construction is inline at lines 26–31 inside `JsonResponse`.
- Replace the list comprehension with `self.serialize_result(obj, to_field_name)`.
- Add `serialize_result(self, obj, to_field_name)` returning `{'id': str(getattr(obj, to_field_name)), 'text': str(obj)}` after `get()`.
- Leave pagination, permissions, `process_request()`, `get_queryset()`, and `get_paginator()` unchanged.

**Tests:** `tests/admin_views/test_autocomplete_view.py`
- `AutocompleteJsonViewTests` spans lines 64–296.
- Existing success/response assertions start at `test_success` line 82; custom to-field tests lines 94–174.
- Add a test subclass overriding `serialize_result()` and assert extra keys appear in `response.json()['results']`.

**Docs:** Related admin autocomplete documentation is in `docs/ref/contrib/admin/index.txt`; document the new override hook if behavior is public.

**Ruled out:** Overriding `get()` is unnecessary and fragile. No changes needed in `django/contrib/admin/sites.py` or `django/contrib/admin/widgets.py`; they only reference/route the view. Queryset, permission, pagination, and search behavior should not change.

**Conclusion:** Implement the small `serialize_result()` refactor in `autocomplete.py` and cover it with a regression test in `test_autocomplete_view.py`.
