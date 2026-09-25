# Journal and crash recovery

A key-value store that survives being killed. State is rebuilt from a
checkpoint plus whatever the journal managed to get to disk.

## Records

Each journal record is framed as:

    4 bytes   payload length, big-endian unsigned
    4 bytes   CRC32 of the payload, big-endian unsigned
    N bytes   payload

The checksum covers **the payload only** -- not the length, not itself.

The payload is `lsn`, `key` and `delta` joined by NUL bytes. `lsn` is a
positive integer, `key` is ASCII without NULs, `delta` is an integer that may
be negative.

## Applying records

Applying a record adds `delta` to the running total for `key`, starting from
zero when the key is new. **Applying is not idempotent**: applying the same
record twice is wrong and the answer will silently be too large.

## Recovery

`recover(checkpoint, blob)` returns the state the store should come back up
with. A checkpoint carries the state as of some `lsn`; a fresh one is `lsn=0`
with empty state.

- A record with `lsn` **greater than** the checkpoint's `lsn` is applied.
- A record with `lsn` **less than or equal to** the checkpoint's `lsn` is
  already accounted for in the snapshot and must be skipped. The record *at*
  the checkpoint's own `lsn` is included in the snapshot, not pending.
- `recover` must not modify the checkpoint it was given. Recovering twice from
  the same checkpoint must produce the same answer both times.

## Damage

A process that dies mid-write leaves a mess at the end of the journal, and
this is normal rather than an error. Two kinds:

- **Torn**: the journal ends in the middle of a record -- fewer than 8 bytes of
  header remain, or the header promises more payload than the file holds.
- **Corrupt**: a record's payload does not match its checksum.

This is the part that is easy to get wrong.

In **both** cases, replay **stops at that record**. It is discarded, and so is
**everything after it**, whether or not those later records are individually
valid. Do not skip the bad record and carry on with the rest: a journal is a
sequence, and anything after a gap cannot be trusted to mean what it says.
Neither case raises -- a damaged tail is the expected result of a crash.
