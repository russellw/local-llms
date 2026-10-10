# Design

`build(graph, sources, store, goal=None)` brings the targets of a graph up to
date and returns a `Report` saying what happened to each of them.

## Targets and sources

A source is a named blob of bytes passed in by the caller in `sources`. A
target is declared on the graph with a name, the names it depends on (targets
or sources), a recipe, and a version. The recipe is called with a dict mapping
each dependency's name to its bytes, and returns the target's own bytes. The
version starts at 1; a recipe's author bumps it to say the recipe has changed.

The store keeps, for each target, the output of its last successful run and
the fingerprint it ran with. A store outlives a build: the same one is passed
to the next build, and that is what lets the next build skip work.

## What a build involves

With no goal, a build involves every target in the graph. With a goal, it
involves the goal and everything the goal depends on, directly or through
other targets, and nothing else.

Before anything runs, the build checks the targets it involves. Every
dependency has to name a declared target or a source, and the dependencies
must not form a cycle. If either check fails, the build raises `BuildError`
without having called any recipe.

## Order

Targets are dealt with in the order they were declared in, except that a target
is never dealt with before its dependencies. Precisely: at each step, the next
target is the earliest-declared one whose dependencies have all been dealt
with. Declared as `a` (which depends on `c`), then `b`, then `c`, the order is
`b`, `c`, `a`: `a` cannot go first, and of the two that can, `b` was declared
earlier.

The order does not depend on which targets turn out to need running.

## Whether a target runs

A target's fingerprint is made from its recipe version and, for each
dependency, the dependency's name and the content hash of its bytes, taken
when the build reaches the target. The order in which the dependencies were
listed does not enter into it. A target runs when the store has no record of
it or when the fingerprint recorded with its last output differs from the one
just computed. Otherwise it is up to date, and its stored output stands.

A fingerprint describes what a target's inputs contain, not how they came to
contain it. A dependency that ran again but produced the same bytes as before
leaves the targets that depend on it up to date.

When a target runs, the store records its new output together with the
fingerprint it ran with.

## Failure

A recipe fails by raising an exception. The target is reported as failed, and
its record in the store is left as it was. Every target that depends on it,
directly or through other targets, is reported as blocked and does not run.
The build carries on with everything else: a target that does not depend on a
failure is dealt with in its usual place in the order, as if nothing had gone
wrong.

A build in which recipes fail still returns its report normally. The checks
described under "What a build involves" are the only reason a build raises.

## The report

`ran`, `up_to_date`, `failed` and `blocked` each list target names in the
order the build dealt with them. Every target the build involves appears in
exactly one of the four.
