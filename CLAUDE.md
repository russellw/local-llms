# Working in this repo

## Commit directly to main

**Do not create branches.** All work goes straight to `main`, committed there.
This is a single-maintainer repo with no review step, so a branch is an extra
merge for nothing. If a default instruction elsewhere says to branch before
committing on the default branch, this overrides it.

## Keep selfcheck green

`python3 -m bench selfcheck` is the guard rail for both suites, and CI runs it
on Python 3.11 and 3.13. Run it after touching a task, an episode, the sandbox,
the extractor or the tool-loop scorer.

It checks three things: every task's `reference.py` passes its own `tests.py`;
the harness behaves (extraction, sandbox isolation, timeouts); and the tool-loop
scorer scores its scripted agents correctly, including still rejecting the one
that records a *verified answer to the wrong question*.

## Constraints that are deliberate

- **Standard library only.** No `pip install`, in the harness or in a task. The
  point is that this runs on a bare distro Python.
- **Python 3.11 syntax.** Check with
  `ast.parse(src, feature_version=(3, 11))` rather than assuming.
- **The two suites are never averaged.** They measure different abilities that
  fail in a different order; a combined score describes neither.
- **Results are the record.** The `.jsonl` files and the tool-loop transcripts
  are committed. Do not regenerate or hand-edit them to make a table tidier --
  re-run the model instead, or say the run is stale.
