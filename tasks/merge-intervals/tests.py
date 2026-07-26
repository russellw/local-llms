import sys

from solution import merge_intervals

fails = []


def check(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")


check("empty", merge_intervals([]), [])
check("single", merge_intervals([(1, 5)]), [(1, 5)])
check("disjoint", merge_intervals([(1, 2), (5, 6)]), [(1, 2), (5, 6)])
check("overlap", merge_intervals([(1, 4), (2, 6)]), [(1, 6)])
check("touching", merge_intervals([(1, 3), (3, 5)]), [(1, 5)])
check("adjacent ints", merge_intervals([(1, 3), (4, 6)]), [(1, 6)])
check("gap of one", merge_intervals([(1, 3), (5, 7)]), [(1, 3), (5, 7)])
check("unsorted", merge_intervals([(8, 10), (1, 3), (2, 6)]), [(1, 6), (8, 10)])
check("nested", merge_intervals([(1, 20), (5, 6), (7, 8)]), [(1, 20)])
check("degenerate", merge_intervals([(3, 3), (3, 3)]), [(3, 3)])
check("point joins", merge_intervals([(1, 1), (2, 2), (3, 3)]), [(1, 3)])
check("negatives", merge_intervals([(-5, -3), (-2, 0)]), [(-5, 0)])
check(
    "chain",
    merge_intervals([(1, 2), (2, 3), (3, 4), (10, 11)]),
    [(1, 4), (10, 11)],
)

got = merge_intervals([(1, 4), (2, 6)])
if got and not all(isinstance(x, tuple) for x in got):
    fails.append(f"element type: expected tuples, got {[type(x).__name__ for x in got]}")

original = [(8, 10), (1, 3)]
snapshot = list(original)
merge_intervals(original)
if original != snapshot:
    fails.append(f"input mutated: {original!r} != {snapshot!r}")

if fails:
    print("\n".join(fails[:12]))
    sys.exit(1)
print("ok")
