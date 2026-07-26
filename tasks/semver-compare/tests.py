import sys

from solution import compare

fails = []


def check(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")


def lt(a, b):
    """a must sort strictly before b, in both directions."""
    check(f"{a} < {b}", compare(a, b), -1)
    check(f"{b} > {a}", compare(b, a), 1)


def eq(a, b):
    check(f"{a} == {b}", compare(a, b), 0)
    check(f"{b} == {a}", compare(b, a), 0)


# core numeric precedence
eq("1.0.0", "1.0.0")
lt("1.0.0", "2.0.0")
lt("2.0.0", "2.1.0")
lt("2.1.0", "2.1.1")
lt("1.9.0", "1.10.0")
lt("1.0.9", "1.0.10")
lt("0.0.1", "0.1.0")
lt("1.0.0", "10.0.0")

# build metadata is ignored
eq("1.0.0+build.1", "1.0.0")
eq("1.0.0+build.1", "1.0.0+build.999")
eq("1.0.0-alpha+a", "1.0.0-alpha+b")
lt("1.0.0-alpha+zzz", "1.0.0+aaa")

# prerelease is lower than the release
lt("1.0.0-alpha", "1.0.0")
lt("1.0.0-rc.1", "1.0.0")
lt("1.0.0-alpha", "1.0.1")

# the canonical spec ordering
order = [
    "1.0.0-alpha",
    "1.0.0-alpha.1",
    "1.0.0-alpha.beta",
    "1.0.0-beta",
    "1.0.0-beta.2",
    "1.0.0-beta.11",
    "1.0.0-rc.1",
    "1.0.0",
]
for i in range(len(order) - 1):
    lt(order[i], order[i + 1])
for i in range(len(order)):
    for j in range(i + 2, len(order)):
        check(f"transitive {order[i]} < {order[j]}", compare(order[i], order[j]), -1)

# numeric identifiers compare numerically, not as strings
lt("1.0.0-2", "1.0.0-11")
lt("1.0.0-alpha.2", "1.0.0-alpha.11")

# numeric identifiers sort below alphanumeric ones
lt("1.0.0-1", "1.0.0-alpha")
lt("1.0.0-999", "1.0.0-a")
lt("1.0.0-alpha.1", "1.0.0-alpha.a")

# ASCII order for non-numeric identifiers, and hyphens count as non-numeric
lt("1.0.0-Alpha", "1.0.0-alpha")
lt("1.0.0-alpha", "1.0.0-alpha-1")
lt("1.0.0-1", "1.0.0-1a")

# a longer identifier list wins when the common prefix is equal
lt("1.0.0-alpha", "1.0.0-alpha.0")
lt("1.0.0-1.2", "1.0.0-1.2.3")
eq("1.0.0-a.b.c", "1.0.0-a.b.c")

# sorting a shuffled list must reproduce the canonical order
import functools
import random

shuffled = list(order)
random.seed(3)
random.shuffle(shuffled)
check("sorted", sorted(shuffled, key=functools.cmp_to_key(compare)), order)

# zeros are legal, leading zeros are not
eq("0.0.0", "0.0.0")
lt("0.0.0", "0.0.1")

for bad in [
    "1.0",
    "1",
    "",
    "1.0.0.0",
    "a.b.c",
    "1.0.x",
    "01.0.0",
    "1.01.0",
    "1.0.01",
    "1.0.0-",
    "1.0.0-alpha..1",
    "1.0.0-.alpha",
    "1.0.0-01",
    "1.0.0-alpha.01",
    "-1.0.0",
    "1.-1.0",
]:
    try:
        got = compare(bad, "1.0.0")
        fails.append(f"invalid {bad!r}: returned {got!r}, want ValueError")
    except ValueError:
        pass
    except Exception as e:
        fails.append(f"invalid {bad!r}: raised {type(e).__name__}, want ValueError")

if fails:
    print("\n".join(fails[:12]))
    sys.exit(1)
print("ok")
