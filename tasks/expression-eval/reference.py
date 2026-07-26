import re

_TOKEN = re.compile(r"\s*(\*\*|[-+*/%()]|\d+\.?\d*|\.\d+|\.)")


def _tokenize(expr: str) -> list[str]:
    tokens = []
    pos = 0
    while pos < len(expr):
        m = _TOKEN.match(expr, pos)
        if not m:
            if expr[pos:].strip() == "":
                break
            raise ValueError(f"unexpected character at {pos}: {expr[pos]!r}")
        tok = m.group(1)
        if tok == ".":
            raise ValueError("stray '.'")
        tokens.append(tok)
        pos = m.end()
    return tokens


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0

    def peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def take(self):
        tok = self.peek()
        if tok is None:
            raise ValueError("unexpected end of expression")
        self.i += 1
        return tok

    def expr(self) -> float:
        value = self.term()
        while self.peek() in ("+", "-"):
            op = self.take()
            rhs = self.term()
            value = value + rhs if op == "+" else value - rhs
        return value

    def term(self) -> float:
        value = self.unary()
        while self.peek() in ("*", "/", "%"):
            op = self.take()
            rhs = self.unary()
            if op == "*":
                value *= rhs
            elif op == "/":
                if rhs == 0:
                    raise ZeroDivisionError("division by zero")
                value /= rhs
            else:
                if rhs == 0:
                    raise ZeroDivisionError("modulo by zero")
                value %= rhs
        return value

    def unary(self) -> float:
        tok = self.peek()
        if tok == "-":
            self.take()
            return -self.unary()
        if tok == "+":
            self.take()
            return self.unary()
        return self.power()

    def power(self) -> float:
        base = self.atom()
        if self.peek() == "**":
            self.take()
            return base ** self.unary()  # right-associative, unary-aware
        return base

    def atom(self) -> float:
        tok = self.take()
        if tok == "(":
            value = self.expr()
            if self.take() != ")":
                raise ValueError("expected ')'")
            return value
        try:
            return float(tok)
        except ValueError:
            raise ValueError(f"expected a number, got {tok!r}") from None


def evaluate(expr: str) -> float:
    tokens = _tokenize(expr)
    if not tokens:
        raise ValueError("empty expression")
    p = _Parser(tokens)
    value = p.expr()
    if p.i != len(tokens):
        raise ValueError(f"unexpected token {tokens[p.i]!r}")
    return float(value)
