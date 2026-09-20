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
- **The two suites are never averaged.** The tool loop asks for at least
  everything the code tasks ask for and more, so a combined score describes
  neither. Whether the two orderings can also *disagree* was tested and they do
  not: gpt-oss-20b and Qwen3-Coder-30B are 23 code points apart and tie at 75%
  on the loop. Do not write the stronger "separate axes / different order"
  claim into the docs unless a results file shows an actual rank inversion.
- **Results are the record.** The `.jsonl` files and the tool-loop transcripts
  are committed. Do not regenerate or hand-edit them to make a table tidier --
  re-run the model instead, or say the run is stale.
