## Handoff note

**Issue:** `django.utils.safestring.mark_safe()` eagerly evaluates lazy translation objects (`ugettext_lazy`/`lazystr`), so a `mark_safe(_("username"))` captured before `activate("fr")` renders the original language instead of the active translation.

**Key code:** `django/utils/safestring.py:56-68` defines `mark_safe()`. The non-callable/non-`__html__` path returns `SafeString(s)`, which forces `Promise.__str__`. `SafeText` is only a backward-compatible alias at line 45; `SafeBytes` is gone (removed since Django 2.0), so the old bytes/text type ambiguity from the report no longer applies directly. `django/utils/functional.py:226-257` defines `keep_lazy()`/`keep_lazy_text()`, the existing mechanism for preserving lazy results; `escape()` in `django/utils/html.py:20` is a nearby example using `@keep_lazy(SafeString)`.

**Tests:** `tests/utils_tests/test_safestring.py:42-46` (`test_mark_safe_lazy`) only checks the result is `SafeData` and renders once, so it misses later locale activation. Lines 60-61 check `__html__()` on a lazy result. Lines 94-103 (`test_mark_safe_decorator_does_not_affect_promises`) are the closest regression coverage for lazy `Promise` objects.

**Docs:** `docs/ref/utils.txt:764` documents `mark_safe`; `docs/topics/i18n/translation.txt:495-525` covers lazy translation behavior; `docs/howto/custom-template-tags.txt:275,297-309,441-443` references `mark_safe`.

**Ruled out:** a `SafeBytes`-specific fix, since that class no longer exists; and naïvely wrapping with `allow_lazy` without preserving `SafeData`/`SafeString` semantics. The callable-decorator and `__html__` passthrough paths at `safestring.py:66-68` already behave correctly.

**Conclusion:** bug is valid. Fix `mark_safe()` so non-callable lazy `Promise` inputs are not coerced immediately—likely special-case `Promise` or use `keep_lazy(SafeString)`—while still returning safe data. Add a regression test that calls `mark_safe()` before `activate()` and renders afterward.
