# Handoff: empty `extra_tags` lost on message serialization

## Issue
`MessageEncoder` in `django/contrib/messages/storage/cookie.py` appends `extra_tags` only when truthy, so `extra_tags=""` is dropped during encoding. `MessageDecoder.process_messages` then rebuilds via `Message(*obj[2:])`, and the missing argument defaults to `None`. Round-tripping through cookie/session storage turns `""` into `None`, breaking templates like `{% if x not in message.extra_tags %}`.

## Files and lines
- `django/contrib/messages/storage/cookie.py`
  - `MessageEncoder.default`, lines ~17–24: the buggy guard `if obj.extra_tags:` (line ~21). Should be `if obj.extra_tags is not None:` so empty strings are serialized.
  - `MessageDecoder.process_messages`, lines ~29–40: `return Message(*obj[2:])` (line ~34) is fine; once the empty string is encoded, it is passed through as the 4th element.
- `django/contrib/messages/storage/base.py`
  - `Message.__init__` lines 12–16 and `_prepare` lines 18–24: already distinguish `None` from `""` (`str(...) if ... is not None else None`), so no change needed here.
- `django/contrib/messages/storage/session.py`: reuses `MessageEncoder`/`MessageDecoder` for `serialize_messages`/`deserialize_messages`, so the single fix covers both backends.

## Tests
- `tests/messages_tests/test_cookie.py`: `test_json_encoder_decoder` (lines ~147–164) is the natural place for a regression test asserting `extra_tags=""` survives encode/decode.
- `tests/messages_tests/test_session.py`: lines ~17–23 exercise serialize/deserialize round-trips.
- `tests/messages_tests/base.py` covers storage behaviour with `extra_tags='tag'`/`None`, but not `""`.

## Docs
`docs/ref/contrib/messages.txt` (storage/serialization and `extra_tags` semantics) — no doc change strictly required, but worth confirming wording.

## Ruled out
- `Message._prepare` / `Message.__eq__` in `base.py`: `_prepare` is correct; `__eq__` ignoring `extra_tags` is pre-existing and unrelated.
- `MessageDecoder`: correctly reconstructs from the list; the loss happens only at encode time.

## Conclusion
Change the truthiness check to an explicit `is not None` test in `MessageEncoder.default` (`cookie.py` ~line 21) and add a regression test covering `extra_tags=""` through both cookie and session storage.
