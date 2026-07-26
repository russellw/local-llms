import sys

from solution import insert_position

fails = []


class Probe:
    """Indexable-only sequence that counts accesses and forbids iteration."""

    def __init__(self, data):
        self._data = list(data)
        self.reads = 0

    def __len__(self):
        return len(self._data)

    def __getitem__(self, i):
        if not isinstance(i, int):
            raise TypeError("slicing is not supported by this sequence")
        self.reads += 1
        if i < 0:
            i += len(self._data)
        if not 0 <= i < len(self._data):
            raise IndexError(i)
        return self._data[i]

    def __iter__(self):
        raise TypeError("iterating this sequence is not supported")


def check(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")


data = [1, 3, 3, 3, 5, 7, 7, 9]
for i, side, want in [
    (0, "left", 0), (0, "right", 0),
    (1, "left", 0), (1, "right", 1),
    (2, "left", 1), (2, "right", 1),
    (3, "left", 1), (3, "right", 4),
    (4, "left", 4), (4, "right", 4),
    (7, "left", 5), (7, "right", 7),
    (9, "left", 7), (9, "right", 8),
    (99, "left", 8), (99, "right", 8),
]:
    check(f"{i} {side}", insert_position(Probe(data), i, side), want)

check("default side is left", insert_position(Probe(data), 3), 1)
check("empty left", insert_position(Probe([]), 5, "left"), 0)
check("empty right", insert_position(Probe([]), 5, "right"), 0)
check("all equal left", insert_position(Probe([2] * 10), 2, "left"), 0)
check("all equal right", insert_position(Probe([2] * 10), 2, "right"), 10)
check("floats", insert_position(Probe([0.5, 1.5, 2.5]), 1.5, "right"), 2)
check("strings", insert_position(Probe(["a", "c", "e"]), "d", "left"), 2)

try:
    insert_position(Probe(data), 3, "middle")
    fails.append("bad side: no exception, want ValueError")
except ValueError:
    pass
except Exception as e:
    fails.append(f"bad side: raised {type(e).__name__}, want ValueError")

big = Probe(list(range(1_000_000)))
got = insert_position(big, 499_999, "left")
check("large value", got, 499_999)
if big.reads > 64:
    fails.append(f"not O(log n): {big.reads} index reads on a 1e6 sequence (max 64)")

if fails:
    print("\n".join(fails[:12]))
    sys.exit(1)
print("ok")
