Implement a class `EventEmitter` with exactly these methods:

```python
class EventEmitter:
    def on(self, event: str, handler) -> None
    def once(self, event: str, handler) -> None
    def off(self, event: str, handler) -> None
    def emit(self, event: str, *args) -> int
    def listener_count(self, event: str) -> int
```

Semantics, all of which are tested:

- `on` registers `handler` to be called with `*args` every time `event` is
  emitted. The same handler may be registered more than once for the same
  event, and is then called once per registration.
- `once` registers a handler that fires at most once, then is removed
  automatically before it is called (so a handler that re-emits its own event
  does not recurse).
- `off` removes **one** registration of `handler` for `event` — the earliest
  one still registered. Removing a handler that is not registered, or for an
  event that has none, is a no-op and must not raise.
- `emit` calls the handlers registered for `event` in registration order, and
  returns the number of handlers it called. Emitting an event with no handlers
  returns 0.
- `emit` iterates over a snapshot of the handler list: handlers added or
  removed *during* an emit do not affect that same emit. A `once` handler
  already scheduled in the snapshot still runs.
- If a handler raises an exception, `emit` swallows it, continues calling the
  remaining handlers, and still counts the raising handler in its return value.
- `listener_count` returns the number of registrations currently attached to
  `event`, counting `on` and `once` alike.

Handlers registered for different events never interfere with each other.
