# Handoff: `floatformat` should ignore `USE_L10N` and support forced unlocalized output

## Issue
`{% localize on/off %}` has no effect on `floatformat` because the filter calls `formats.number_format()` without a `use_l10n` argument, so it always falls back to `settings.USE_L10N`. The desired behavior is to make `floatformat` always use the active locale (independent of `USE_L10N`) and add a `u` suffix to force unlocalized output.

## Key files
- `django/template/defaultfilters.py:95-163` — `floatformat`; both `formats.number_format()` calls (~144 and ~163) are the bug sites. This is where the fix goes.
- `django/utils/formats.py:164-201` — `number_format()` / `localize()` already accept `use_l10n`; no change needed but confirms the parameter exists.
- `django/templatetags/l10n.py:1-50` — `localize`/`unlocalize` filters and `LocalizeNode`, which sets `context.use_l10n`. Confirms context carries the flag.
- `django/template/base.py:990-1030` — `VariableNode.render` / `FilterExpression.resolve`: filters receive no context, which is why the `u` suffix approach is needed.
- `django/template/context.py:127-135` — `Context.use_l10n`.

## Tests and docs
- `tests/template_tests/filter_tests/test_floatformat.py` — add the `u` suffix regression test here.
- `tests/i18n/tests.py:516-535, 630-636` — existing `floatformat` localization expectations must change since `USE_L10N=False` will no longer suppress localization.
- `docs/ref/templates/builtins.txt:1677-1760` — document the `u` suffix.
- `docs/releases/4.0.txt:349` — Templates section entry (`...` placeholder).
- `docs/ref/settings.txt:2772+` — `USE_L10N` docs.

## Ruled out
Passing context into filters: filters have no context access and adding a context-passing mechanism to the template engine is too invasive. Also ruled out altering `formats.number_format` semantics.

## Conclusion
Fix `floatformat` in `defaultfilters.py` to always localize with the active locale regardless of `USE_L10N`, and parse a trailing `u` suffix to force unlocalized output; update the i18n test expectations accordingly.
