import sys

from solution import rle_encode, rle_decode

fails = []


def check(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")


check("encode basic", rle_encode("aaabbc"), "a3b2c1")
check("encode empty", rle_encode(""), "")
check("encode single", rle_encode("a"), "a1")
check("encode multidigit", rle_encode("a" * 12), "a12")
check("encode alternating", rle_encode("abab"), "a1b1a1b1")
check("encode split runs", rle_encode("aabaa"), "a2b1a2")
check("encode punctuation", rle_encode("  !!\n\n"), " 2!2\n2")
check("encode unicode", rle_encode("ééx"), "é2x1")

check("decode basic", rle_decode("a3b2c1"), "aaabbc")
check("decode empty", rle_decode(""), "")
check("decode multidigit", rle_decode("a12"), "a" * 12)
check("decode big", rle_decode("x105"), "x" * 105)
check("decode space", rle_decode(" 2!2"), "  !!")

for s in [
    "",
    "a",
    "aaaaaaaaaaaaaaaaaaaaa",
    "the quick brown fox   jumps",
    "\n\n\t\t  ",
    "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz",
    "MiXeD CaSe!!!",
]:
    check(f"roundtrip {s[:12]!r}", rle_decode(rle_encode(s)), s)

if fails:
    print("\n".join(fails[:12]))
    sys.exit(1)
print("ok")
