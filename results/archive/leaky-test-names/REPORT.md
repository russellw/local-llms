# Local LLM benchmark

## Agentic coding

| Model                               | solved | any | operates tools | verifies | reads the spec | false done | steps | tok/s |
|-------------------------------------|--------|-----|----------------|----------|----------------|------------|-------|-------|
| gpt-oss-20b-MXFP4                   |   100% | 100% |           100% |     100% |            87% |          0 |   44% |   1.8 |
| Qwen3-Coder-30B-A3B-Instruct-Q4_K_M |    67% | 80% |           100% |     100% |            80% |          4 |   58% |   1.1 |
| Devstral-Small-2507-Q4_K_M          |    60% | 60% |           100% |     100% |            20% |          0 |   74% |   0.6 |
| Qwen2.5-Coder-32B-Instruct-Q4_K_M   |    40% | 40% |             0% |     100% |             0% |          0 |   83% |   0.3 |

### Reading these numbers

Sample: 5 task(s); attempts per model vary (1-3), so a row with fewer attempts resolves less. Per-model counts are in the notes below.

**solved** is the score, and it is the only column that is. It is the
fraction of attempts where the hidden test suite passes against the
project the model left behind -- not what the model claimed, and not
whether some intermediate run went green. Everything else explains how.

- **any** — tasks solved by at least one attempt. The gap from *solved*
  measures consistency.
- **operates tools** — four fifths of calls in the tool-call field, four
  fifths not refused, at least three distinct tools. A floor, not a
  skill: below it, nothing else in the row means anything.
- **verifies** — ran the tests at least once. A model that edits blind
  is guessing even when it guesses right.
- **reads the spec** — on tasks with a requirement stated only in prose,
  whether it opened the file holding it. Nothing points it there.
- **false done** — called `finish` with tests still failing: it believed
  it was done and was not. The agentic failure that costs most in real
  use, and the one no amount of re-running the evidence can catch.
- **steps** — fraction of the step budget spent. Low with a high score
  is a model that knew when it was done; high with a low score is one
  that wandered until it was stopped.

**gpt-oss-20b-MXFP4** (native tool calls) -- 1 attempt(s) ended on a server error; 22 call(s) repeated a call already made; 1 edit(s) were refused; 15 attempt(s) over 5 task(s); 3.2 edits and 2.1 test runs per attempt
**Qwen3-Coder-30B-A3B-Instruct-Q4_K_M** (native tool calls) -- **4 attempt(s) declared done with tests failing**; 88 call(s) repeated a call already made; 13 history compaction(s) -- conversations outgrew the window and older results were summarised; 15 attempt(s) over 5 task(s); 4.1 edits and 6.0 test runs per attempt; never solved: route-matcher
**Devstral-Small-2507-Q4_K_M** (text tool calls) -- 73% of calls were not fenced as the prompt asked (parsed anyway; a formatting deviation, not a channel failure); 47 call(s) repeated a call already made; 1 edit(s) were refused; 7 history compaction(s) -- conversations outgrew the window and older results were summarised; 5 attempt(s) over 5 task(s); 5.6 edits and 8.8 test runs per attempt; never solved: retry-policy, route-matcher
**Qwen2.5-Coder-32B-Instruct-Q4_K_M** (native tool calls) -- 100% of calls were malformed or named no tool (92 written in the reply text rather than as a tool call); 1 attempt(s) ended on a server error; 41 call(s) repeated a call already made; 17 edit(s) were refused; 1 history compaction(s) -- conversations outgrew the window and older results were summarised; 5 attempt(s) over 5 task(s); 4.6 edits and 5.6 test runs per attempt; never solved: inventory-ledger, retry-policy, route-matcher
