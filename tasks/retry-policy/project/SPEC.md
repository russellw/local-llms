# Retry policy

Two pieces that have to agree: `classify` decides what kind of failure
happened, and `RetryPolicy` decides whether and when to try again. A correct
delay calculation on a misclassified error is still the wrong answer, so both
sides matter.

## Classification

`classify(status, message="")` returns one of `RETRYABLE`, `THROTTLED`,
`FATAL`.

- `408`, `500`, `502`, `503`, `504` -- **RETRYABLE**
- `429` -- **THROTTLED**. It is not fatal, and it is not an ordinary retryable
  error either; it has its own delay rule below.
- Any other status at or above 400 -- **FATAL**
- Any status below 400 -- **FATAL** (it is not a failure, so there is nothing
  to retry)
- `status=None` means the request never got a reply. The message decides: if it
  mentions `timeout` or `reset`, **RETRYABLE**; otherwise **FATAL**. Matching is
  case-insensitive.

## Delays

`RetryPolicy(base_delay, max_delay, max_attempts, max_elapsed, rng)`.

`next_delay(attempt, status, retry_after=None, elapsed=0.0)` returns the number
of seconds to wait before the next try, or `None` if there must not be one.
`attempt` is 0 for the first failure, 1 for the second, and so on.

**FATAL** returns `None` immediately.

**Attempt limit.** `max_attempts` counts total tries. After the failure of the
last permitted try there is no delay: with `max_attempts=3`, attempts 0 and 1
may produce a delay and attempt 2 must return `None`.

**RETRYABLE** backs off exponentially from the first retry: the ceiling is
`base_delay * 2 ** attempt`, so attempt 0 has a ceiling of exactly
`base_delay`. The ceiling is capped at `max_delay` **before** any jitter is
applied, and the delay is then `rng.uniform(0, ceiling)` -- full jitter, over
the capped ceiling. Jittering first and capping afterwards changes the
distribution and is not what this does.

**THROTTLED** ignores the backoff entirely and waits exactly `retry_after`
seconds, with no jitter, capped at `max_delay`. If `retry_after` is `None`,
fall back to the RETRYABLE rule.

**Elapsed budget.** `max_elapsed` is a ceiling on the total time spent,
including the delay about to be waited. If `elapsed + delay` would exceed
`max_elapsed`, there must be no further try and the answer is `None`. Exactly
reaching `max_elapsed` is permitted; exceeding it is not.
