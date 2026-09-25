# local-llms

[![selfcheck](https://github.com/russellw/local-llms/actions/workflows/selfcheck.yml/badge.svg)](https://github.com/russellw/local-llms/actions/workflows/selfcheck.yml)

Benchmarking locally-runnable LLMs on ordinary CPU hardware, on the only
question that turns out to matter: **can it do a real piece of coding work by
itself?**

Every model here runs on the machine in front of you: no GPU, no API key, no
data leaving the box.

## What it measures

One suite. Each task is a small Python project that does not pass its tests,
and **two** test suites:

- one the model **cannot read but can run as often as it likes**, which reports
  the symptoms;
- one it never sees, never runs, and is scored on, which checks the rules that
  are stated only in the project's spec.

The model gets six tools -- list, read, write, targeted replace, run the tests,
stop -- and a step budget. It passes when the **held-out** suite passes against
whatever it left on disk.

That split is the point of the design. A model can satisfy every signal it has
access to and still be wrong, and the gap between the two suites is the
`green but wrong` column. This is how real work fails: the tests pass and
production breaks, because the tests described the symptom and the requirement
lived somewhere nobody read.

It exists because the first version of this suite had only the runnable half,
and a 20B model solved every task on every attempt. A suite a model can run to
completion measures how well it hill-climbs a gradient you handed it. The
weaker the model, the more it leans on that: on the runnable-only version the
strongest model needed 2.1 test runs per attempt and the weakest 8.8. Removing
the gradient is the only change that makes the question *why is this wrong*
unavoidable.

That is deliberately one task and not two, because it is the compound ability
that decides whether a local model is any use:

| it has to | or it fails by |
|---|---|
| operate the tools at all | writing calls as prose nobody executes |
| navigate code it did not write | editing the wrong file, or guessing at a function it never read |
| work out what is actually wrong | fixing the symptom the first failure names and stopping |
| write correct, non-trivial Python | passing eleven of twelve and calling it done |
| check itself | declaring victory over a suite that is still red |

Earlier versions of this repo split that into a write-a-function suite and a
drive-a-loop suite. Both are in `results/archive/`, along with what they
measured. They were separated because the abilities fail in different places,
and merged again because a model that has one and not the other is not usable
either way, so a table with two columns and a footnote was answering a question
nobody had.

The tok/s figures sit alongside the scores, because on this hardware **too slow
to use** is its own way to be unusable.

## The machine

| | |
|---|---|
| CPU | Intel i5-7300U, 2 physical cores / 4 threads, AVX2 |
| RAM | 30 GB usable |
| GPU | none |
| Effective memory bandwidth | ~14 GB/s (measured, see below) |

That bandwidth number is the one that matters. CPU token generation is
memory-bound: every generated token requires reading the model's active weights
out of RAM, so **tokens/sec ≈ bandwidth ÷ active-weight bytes**. Compute barely
enters into it.

Two consequences shape every model choice in this repo:

1. **RAM capacity is not the constraint; bandwidth is.** 30 GB is enough to
   *load* a 30B dense model at Q4, but reading ~18 GB per token caps you near
   0.8 tok/s. A 500-token answer would take ten minutes.
2. **Mixture-of-experts models are the sweet spot.** An MoE only reads its
   *active* parameters per token. Qwen3-Coder-30B-A3B has 30B total parameters
   but ~3B active, so it carries a 30B model's knowledge at roughly a 3B
   model's speed. On this box that is the difference between unusable and
   usable.

An agentic suite is far more sensitive to this than a single-shot one. A task
here is twenty-odd model turns, each replaying a conversation that grows with
every file read, so prompt processing stops being a rounding error and starts
being most of the wall clock.

## Quick start

```bash
scripts/build.sh                     # build llama.cpp (slow: ~15 min on 2 cores)
scripts/fetch-model.sh mistralai/Devstral-Small-2507_gguf \
    Devstral-Small-2507-Q4_K_M.gguf

scripts/serve.sh models/Devstral-Small-2507-Q4_K_M.gguf   # terminal 1
python3 -m bench run --label devstral-small-2507-q4       # terminal 2
```

Start with a single task -- `--task inventory-ledger` -- to see what the loop
looks like before committing to a full run.

No `pip install`: the harness is standard library only, so it runs on a bare
Python 3.11+.

## Commands

| Command | What it does |
|---|---|
| `python3 -m bench tasks` | list the tasks |
| `python3 -m bench selfcheck` | prove the suite still measures what it claims |
| `python3 -m bench run --label NAME` | run the suite against the served model |
| `python3 -m bench report --write` | regenerate `results/REPORT.md` from all runs |

Useful `run` flags: `--task <id>` (repeatable) to run a subset, `--repeats N`
to sample each task N times, `--protocol native|text|auto`, `--fresh` to
discard prior results, `--max-tokens-scale 3` for a reasoning model that needs
room to think before each call.

Runs default to temperature 0. That is the right setting for a single pass --
greedy decoding is deterministic, so the score is reproducible. It is the wrong
setting for `--repeats > 1`, where every attempt would replay the identical
run, so passing repeats without a temperature switches to 0.2 and says so.

**`selfcheck` is the guard rail**, and it is the thing to run after touching a
task, the workspace or the scorer. It checks three things:

- **Every task is solvable and not already solved.** Its `reference/` overlay
  must make the hidden suite pass, and the project as shipped must fail it. A
  task whose own reference fix fails measures nothing; a task that passes as
  shipped measures nothing either, and both are easy to introduce by accident.
  It has already caught a test of mine that was wrong rather than a reference
  that was.
- **The workspace cannot be talked out of its boundaries.** The tests must not
  be readable, reachable by a relative path, or visible in a listing, and
  failure output must not carry their source back to the model.
- **The scorer scores the right thing.** Scripted agents are played against it:
  one that applies the reference fix must pass, one that announces success
  without changing anything must not, one that gets the suite green and then
  breaks it again must be scored on the wreckage, and one whose every call is
  written as prose must fail the tool-operating floor.

## The tasks

Five, all deliberately hard. A task that a 7B solves on the first try tells you
nothing you did not already know.

| Task | The work | The trap |
|---|---|---|
| `inventory-ledger` | FIFO stock costing with fractional unit costs | rounding each lot separately instead of once per issue -- and the rule is stated only in `README.md` |
| `route-matcher` | URL routing with parameter and wildcard segments | matching in registration order, when the spec decides by segment specificity |
| `log-compactor` | one-pass compaction of a record stream | fixing the logic and leaving the per-record scan, so it stays quadratic and the suite times out |
| `retry-policy` | backoff, jitter, throttling and an elapsed budget | fixing the arithmetic while the classifier still calls `429` fatal, so the throttling branch is never reached |
| `crash-recovery` | rebuilding a store from a checkpoint and a damaged journal | skipping a corrupt record and carrying on, where the spec says replay stops there and discards everything after |

`crash-recovery` is the hardest and was added because gpt-oss-20b solved the
other four outright. Its three bugs are spread over three files and none of
them is local to the symptom: replay is off by one against the checkpoint's own
sequence number, recovery aliases the checkpoint's state instead of copying it
(so recovering twice gives different answers), and a corrupt record is skipped
rather than stopping the replay. Fixing everything visible in the code gets to
**18 of 20** and still fails -- the last two need the rule that exists only in
`SPEC.md`.

Each has several interacting bugs rather than one, because a single planted bug
rewards pattern-matching and a spec clause nobody mentioned rewards reading.
Each carries a requirement that **cannot be inferred from the code** -- stated
in a `README.md` or `SPEC.md` that nothing points the model towards. Whether it
goes and reads that file is its own column in the report.

**How much the tests give away, stated honestly.** A failing assertion has to
report what it expected, so the *target values* are visible: a model that reads
`expected 'throttled'` knows what 429 should classify as. What it does not get
is the *reason* -- it must still infer "round half to even" from "expected 2,
not 3", and the spec is where the reasons are.

That boundary was not free. The first version of this suite named its checks
after the rules they enforced -- `rounds_once_not_per_lot`,
`static_beats_param_registered_later`,
`everything_after_a_corrupt_record_is_discarded_too` -- and printed those names
on failure. The specs were therefore readable straight off the test output, and
two models solved `crash-recovery` without opening `SPEC.md` at all. Checks are
now named for the scenario they run, not the rule they check.

### Adding a task

```
tasks/<id>/
    task.json     title, brief, budget, difficulty, spec_file
    project/      the tree the model is given, copied fresh per attempt
    tests/        run_tests.py -- runnable by the model, never readable
    acceptance/   run_tests.py -- held out; the suite the score comes from
    reference/    files overlaid on project/ to make both suites pass
```

**Design the split deliberately.** `tests/` must fail as shipped, or the model
has nothing to work from and stops at once. `acceptance/` must hold the rules
that only the spec states, so that a fix arrived at by watching the visible
tests go green is not enough. The test worth running by hand: build the
reference, put the spec-only rules back to their broken state, and check that
the visible suite goes green while the held-out one does not. All five tasks
here satisfy that, and `crash-recovery` needed a mechanical bug added
afterwards because all three of its original bugs were spec-only -- its visible
suite passed as shipped, which would have made it unplayable.

`tests/run_tests.py` must print `RESULT <n> passed <m> failed` and exit
non-zero on failure. Print **curated one-line failures and never a traceback**:
a traceback quotes the failing source line, which for a hidden suite hands the
model the assertion it is supposed to satisfy.

**Name checks after the scenario, not the rule.** `two_lots_of_half_a_cent`,
not `rounds_once_not_per_lot`; `delay_on_attempt_6_with_a_cap_of_10`, not
`the_ceiling_is_capped_before_jitter`. The same goes for the text in an
assertion: report the quantity that differs ("cost of issuing 2"), not the
policy it should have followed ("cost of two half-cent units rounded once").
The check name is printed to the model on every failing run, so a descriptive
one is a free copy of the spec and makes the `reads the spec` column measure
nothing. This is the single easiest way to ruin a task, and it ruined all five
of these before it was noticed.

Then run `python3 -m bench selfcheck`.

## What this does not measure

Stated plainly, because these are deliberate boundaries rather than oversights:

**Five tasks is a small sample.** It resolves large differences between models
and nothing finer. Attempts at the same task are correlated, so the effective
sample size is closer to the number of *tasks* than the number of attempts.

**The projects are small and synthetic.** A few files each, written to be
broken in specific ways. That is what makes them deterministic, replayable and
free of contamination, and it is also why passing here is not evidence a model
can work in a real repository with a hundred thousand lines and no spec.

**Whole-file writes and exact-string replaces are not a real editor.** No
patches, no partial application, no failure to apply. A model that is good at
producing diffs gets no credit for it, and one that is bad at it is not
punished.

**One hardware configuration, one quantisation.** Results are Q4_K_M (or the
model's native format) on one CPU. Quantisation quality effects and any
GPU-relevant conclusions are out of scope; the tok/s figures transfer to
nothing but a machine with similar memory bandwidth.

**Contamination is damped, not absent.** The projects are written for this
repo, so they are not in any model's training data today. Nothing stops that
changing, and the defence is that they are cheap to replace.

**The ceiling is established for four of the five.** `inventory-ledger`,
`route-matcher`, `log-compactor` and `retry-policy` have each been solved by a
real model rather than merely by their own reference fix -- gpt-oss-20b solved
all four on all three attempts. A 0% on those is the model's, and the
transcripts will say why.

`crash-recovery` was added afterwards, precisely because that 100% meant the
suite could not rank anything at or above gpt-oss-20b. It is calibrated against
partial fixes rather than against a model, so its difficulty is argued and not
yet demonstrated: **no model has attempted it.** Until one does, treat a zero
there as unexplained rather than damning.

## What the first run found

Four models, on the machine described above. `results/REPORT.md` has the full
table and the diagnostics; this is the part worth knowing.

**These numbers are stale and are kept only as history.** They were measured
against a version of the tests whose check names stated the rules the specs were
supposed to hold, so the `reads the spec` column and anything resting on it
cannot be trusted. They live in `results/archive/leaky-test-names/`. A run
against the current tests is in progress.

| Model | solved | operates tools | reads the spec | false done | tok/s |
|---|---|---|---|---|---|
| gpt-oss-20b-MXFP4 | 100% | 100% | 83% | 0 | 1.8 |
| Qwen3-Coder-30B-A3B | 58% | 100% | 75% | 4 | 1.2 |
| Devstral-Small-2507 | 50% | 100% | 25% | 0 | 0.6 |
| Qwen2.5-Coder-32B | 25% | 0% | 0% | 0 | 0.3 |

The MoE models were run three times per task and the dense ones once, because
at 0.3 tok/s a single pass is a day. A one-attempt row resolves less; treat the
gap between 58% and 50% as nothing. All four scored 100% on `crash-recovery`,
which is what exposed the leak: two of them did it without opening the spec.

**The ranking is the least interesting thing here.** The three models that fail
fail in three unrelated ways, and a single score would have hidden all of it:

- **Qwen3-Coder-30B is competent and over-confident.** It fixes most of a task
  and then stops: four attempts called `finish` with the suite still red, twice
  leaving `retry-policy` at 20 of 22 passing. It is the only model that did
  this, and it is the failure that costs most in real use, because nothing
  downstream can catch it -- the code is plausible, the model is certain, and
  the tests were never run again.
- **Devstral-Small-24B spins.** On `retry-policy` it made one edit at step 6
  and then ran the tests twenty times in a row until the budget stopped it,
  never editing again. 10.3 hours to change one line. Its other failure,
  `route-matcher`, is the opposite shape: 14 edits and still short.
- **Qwen2.5-Coder-32B cannot quote code.** 17 refused edits in four attempts,
  against zero for Qwen3 across twelve. On `route-matcher` it made 13
  `replace_in_file` calls and landed none, drifting from the file's text --
  `if` where the source says `elif`, sixteen spaces where it has twelve. It
  also wrote every one of its 75 tool calls into the reply text rather than the
  tool-call field, which is what the 0% floor records.

**Reading the spec tracks the score better than anything else.** The models
that went and opened the file nobody pointed them at are the models that
solved things. The one that never opened it solved one task in four.

**Mixture-of-experts is not a nice-to-have on this hardware.** The two dense
models read 14 and 20 GB per token against the MoE pair's ~2, and that is the
whole difference between 1.8 tok/s and 0.3. It compounds over a twenty-turn
task: gpt-oss finished its twelve attempts in 6.5 hours, Qwen2.5-Coder-32B took
16 hours for four.

## Reading the results

Each run appends to `results/<label>.jsonl`, flushed after every attempt, so an
overnight run that dies at 4am keeps everything it finished. Re-running the
same label resumes where it stopped. A readable transcript of every attempt
lands in `results/transcripts/<label>/`, and those are committed.

**Read the transcripts.** A rate tells you a model failed; only the transcript
tells you whether it never opened the spec, edited a file it had not read, or
got the suite green and then broke it again on the next call. Those are
different problems with different fixes and they look identical in a score.

**solved** is the score, and it is the only column that is: the fraction of
attempts where the hidden suite passes against what the model left behind --
not what the model claimed, and not whether some intermediate run went green.
The rest explain how:

- **operates tools** -- four fifths of calls in the tool-call field, four
  fifths not refused, at least three distinct tools. A floor, not a skill:
  below it nothing else in the row means anything.
- **verifies** -- ran the tests at least once. A model that edits blind is
  guessing even when it guesses right.
- **reads the spec** -- opened the file holding the requirement that cannot be
  inferred. Nothing points it there.
- **false done** -- called `finish` with tests still failing. The agentic
  failure that costs most in real use: confident, well-formed, and wrong.

`results/archive/` holds the two suites this replaced, with their results and
their report, unchanged.

## Tool-call protocols

Tool calls go over the `tools` API parameter by default, the way a real agent
drives a model, so results transfer. `--protocol text` describes the tools in
the system prompt instead, for servers that reject the parameter; `auto` picks
by testing whether the *server* accepts it, never whether the model used it,
because a model that is offered tools and ignores them is exactly what this
suite is trying to catch.

A call written into the reply text instead of the tool-call field is salvaged
and executed, so the rest of the attempt can still be measured -- but counted
as malformed, and a model whose calls mostly arrive that way fails the
`operates tools` floor. A real agent reads the field, finds it empty, and sees
a model that said nothing at all.

**A reply carried in a reasoning channel is not silence.** A model in the
harmony format may answer entirely in its analysis channel, which llama-server
returns as `reasoning_content` beside an empty `content`. Reading only
`content` there scores the harness rather than the model -- it once recorded a
model at 0% while its discarded replies contained the correct tool calls -- so
both are read.

## Tuning

`scripts/speed-test.sh models/foo.gguf` sweeps thread counts with `llama-bench`
and reports prompt-processing and generation speed separately. On a 2-core
machine more threads is not reliably better, since hyperthreads contend for the
same memory ports — measure rather than assume. `serve.sh` defaults to physical
core count and honours `THREADS`, `CTX`, `PORT`, and `MLOCK` from the
environment.

Quantisation is the other lever. Q4_K_M is the default choice here because it
roughly halves bytes-read-per-token versus Q8 for a small quality cost; on a
bandwidth-bound box that is close to a 2x speedup. Q5_K_M is worth testing when
a model is close to passing but sloppy.

Context size matters more here than it did for single-shot prompting, and it is
easy to get wrong in both directions:

- **Too small silently destroys scores.** An agentic conversation grows with
  every file read and every test report. If it outgrows the context the model
  loses the beginning of its own investigation and starts repeating work.
  gpt-oss-20b at `CTX=8192` previously hit the ceiling mid-thought on 7 of 12
  single-shot attempts; a tool loop reaches that ceiling far sooner.
- **Too large costs real speed.** Raising the same model to `CTX=32768` dropped
  it from 5.1 to ~3.2 tok/s, because attention work grows with sequence length
  and the KV cache competes for the same scarce bandwidth.

## A note on running model-generated code

The harness executes model output in a subprocess with a wall-clock timeout, a
2 GB address-space cap, a process-count cap, and a scratch working directory
that is deleted afterwards.

Those limits stop *accidents* — runaway loops, memory bombs, a stray
`while True`. They are **not** a security boundary. The code runs as your user,
with your filesystem and your network. That is an acceptable trade for
benchmarking known-good open-weight models on this suite's prompts, but if you
ever point the harness at untrusted prompts or untrusted weights, put it in a
container or a VM first.
