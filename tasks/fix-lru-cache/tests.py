import sys

from solution import LRUCache

fails = []


def check(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")


c = LRUCache(2)
c.put("a", 1)
c.put("b", 2)
check("get a", c.get("a"), 1)
check("get b", c.get("b"), 2)
check("len", len(c), 2)
check("missing", c.get("zz"), None)
check("missing default", c.get("zz", "x"), "x")

# Read 'a' again so that 'b' becomes the least recently used entry.
check("touch a", c.get("a"), 1)
c.put("c", 3)
check("evicted b", c.get("b"), None)
check("kept a", c.get("a"), 1)
check("kept c", c.get("c"), 3)
check("len after evict", len(c), 2)

# Updating an existing key must not evict or grow.
c2 = LRUCache(2)
c2.put("a", 1)
c2.put("b", 2)
c2.put("a", 99)
check("update value", c2.get("a"), 99)
check("update kept b", c2.get("b"), 2)
check("update len", len(c2), 2)

# put() also refreshes recency.
c3 = LRUCache(2)
c3.put("a", 1)
c3.put("b", 2)
c3.put("a", 10)   # a is now most recent
c3.put("c", 3)    # should evict b
check("put refreshes recency", c3.get("b"), None)
check("put refreshes kept a", c3.get("a"), 10)

# Missing-key lookups must not disturb recency.
c4 = LRUCache(2)
c4.put("a", 1)
c4.put("b", 2)
c4.get("nope")
c4.put("c", 3)
check("miss does not save a", c4.get("a"), None)
check("miss kept b", c4.get("b"), 2)

c5 = LRUCache(1)
c5.put("a", 1)
c5.put("b", 2)
check("cap 1 evicts", c5.get("a"), None)
check("cap 1 holds", c5.get("b"), 2)
check("cap 1 len", len(c5), 1)

big = LRUCache(3)
for i in range(100):
    big.put(f"k{i}", i)
    if len(big) > 3:
        fails.append(f"capacity exceeded at i={i}: len={len(big)}")
        break
check("last three", [big.get(f"k{i}") for i in (97, 98, 99)], [97, 98, 99])

for bad in (0, -1):
    try:
        LRUCache(bad)
        fails.append(f"LRUCache({bad}): no exception, want ValueError")
    except ValueError:
        pass
    except Exception as e:
        fails.append(f"LRUCache({bad}): raised {type(e).__name__}, want ValueError")

if fails:
    print("\n".join(fails[:12]))
    sys.exit(1)
print("ok")
