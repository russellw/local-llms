import sys

from solution import parse_csv

fails = []


def check(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")


check("empty input", parse_csv(""), [])
check("one field", parse_csv("a"), [["a"]])
check("simple row", parse_csv("a,b,c"), [["a", "b", "c"]])
check("two rows", parse_csv("a,b\nc,d"), [["a", "b"], ["c", "d"]])
check("trailing newline", parse_csv("a,b\n"), [["a", "b"]])
check("crlf", parse_csv("a,b\r\nc,d\r\n"), [["a", "b"], ["c", "d"]])
check("bare cr", parse_csv("a,b\rc,d"), [["a", "b"], ["c", "d"]])

check("empty fields", parse_csv("a,,b"), [["a", "", "b"]])
check("leading empty", parse_csv(",a"), [["", "a"]])
check("trailing empty", parse_csv("a,"), [["a", ""]])
check("all empty", parse_csv(",,"), [["", "", ""]])
check("blank line in middle", parse_csv("a\n\nb"), [["a"], [""], ["b"]])

check("quoted plain", parse_csv('"a","b"'), [["a", "b"]])
check("quoted comma", parse_csv('"a,b",c'), [["a,b", "c"]])
check("quoted newline", parse_csv('"line1\nline2",x'), [["line1\nline2", "x"]])
check("quoted crlf inside", parse_csv('"a\r\nb"'), [["a\r\nb"]])
check("escaped quote", parse_csv('"he said ""hi"""'), [['he said "hi"']])
check("only escaped quotes", parse_csv('""""'), [['"']])
check("empty quoted field", parse_csv('""'), [[""]])
check("quoted empty among others", parse_csv('a,"",b'), [["a", "", "b"]])

check("quote mid-field is literal", parse_csv('say "hi"'), [['say "hi"']])
check("unquoted internal quote", parse_csv('a"b,c'), [['a"b', "c"]])

check("whitespace kept", parse_csv(" a , b "), [[" a ", " b "]])
check("quoted whitespace", parse_csv('" a ", b'), [[" a ", " b"]])

check(
    "ragged rows",
    parse_csv("a,b,c\nd\ne,f"),
    [["a", "b", "c"], ["d"], ["e", "f"]],
)
check(
    "realistic",
    parse_csv('name,note\r\n"Smith, John","said ""ok""\nthen left"\r\nx,y\r\n'),
    [
        ["name", "note"],
        ["Smith, John", 'said "ok"\nthen left'],
        ["x", "y"],
    ],
)
check("unicode", parse_csv("café,naïve"), [["café", "naïve"]])

rows = parse_csv("a,b")
if not (isinstance(rows, list) and all(isinstance(r, list) for r in rows)):
    fails.append(f"types: expected list of lists, got {rows!r}")

for name, bad in [
    ("unterminated quote", '"abc'),
    ("unterminated after escape", '"abc""'),
    ("unterminated with newline", 'a,"b\nc'),
]:
    try:
        got = parse_csv(bad)
        fails.append(f"{name}: returned {got!r}, want ValueError")
    except ValueError:
        pass
    except Exception as e:
        fails.append(f"{name}: raised {type(e).__name__}, want ValueError")

if fails:
    print("\n".join(fails[:12]))
    sys.exit(1)
print("ok")
