# Local LLM benchmark

## Agentic coding

| Model                               | solved | tests green | any | operates tools | reads the spec | green but wrong | false done | steps | tok/s |
|-------------------------------------|--------|-------------|-----|----------------|----------------|-----------------|------------|-------|-------|
| gpt-oss-20b-MXFP4                   |    73% |        100% | 100% |           100% |            87% |               4 |          0 |   42% |   1.9 |
| Qwen3.6-27B-Q4_K_M                  |    73% |        100% | 80% |           100% |           100% |               4 |          0 |   33% |   0.6 |
| Qwen3.6-35B-A3B-Q4_K_M              |     7% |         80% | 20% |           100% |            73% |              11 |          0 |   31% |   3.4 |
| Devstral-Small-2507-Q4_K_M          |     0% |         60% |  0% |           100% |            20% |               3 |          0 |   74% |   0.6 |
| Qwen2.5-Coder-32B-Instruct-Q4_K_M   |     0% |         20% |  0% |             0% |             0% |               1 |          0 |   71% |   0.4 |
| Qwen3-Coder-30B-A3B-Instruct-Q4_K_M |     0% |         40% |  0% |            93% |            80% |               6 |          4 |   58% |   1.2 |

### Reading these numbers

Sample: 5 task(s); attempts per model vary (1-3), so a row with fewer attempts resolves less. Per-model counts are in the notes below.

**solved** is the score, and it is the only column that is. It is the
fraction of attempts where the **held-out** suite passes against the
project the model left behind. The model never sees or runs that suite.
Everything else explains how.

- **tests green** — the suite the model *could* run, passing at the end.
  This is what the model thinks it achieved.
- **green but wrong** — attempts where *tests green* and *solved*
  disagree: every signal the model had said done, and the held-out
  suite says no. The visible tests report the symptoms; the held-out
  ones check the rules that only the spec states, so this column counts
  the fixes that satisfied the symptoms without reading why. It is the
  closest thing here to how real work goes wrong.
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

**gpt-oss-20b-MXFP4** (native tool calls) -- **4 attempt(s) went green on every test they could run and still failed the held-out suite**; 19 call(s) repeated a call already made; 1 edit(s) were refused; 15 attempt(s) over 5 task(s); 2.9 edits and 1.9 test runs per attempt
**Qwen3.6-27B-Q4_K_M** (native tool calls) -- **4 attempt(s) went green on every test they could run and still failed the held-out suite**; 19 call(s) repeated a call already made; 15 attempt(s) over 5 task(s); 2.5 edits and 2.1 test runs per attempt; never solved: inventory-ledger
**Qwen3.6-35B-A3B-Q4_K_M** (native tool calls) -- **11 attempt(s) went green on every test they could run and still failed the held-out suite**; 3 attempt(s) ended on a server error; 21 call(s) repeated a call already made; 15 attempt(s) over 5 task(s); 1.9 edits and 2.3 test runs per attempt; never solved: crash-recovery, log-compactor, retry-policy, route-matcher
**Devstral-Small-2507-Q4_K_M** (text tool calls) -- **3 attempt(s) went green on every test they could run and still failed the held-out suite**; 76% of calls were not fenced as the prompt asked (parsed anyway; a formatting deviation, not a channel failure); 47 call(s) repeated a call already made; 3 history compaction(s) -- conversations outgrew the window and older results were summarised; 5 attempt(s) over 5 task(s); 2.6 edits and 10.2 test runs per attempt; never solved: crash-recovery, inventory-ledger, log-compactor, retry-policy, route-matcher
**Qwen2.5-Coder-32B-Instruct-Q4_K_M** (native tool calls) -- **1 attempt(s) went green on every test they could run and still failed the held-out suite**; 100% of calls were malformed or named no tool (76 written in the reply text rather than as a tool call); 1 attempt(s) ended with prose instead of a call; 30 call(s) repeated a call already made; 13 edit(s) were refused; 1 history compaction(s) -- conversations outgrew the window and older results were summarised; 5 attempt(s) over 5 task(s); 4.2 edits and 3.6 test runs per attempt; never solved: crash-recovery, inventory-ledger, log-compactor, retry-policy, route-matcher
**Qwen3-Coder-30B-A3B-Instruct-Q4_K_M** (native tool calls) -- **6 attempt(s) went green on every test they could run and still failed the held-out suite**; 1 attempt(s) left the project unimportable, so neither suite could run; **4 attempt(s) declared done with tests failing**; 7% of calls were malformed or named no tool (17 written in the reply text rather than as a tool call); 80 call(s) repeated a call already made; 17 call(s) ran out of tokens mid-argument (tried to send a whole file); 4 edit(s) were refused; 10 history compaction(s) -- conversations outgrew the window and older results were summarised; 15 attempt(s) over 5 task(s); 3.5 edits and 5.6 test runs per attempt; never solved: crash-recovery, inventory-ledger, log-compactor, retry-policy, route-matcher
