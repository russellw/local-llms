import random
import sys

from solution import MinHeap

fails = []


def check(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")


def heap_ok(items):
    """True if the array satisfies the min-heap property."""
    for i in range(len(items)):
        for c in (2 * i + 1, 2 * i + 2):
            if c < len(items) and items[c] < items[i]:
                return False
    return True


h = MinHeap()
check("empty len", len(h), 0)

for v in [5, 3, 8, 1, 9, 2]:
    h.push(v)
    if not heap_ok(h.items):
        fails.append(f"heap property broken after push({v}): {h.items}")
        break

check("len after pushes", len(h), 6)
check("peek", h.peek(), 1)
check("peek does not remove", len(h), 6)

out = [h.pop() for _ in range(6)]
check("sorted drain", out, [1, 2, 3, 5, 8, 9])
check("len after drain", len(h), 0)

# Descending input is the case the original sift-up gets wrong.
h2 = MinHeap()
for v in range(20, 0, -1):
    h2.push(v)
check("descending drain", [h2.pop() for _ in range(20)], list(range(1, 21)))

# Duplicates.
h3 = MinHeap()
for v in [4, 4, 1, 1, 4, 1]:
    h3.push(v)
check("duplicates", [h3.pop() for _ in range(6)], [1, 1, 1, 4, 4, 4])

# Interleaved push/pop against a plain sorted model.
random.seed(7)
h4 = MinHeap()
model = []
for _ in range(400):
    if model and random.random() < 0.4:
        got = h4.pop()
        want = min(model)
        model.remove(want)
        if got != want:
            fails.append(f"interleaved pop: got {got!r}, want {want!r}")
            break
    else:
        v = random.randint(0, 999)
        h4.push(v)
        model.append(v)
    if len(h4) != len(model):
        fails.append(f"length drift: heap {len(h4)} vs model {len(model)}")
        break
    if not heap_ok(h4.items):
        fails.append(f"heap property broken during interleave: {h4.items[:20]}")
        break

# Strings, to confirm nothing assumes numbers.
h5 = MinHeap()
for w in ["pear", "apple", "fig", "date"]:
    h5.push(w)
check("strings", [h5.pop() for _ in range(4)], ["apple", "date", "fig", "pear"])

for name, fn in (("pop", lambda: MinHeap().pop()), ("peek", lambda: MinHeap().peek())):
    try:
        fn()
        fails.append(f"empty {name}: no exception, want IndexError")
    except IndexError:
        pass
    except Exception as e:
        fails.append(f"empty {name}: raised {type(e).__name__}, want IndexError")

if fails:
    print("\n".join(fails[:12]))
    sys.exit(1)
print("ok")
