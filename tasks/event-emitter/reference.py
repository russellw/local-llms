class EventEmitter:
    def __init__(self):
        # event -> list of (handler, is_once) registrations, in order
        self._handlers = {}

    def on(self, event: str, handler) -> None:
        self._handlers.setdefault(event, []).append([handler, False])

    def once(self, event: str, handler) -> None:
        self._handlers.setdefault(event, []).append([handler, True])

    def off(self, event: str, handler) -> None:
        regs = self._handlers.get(event)
        if not regs:
            return
        for i, (h, _) in enumerate(regs):
            if h == handler:
                del regs[i]
                return

    def emit(self, event: str, *args) -> int:
        regs = self._handlers.get(event)
        if not regs:
            return 0
        snapshot = list(regs)
        for reg in snapshot:
            handler, is_once = reg
            if is_once:
                try:
                    regs.remove(reg)
                except ValueError:
                    pass
            try:
                handler(*args)
            except Exception:
                pass
        return len(snapshot)

    def listener_count(self, event: str) -> int:
        return len(self._handlers.get(event, []))
