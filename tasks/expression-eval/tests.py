import math
import sys

from solution import evaluate

fails = []


def check(name, expr, want):
    try:
        got = evaluate(expr)
    except Exception as e:
        fails.append(f"{name} {expr!r}: raised {type(e).__name__}: {e}, want {want!r}")
        return
    if not isinstance(got, float):
        fails.append(f"{name} {expr!r}: got {type(got).__name__}, want float")
        return
    if not math.isclose(got, want, rel_tol=1e-9, abs_tol=1e-12):
        fails.append(f"{name} {expr!r}: got {got!r}, want {want!r}")


def check_raises(name, expr, exc):
    try:
        got = evaluate(expr)
    except exc:
        return
    except Exception as e:
        fails.append(f"{name} {expr!r}: raised {type(e).__name__}, want {exc.__name__}")
        return
    fails.append(f"{name} {expr!r}: returned {got!r}, want {exc.__name__}")


check("int", "42", 42.0)
check("decimal", "3.5", 3.5)
check("leading dot", ".5", 0.5)
check("trailing dot", "10.", 10.0)
check("add", "1+2", 3.0)
check("sub", "10-3", 7.0)
check("mul", "6*7", 42.0)
check("div", "7/2", 3.5)
check("mod", "7%3", 1.0)
check("mod negative", "-7%3", 2.0)

check("precedence mul over add", "2+3*4", 14.0)
check("precedence div over sub", "10-6/2", 7.0)
check("left assoc sub", "10-3-2", 5.0)
check("left assoc div", "100/5/2", 10.0)
check("left assoc mod", "17%10%4", 3.0)

check("parens", "(2+3)*4", 20.0)
check("nested parens", "((1+2)*(3+4))", 21.0)
check("deep parens", "(((((5)))))", 5.0)

check("pow", "2**10", 1024.0)
check("pow right assoc", "2**3**2", 512.0)
check("pow over mul", "2*3**2", 18.0)
check("pow binds tighter than unary", "-2**2", -4.0)
check("unary in parens", "(-2)**2", 4.0)

check("unary minus", "-5", -5.0)
check("unary plus", "+5", 5.0)
check("double negative", "--3", 3.0)
check("triple negative", "---3", -3.0)
check("unary tighter than mul", "-2*3", -6.0)
check("unary after operator", "2*-3", -6.0)
check("unary after paren", "(-3)", -3.0)
check("subtract negative", "5--3", 8.0)

check("whitespace", "  2   +   3 * 4  ", 14.0)
check("tabs and newlines", "1\t+\n2", 3.0)
check("no whitespace", "1+2*3-4/2", 5.0)
check("float mix", "1.5*2+0.25", 3.25)
check("big", "((2+3)**2 - 5) % 7 + 1.5", 7.5)  # 20 % 7 == 6

check_raises("div zero", "1/0", ZeroDivisionError)
check_raises("mod zero", "1%0", ZeroDivisionError)
check_raises("nested div zero", "1/(3-3)", ZeroDivisionError)

check_raises("empty", "", ValueError)
check_raises("whitespace only", "   ", ValueError)
check_raises("unbalanced open", "(1+2", ValueError)
check_raises("unbalanced close", "1+2)", ValueError)
check_raises("empty parens", "()", ValueError)
check_raises("missing operand", "1+", ValueError)
check_raises("leading operator", "*2", ValueError)
check_raises("two numbers", "1 2", ValueError)
check_raises("double operator", "1++*2", ValueError)
check_raises("unknown char", "1 $ 2", ValueError)
check_raises("letters", "2*x", ValueError)
check_raises("stray dot", "1 . 2", ValueError)

if fails:
    print("\n".join(fails[:12]))
    sys.exit(1)
print("ok")
