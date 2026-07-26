Write a function:

```python
def compare(a: str, b: str) -> int
```

that compares two Semantic Versioning 2.0.0 version strings and returns `-1` if
`a` sorts before `b`, `1` if `a` sorts after `b`, and `0` if they have equal
precedence.

A version looks like `MAJOR.MINOR.PATCH`, optionally followed by `-PRERELEASE`
and/or `+BUILD`, e.g. `1.0.0`, `1.0.0-alpha.1`, `1.0.0+20130313`,
`1.0.0-beta.2+exp.sha.5114f85`.

Precedence rules:

1. Compare `MAJOR`, then `MINOR`, then `PATCH` numerically.
2. Build metadata (everything after `+`) is **ignored** entirely — two versions
   differing only in build metadata have equal precedence.
3. A version *with* a prerelease has **lower** precedence than the same version
   without one: `1.0.0-alpha` < `1.0.0`.
4. When both have a prerelease, compare the dot-separated identifiers left to
   right:
   - An identifier made only of digits is compared numerically, and always
     sorts **lower** than an identifier containing a letter or hyphen.
   - Two non-numeric identifiers are compared by ASCII order.
   - If all identifiers so far are equal, the version with **more** identifiers
     has higher precedence: `1.0.0-alpha` < `1.0.0-alpha.1`.

So the canonical ordering is:
`1.0.0-alpha` < `1.0.0-alpha.1` < `1.0.0-alpha.beta` < `1.0.0-beta` <
`1.0.0-beta.2` < `1.0.0-beta.11` < `1.0.0-rc.1` < `1.0.0`

Raise `ValueError` for a string that is not a valid version: a missing
component, a non-numeric or leading-zero major/minor/patch, an empty prerelease
identifier, or a prerelease numeric identifier with a leading zero.
