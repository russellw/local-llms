import sys

from solution import to_roman, from_roman

fails = []


def check(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")


def check_raises(name, fn, *args):
    try:
        got = fn(*args)
    except ValueError:
        return
    except Exception as e:
        fails.append(f"{name}: raised {type(e).__name__}, want ValueError")
        return
    fails.append(f"{name}: returned {got!r}, want ValueError")


known = {
    1: "I",
    3: "III",
    4: "IV",
    9: "IX",
    14: "XIV",
    40: "XL",
    44: "XLIV",
    90: "XC",
    100: "C",
    400: "CD",
    500: "D",
    900: "CM",
    1000: "M",
    1987: "MCMLXXXVII",
    2024: "MMXXIV",
    3888: "MMMDCCCLXXXVIII",
    3999: "MMMCMXCIX",
}
for n, r in known.items():
    check(f"to_roman({n})", to_roman(n), r)
    check(f"from_roman({r!r})", from_roman(r), n)

for n in range(1, 4000):
    r = to_roman(n)
    if from_roman(r) != n:
        fails.append(f"roundtrip failed at {n}: to_roman -> {r!r}")
        break

check_raises("to_roman(0)", to_roman, 0)
check_raises("to_roman(4000)", to_roman, 4000)
check_raises("to_roman(-1)", to_roman, -1)
check_raises("to_roman('5')", to_roman, "5")

if fails:
    print("\n".join(fails[:12]))
    sys.exit(1)
print("ok")
