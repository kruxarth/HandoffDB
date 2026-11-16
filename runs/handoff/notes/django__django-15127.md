# Handoff: LEVEL_TAGS not updated by `@override_settings(MESSAGE_TAGS=...)`

## Issue
`Message.level_tag` returns `''` for custom levels added via `@override_settings(MESSAGE_TAGS={...})`, because tags are resolved from a module-level constant snapshotted at import time.

## Key files/lines
- `django/contrib/messages/storage/base.py:4` — `LEVEL_TAGS = utils.get_level_tags()` is evaluated once at import.
- `django/contrib/messages/storage/base.py:41` — `Message.level_tag` reads that stale constant; `tags` (line ~37) depends on it too.
- `django/contrib/messages/utils.py:5-11` — `get_level_tags()` merges `constants.DEFAULT_TAGS` with `settings.MESSAGE_TAGS`; this is the value that *should* be consulted at access time.
- `django/contrib/messages/constants.py` — `DEFAULT_TAGS` source.

## Tests
- `tests/messages_tests/base.py:25-37` — `override_settings_tags`, a custom `override_settings` subclass that manually saves/restores `base.LEVEL_TAGS`. This is a **workaround in test code**, not a fix; it should be removable once the bug is fixed.
- `tests/messages_tests/base.py:371` — uses `override_settings_tags(MESSAGE_TAGS={...})`; the relevant custom-tag test.
- `tests/messages_tests/base.py:157, 177, 203, 227, 253, 346` — other `override_settings(MESSAGE_LEVEL=...)` uses.
- `tests/messages_tests/` suite (test_api, test_cookie, test_session, test_fallback, test_mixins) — all exercise `Message`/storage.

## Docs
`docs/ref/contrib/messages.txt` (MESSAGE_TAGS setting) and `docs/topics/testing/tools.txt` (`override_settings`).

## Ruled out
- `override_settings` machinery itself is fine; the staleness is entirely the module-level constant.
- No issue in storage backends or `get_level_tags()` logic.

## Conclusion
Fix in `django/contrib/messages/storage/base.py`: make `Message.level_tag` (and thus `tags`) call `utils.get_level_tags()` at access time, or otherwise invalidate `LEVEL_TAGS` on `setting_changed`. Remove the `override_settings_tags` workaround in `tests/messages_tests/base.py` and add a regression test using plain `@override_settings(MESSAGE_TAGS=...)`.
