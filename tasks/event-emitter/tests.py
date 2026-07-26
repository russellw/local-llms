import sys

from solution import EventEmitter

fails = []


def check(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")


# --- basic on/emit ---------------------------------------------------------
e = EventEmitter()
seen = []
e.on("tick", lambda *a: seen.append(a))
check("emit count", e.emit("tick", 1, 2), 1)
check("args passed", seen, [(1, 2)])
check("emit again", e.emit("tick"), 1)
check("no-arg call", seen[-1], ())
check("unknown event", e.emit("nope"), 0)
check("listener_count", e.listener_count("tick"), 1)
check("listener_count unknown", e.listener_count("nope"), 0)

# --- ordering and duplicate registration ------------------------------------
e2 = EventEmitter()
order = []
h1 = lambda: order.append("h1")
h2 = lambda: order.append("h2")
e2.on("x", h1)
e2.on("x", h2)
e2.on("x", h1)
check("dup count", e2.listener_count("x"), 3)
check("emit dup", e2.emit("x"), 3)
check("order", order, ["h1", "h2", "h1"])

# off removes only one registration
e2.off("x", h1)
order.clear()
e2.emit("x")
check("after off order", order, ["h2", "h1"])
check("after off count", e2.listener_count("x"), 2)

# off on unknown handler / event is a no-op
e2.off("x", lambda: None)
e2.off("ghost", h1)
check("noop off count", e2.listener_count("x"), 2)

# --- once -------------------------------------------------------------------
e3 = EventEmitter()
hits = []
e3.once("boom", lambda: hits.append(1))
check("once counted", e3.listener_count("boom"), 1)
check("once first emit", e3.emit("boom"), 1)
check("once removed", e3.listener_count("boom"), 0)
check("once second emit", e3.emit("boom"), 0)
check("once ran once", hits, [1])

# a once handler that re-emits must not recurse
e4 = EventEmitter()
depth = []


def reentrant():
    depth.append(1)
    e4.emit("r")


e4.once("r", reentrant)
e4.emit("r")
check("no recursion", depth, [1])

# --- mixed on + once --------------------------------------------------------
e5 = EventEmitter()
log = []
e5.on("m", lambda: log.append("persist"))
e5.once("m", lambda: log.append("single"))
check("mixed count", e5.listener_count("m"), 2)
check("mixed emit 1", e5.emit("m"), 2)
check("mixed emit 2", e5.emit("m"), 1)
check("mixed log", log, ["persist", "single", "persist"])

# --- snapshot semantics -----------------------------------------------------
e6 = EventEmitter()
calls = []


def adds_more():
    calls.append("first")
    e6.on("s", lambda: calls.append("added-during-emit"))


e6.on("s", adds_more)
check("snapshot emit count", e6.emit("s"), 1)
check("snapshot calls", calls, ["first"])
check("added handler registered", e6.listener_count("s"), 2)
calls.clear()
e6.emit("s")
check("added fires next time", calls, ["first", "added-during-emit"])

# a handler removed during emit still does not fire in that emit
e7 = EventEmitter()
fired = []
victim = lambda: fired.append("victim")


def remover():
    fired.append("remover")
    e7.off("d", victim)


e7.on("d", remover)
e7.on("d", victim)
check("remove-during-emit count", e7.emit("d"), 2)
check("remove-during-emit calls", fired, ["remover", "victim"])
check("victim gone after", e7.listener_count("d"), 1)

# --- exceptions -------------------------------------------------------------
e8 = EventEmitter()
survived = []


def boom():
    raise RuntimeError("handler exploded")


e8.on("z", boom)
e8.on("z", lambda: survived.append("after"))
try:
    n = e8.emit("z")
except Exception as exc:
    fails.append(f"emit propagated {type(exc).__name__}, want it swallowed")
    n = -1
check("raising handler counted", n, 2)
check("later handler still ran", survived, ["after"])

# --- event isolation --------------------------------------------------------
e9 = EventEmitter()
a_hits, b_hits = [], []
e9.on("a", lambda: a_hits.append(1))
e9.on("b", lambda: b_hits.append(1))
e9.emit("a")
check("isolation a", (len(a_hits), len(b_hits)), (1, 0))
e9.off("a", lambda: None)
e9.emit("b")
check("isolation b", (len(a_hits), len(b_hits)), (1, 1))

if fails:
    print("\n".join(fails[:12]))
    sys.exit(1)
print("ok")
