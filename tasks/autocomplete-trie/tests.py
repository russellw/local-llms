import sys

from solution import Autocomplete

fails = []


def check(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")


a = Autocomplete()
check("empty len", len(a), 0)
check("empty suggest", a.suggest("x"), [])

for word, w in [
    ("cat", 10),
    ("car", 8),
    ("card", 12),
    ("care", 8),
    ("careful", 3),
    ("dog", 20),
    ("do", 1),
]:
    a.add(word, w)

check("len", len(a), 7)
check("prefix car", a.suggest("car", 3), ["card", "car", "care"])
check("prefix ca", a.suggest("ca", 2), ["card", "cat"])
check("word is own prefix", a.suggest("cat"), ["cat"])
check("prefix d", a.suggest("d", 5), ["dog", "do"])
check("no match", a.suggest("zebra"), [])
check("empty prefix", a.suggest("", 3), ["dog", "card", "cat"])
check("k larger than matches", a.suggest("dog", 99), ["dog"])
check("k zero", a.suggest("car", 0), [])
check("k negative", a.suggest("car", -1), [])

# equal weights break ties lexicographically
check("tie break", a.suggest("care", 5), ["care", "careful"])

# re-adding replaces the weight instead of duplicating
a.add("car", 99)
check("len after replace", len(a), 7)
check("replaced weight wins", a.suggest("car", 1), ["car"])

# default weight
b = Autocomplete()
b.add("alpha")
b.add("beta")
check("default weight ties", b.suggest("", 5), ["alpha", "beta"])
check("empty string is noop", (b.add(""), len(b))[1], 2)

# case sensitivity
c = Autocomplete()
c.add("Apple", 5)
c.add("apple", 5)
check("case sensitive", c.suggest("A"), ["Apple"])
check("case sensitive both", c.suggest("", 5), ["Apple", "apple"])

# unicode and shared prefixes
d = Autocomplete()
for w, wt in [("naïve", 2), ("naïveté", 1), ("nap", 3)]:
    d.add(w, wt)
check("unicode prefix", d.suggest("na", 3), ["nap", "naïve", "naïveté"])
check("unicode deep", d.suggest("naïve", 2), ["naïve", "naïveté"])

# scale: a rare prefix in a big dictionary must stay cheap
big = Autocomplete()
for i in range(20000):
    big.add(f"common{i:05d}", i % 100)
big.add("zzrare", 1)
big.add("zzrarest", 2)
check("big len", len(big), 20002)
check("rare prefix", big.suggest("zzrare", 5), ["zzrarest", "zzrare"])
check("deep prefix count", len(big.suggest("common0000", 20)), 10)

if fails:
    print("\n".join(fails[:12]))
    sys.exit(1)
print("ok")
