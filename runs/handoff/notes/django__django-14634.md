## Handoff note

Issue: add a mixin that shows a success message after successful object deletion.

Relevant code:
- `django/contrib/messages/views.py:4-17` — `SuccessMessageMixin` only hooks `form_valid()`, calls `get_success_message(form.cleaned_data)`, and sends `messages.success()`. This is the natural place to extend.
- `django/views/generic/edit.py:206-225` — `DeletionMixin.delete()` and `get_success_url()`; deletion does not pass through `form_valid()`, so the existing mixin never runs for `DeleteView`.
- `django/views/generic/edit.py:228-236` — `BaseDeleteView` / `DeleteView`; these inherit `DeletionMixin`, confirming the missing hook.

Tests/docs:
- `tests/messages_tests/test_mixins.py` currently tests only `ContactFormViewWithMsg` form submission.
- `tests/messages_tests/urls.py` defines that form view; a delete-view URL would need adding.
- `tests/generic_views/test_edit.py` and `tests/generic_views/views.py:173-184` (`NaiveAuthorDelete`, `AuthorDelete`) cover delete-view behavior but not messages.
- `docs/ref/contrib/messages.txt:356-395` documents `SuccessMessageMixin`; update for deletion.
- `docs/ref/class-based-views/mixins-editing.txt:228-244` documents `DeletionMixin.delete()`.
- `docs/ref/class-based-views/generic-editing.txt:16` references `SuccessMessageMixin`.

Ruled out:
- Admin already has its own delete success messaging (`django/contrib/admin/options.py:1451`, `actions.py:46`); not reusable here.
- Message storage/cookie code is unrelated.
- No existing contrib-messages delete-success behavior exists.

Conclusion: `SuccessMessageMixin` cannot currently message on `DeleteView` because deletion bypasses `form_valid()`. Add deletion support, likely a `delete()` override in `SuccessMessageMixin` that calls `super().delete()` then sends `messages.success()` using `success_message`/object context, plus message-mixin tests with a `DeleteView` URL and docs updates.
