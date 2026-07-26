import sys

from solution import topo_sort

fails = []


def check(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")


check("empty", topo_sort({}), [])
check("single", topo_sort({"a": []}), ["a"])
check("no edges sorted", topo_sort({"c": [], "a": [], "b": []}), ["a", "b", "c"])
check("chain", topo_sort({"a": ["b"], "b": ["c"], "c": []}), ["a", "b", "c"])
check(
    "reverse chain",
    topo_sort({"c": [], "b": ["c"], "a": ["b"]}),
    ["a", "b", "c"],
)

# 'z' is ready immediately but 'm' is alphabetically smaller, so 'm' goes first.
check(
    "tie broken alphabetically",
    topo_sort({"m": [], "z": [], "a": ["z"]}),
    ["a", "m", "z"],
)

check(
    "diamond",
    topo_sort({"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []}),
    ["a", "b", "c", "d"],
)

# 'b' must wait for 'a' even though 'b' < 'c'.
check(
    "dependency beats alphabet",
    topo_sort({"a": ["b"], "c": [], "b": []}),
    ["a", "b", "c"],
)

build = {
    "config": ["compile", "docs"],
    "compile": ["link", "test"],
    "link": ["package"],
    "test": ["package"],
    "docs": ["package"],
    "package": [],
}
order = topo_sort(build)
check("build graph length", len(order), 6)
pos = {n: i for i, n in enumerate(order)}
for u, vs in build.items():
    for v in vs:
        if pos.get(u, -1) >= pos.get(v, -1):
            fails.append(f"build graph: {u} not before {v} in {order}")
check("build graph exact", order, ["config", "compile", "docs", "link", "test", "package"])


def check_cycle(name, g):
    try:
        got = topo_sort(g)
    except ValueError:
        return
    except Exception as e:
        fails.append(f"{name}: raised {type(e).__name__}, want ValueError")
        return
    fails.append(f"{name}: returned {got!r}, want ValueError")


check_cycle("self loop", {"a": ["a"]})
check_cycle("two cycle", {"a": ["b"], "b": ["a"]})
check_cycle("three cycle", {"a": ["b"], "b": ["c"], "c": ["a"]})
check_cycle("cycle plus dag", {"x": [], "a": ["b"], "b": ["c"], "c": ["a"]})

if fails:
    print("\n".join(fails[:12]))
    sys.exit(1)
print("ok")
