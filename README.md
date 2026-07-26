# local-llms

[![selfcheck](https://github.com/russellw/local-llms/actions/workflows/selfcheck.yml/badge.svg)](https://github.com/russellw/local-llms/actions/workflows/selfcheck.yml)

Benchmarking locally-runnable LLMs on coding tasks, on ordinary CPU hardware.

Every model here runs on the machine in front of you: no GPU, no API key, no
data leaving the box. The suite measures the two things that actually decide
whether a local model is usable — **does its code work**, and **how long did
you wait for it**.

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

## Quick start

```bash
scripts/build.sh                     # build llama.cpp (slow: ~15 min on 2 cores)
scripts/fetch-model.sh Qwen/Qwen2.5-Coder-7B-Instruct-GGUF \
    qwen2.5-coder-7b-instruct-q4_k_m.gguf

scripts/serve.sh models/qwen2.5-coder-7b-instruct-q4_k_m.gguf   # terminal 1
python3 -m bench run --label qwen2.5-coder-7b-q4                # terminal 2
```

No `pip install`: the harness is standard library only, so it runs on a bare
Python 3.11+.

## Commands

| Command | What it does |
|---|---|
| `python3 -m bench tasks` | list the task suite |
| `python3 -m bench selfcheck` | run every reference solution against its own tests |
| `python3 -m bench run --label NAME` | benchmark the model currently being served |
| `python3 -m bench report --write` | regenerate `results/REPORT.md` from all runs |

Useful `run` flags: `--task <id-or-category>` (repeatable) to run a subset,
`--repeats N` to sample each task N times, `--fresh` to discard prior results.

Runs default to temperature 0. That is the right setting for a single pass —
greedy decoding is deterministic, so the score is reproducible. It is the wrong
setting for `--repeats > 1`, where every attempt would return the identical
answer, so passing repeats without a temperature switches to 0.2 and says so.

**`selfcheck` is the guard rail.** A benchmark whose tests are subtly wrong
measures nothing, so it checks two things:

- every task's `reference.py` passes its own `tests.py`
- the harness itself behaves — code extraction handles the dozen ways a model
  can wrap (or fail to wrap) a code block, and the sandbox actually fails wrong
  answers, fails syntax errors, kills infinite loops, and isolates workdirs

Run it after touching any task. It has already caught three bugs — two in
tests, one in a reference — that would otherwise have been silently scored
against the models.

## The task suite

Twelve tasks, all verified by executing the model's code against hidden unit
tests. Nothing is graded by eyeballing or by another model.

| Category | Tasks | What it probes |
|---|---|---|
| `algorithm` | rle-codec, merge-intervals, roman-numerals, binary-search-insert | baseline competence and edge cases |
| `datastruct` | topological-sort, autocomplete-trie | does it build the structure that was asked for |
| `bugfix` | fix-lru-cache, fix-min-heap | reading broken code and reasoning about *why* it is broken |
| `spec` | event-emitter, csv-parser, expression-eval, semver-compare | following a long, precise specification exactly |

The suite is deliberately weighted away from "recite a LeetCode answer".
Several tasks defend against the shortcut rather than the wrong answer:

- **binary-search-insert** passes the sequence in as an object that counts
  index accesses and refuses to be iterated, so a linear scan fails outright.
- **autocomplete-trie** checks that a rare prefix in a 20,000-word dictionary
  stays cheap, so a flat list with `startswith` fails.
- **csv-parser** and **expression-eval** forbid the stdlib module that would
  trivialise them.
- **fix-lru-cache** and **fix-min-heap** hand the model plausible-looking code
  with several interacting bugs, which is much closer to real work than writing
  from scratch.

`spec` is usually the category that separates models. Small models can often
produce a working algorithm but lose points on the sixth clause of a
specification — precisely the failure mode that makes a coding assistant
frustrating in practice.

### What this suite does not measure

Stated plainly, because these are deliberate boundaries rather than oversights:

**Training-data contamination is not eliminated, only made less useful.** An
LRU cache, a min-heap, a CSV parser and a semver comparator are all classic
exercises that are certainly in every model's training data. That is survivable
because the tasks do not score "did you recognise this problem" — they score
conformance to a specific written spec, and the specs deliberately deviate from
the textbook version. `merge-intervals` merges intervals that are merely
*adjacent*, not just overlapping. `rle-codec` writes the count even when it is 1.
The observed failures match this design: models produce the recognisable general
shape and then miss a clause. A model that had memorised the answer outright
would not fail that way. Treat contamination as damped, not absent.

**Sample size is small.** Twelve tasks resolves large differences between
models and nothing finer. `results/REPORT.md` restates this next to the numbers.

**Scope is single-file Python.** Every task is one self-contained module with a
clean specification. Real coding work is multi-file, involves existing code you
did not write, and is iterative — you get a failing test and try again. None of
that is measured here. A model that scores well on this suite has demonstrated
that it can write correct Python to a precise spec; it has not demonstrated that
it can work in your codebase.

**One hardware configuration, one quantisation.** Results are Q4_K_M (or the
model's native format) on one CPU. Quantisation quality effects and any
GPU-relevant conclusions are out of scope; the tok/s figures transfer to nothing
but a machine with similar memory bandwidth.

### Adding a task

Create `tasks/<id>/` with three files, and an entry in `tasks/manifest.json`:

- `prompt.md` — the user message. Be exhaustive about edge cases; ambiguity in
  the prompt shows up as noise in the scores.
- `tests.py` — imports from `solution`, prints failures, exits non-zero. Report
  *all* failures rather than stopping at the first: the detail is what makes a
  result diagnosable later.
- `reference.py` — a known-good solution. Then run `python3 -m bench selfcheck`.

## Reading the results

Each run appends to `results/<label>.jsonl`, flushed after every task, so an
overnight run that dies at 4am keeps everything it finished. Re-running the
same label resumes where it stopped. Full model responses land in
`results/responses/<label>/` (gitignored) — read those when a score surprises
you.

The report shows:

- **pass@1** — mean success rate over all attempts. The headline number.
- **pass@any** — solved at least once. With `--repeats > 1` the gap between
  these two measures consistency, which matters more than peak ability when
  you are waiting minutes per answer.
- **tok/s** — median generation speed, taken from llama.cpp's own timings.
- Notes separating the failure modes that are *not* "wrote wrong code":
  responses that hit the token limit, responses containing no code block, and
  attempts that never finished generating inside the request timeout. That last
  one means **too slow to use**, not **too stupid to solve** — a distinction
  worth keeping, since on this hardware a reasoning model can spend over an
  hour on a single task and be marked wrong for it.

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

Context size is a lever in both directions, and it is easy to get wrong:

- **Too small silently destroys scores.** Context must hold the prompt *and*
  the entire response. gpt-oss-20b at `CTX=8192` hit the ceiling mid-thought on
  7 of 12 `spec` attempts and returned no code at all — scoring zero on ability
  it may well have had. If a model shows truncated responses in the report,
  raise `CTX` before believing the number.
- **Too large costs real speed.** Raising the same model to `CTX=32768` dropped
  it from 5.1 to ~3.2 tok/s, because attention work grows with sequence length
  and the KV cache competes for the same scarce bandwidth. Provision context
  for the responses you actually see, not for the maximum the model supports.

## A note on running model-generated code

`bench/sandbox.py` executes model output in a subprocess with a wall-clock
timeout, a 2 GB address-space cap, a process-count cap, and a scratch working
directory that is deleted afterwards.

Those limits stop *accidents* — runaway loops, memory bombs, a stray
`while True`. They are **not** a security boundary. The code runs as your user,
with your filesystem and your network. That is an acceptable trade for
benchmarking known-good open-weight models on this suite's prompts, but if you
ever point the harness at untrusted prompts or untrusted weights, put it in a
container or a VM first.
