# crash-recovery -- Crash recovery from a checkpoint and a torn journal

passed: True   stopped: finish   steps: 11/30   edits: 3   test runs: 2   failing at end: 0/13

## step 1

To understand the project structure, let's start by exploring the project first.

    -> list_files({})

       SPEC.md (54 lines)
       src/__init__.py (0 lines)
       src/codec.py (34 lines)
       src/journal.py (19 lines)
       src/recover.py (14 lines)
       src/store.py (15 lines)

## step 2

Small project. Let me read all the files.

    -> read_file({"path": "SPEC.md"})

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
       record twice is wrong and the answer will silently ... (truncated)

    -> read_file({"path": "src/codec.py"})

       """Framing and parsing of journal records. See SPEC.md."""
       
       import struct
       from zlib import crc32
       
       HEADER = struct.Struct(">II")  # payload length, payload checksum
       
       
       def encode_record(lsn, key, delta):
           """Frame one record for the journal."""
           payload = b"\x00".join([str(lsn).encode(), key.encode("ascii"), str(delta).encode()])
           return HEADER.pack(len(payload), crc32(payload) & 0xFFFFFFFF) + payload
       
       
       def _parse(payload):
           lsn, key, delta = payload.split(b"\x00")
           return int(lsn), key.decode("ascii"), int(delta)
       
       
       def decode_records(blob):
           """Every intact record at the front of `blob`, in order."""
           out = []
           pos = 0
           while pos + HEADER.size <= len(blob):
               length, checksum = HEADER.unpack(blob[pos:pos + HEADER.size])
               if pos + HEADER.size + length ... (truncated)

## step 3

Interesting — only some of the calls were executed. It seems the tool only allows one call per reply? "not executed: one tool call per reply, please." Let me try reading the files one by one.

Actually, the first two (list_files and read_file for SPEC.md and codec.py) were executed. The rest were not. So I should make one tool call per reply. Let me read journal.py.

    -> read_file({"path": "src/journal.py"})

       """Appending to the journal. See SPEC.md."""
       
       from .codec import encode_record
       
       
       class Journal:
           def __init__(self):
               self._buf = bytearray()
               self._last_lsn = 0
       
           @property
           def bytes(self):
               return bytes(self._buf)
       
           def append(self, key, delta):
               """Write one record. Returns the lsn it was given."""
               self._buf += encode_record(self._last_lsn, key, delta)
               self._last_lsn += 1
               return self._last_lsn

## step 4

journal.py: `append` uses `self._last_lsn` and then increments it. So the first record gets lsn=0. But the spec says "lsn is a positive integer". Hmm, the first record should probably be lsn=1. Let me check recover.py and store.py.

    -> read_file({"path": "src/recover.py"})

       """Rebuilding state after a crash. See SPEC.md."""
       
       from .codec import decode_records
       from .store import apply_record
       
       
       def recover(checkpoint, blob):
           """The state to come back up with, from a checkpoint and a journal."""
           state = checkpoint.state
           for lsn, key, delta in decode_records(blob):
               if lsn < checkpoint.lsn:
                   continue
               apply_record(state, key, delta)
           return state

## step 5

Bugs in recover.py:
1. `state = checkpoint.state` — this is a reference, not a copy. Then `apply_record(state, ...)` modifies the checkpoint's state. The spec says "recover must not modify the given checkpoint." So we need to copy the state.
2. `if lsn < checkpoint.lsn: continue` — the spec says records with lsn less than or equal to the checkpoint's lsn should be skipped. So it should be `if lsn <= checkpoint.lsn: continue`.

Next, let's take a look at store.py.

    -> read_file({"path": "src/store.py"})

       """The state a journal rebuilds. See SPEC.md."""
       
       
       class Checkpoint:
           def __init__(self, state=None, lsn=0):
               self.state = dict(state or {})
               self.lsn = lsn
       
           def __repr__(self):
               return f"Checkpoint(lsn={self.lsn}, state={self.state})"
       
       
       def apply_record(state, key, delta):
           """Add `delta` to `key`'s running total."""
           state[key] = state.get(key, 0) + delta

## step 6

Now let me run the tests to see the current state.

    -> run_tests({})

       9/13 tests passed
       FAIL: encode_decode_three_records: decoded records was [(0, 'a', 1), (1, 'b', 2), (2, 'a', 3)], expected [(1, 'a', 1), (2, 'b', 2), (3, 'a', 3)]
       FAIL: blob_cut_inside_a_payload: decoded records was [(0, 'a', 1)], expected [(1, 'a', 1)]
       FAIL: blob_cut_inside_a_header: decoded records was [(0, 'a', 1)], expected [(1, 'a', 1)]
       FAIL: decode_with_a_bad_checksum: first record was (0, 'a', 1), expected (1, 'a', 1)

## step 7

The failures point at the LSN numbering: records should start at 1, not 0. Let me fix `Journal.append`.

    -> replace_in_file({"path": "src/journal.py", "old": "        self._buf += encode_record(self._last_lsn, key, delta)\n        self._last_lsn += 1\n        return self._last_lsn", "new": "        self._last_lsn += 1\n        self._buf += encode_record(self._last_lsn, key, delta)\n        return self._last_lsn"})

       replaced 1 occurrence in src/journal.py

## step 8

Now the corrupt-record handling in `decode_records` — the spec says replay must stop at a corrupt record, not skip it:

    -> replace_in_file({"path": "src/codec.py", "old": "        if crc32(payload) & 0xFFFFFFFF != checksum:\n            pos += HEADER.size + length\n            continue", "new": "        if crc32(payload) & 0xFFFFFFFF != checksum:\n            break"})

       replaced 1 occurrence in src/codec.py

## step 9

Now `recover.py`: it must not mutate the checkpoint's state, and records at the checkpoint's LSN must be skipped too:

    -> replace_in_file({"path": "src/recover.py", "old": "    state = checkpoint.state\n    for lsn, key, delta in decode_records(blob):\n        if lsn < checkpoint.lsn:\n            continue", "new": "    state = dict(checkpoint.state)\n    for lsn, key, delta in decode_records(blob):\n        if lsn <= checkpoint.lsn:\n            continue"})

       replaced 1 occurrence in src/recover.py

## step 10

Wait a sec, there's a subtle point about the `lsn <= checkpoint.lsn` fix. The spec says:

- Records with an lsn **greater than** the checkpoint's lsn are applied.
- Records with an lsn **less than or equal to** the checkpoint's lsn are skipped.

So `if lsn <= checkpoint.lsn: continue` is correct.

But wait — there's a subtle point about idempotency: "recovering twice from the same checkpoint must yield the same answer both times." If we copy the state, that's satisfied.

Alright, let's run the tests.

    -> run_tests({})

       13/13 tests passed
       all tests passed

## step 11

All 13 tests pass. The fixes were:

1. **`src/journal.py`** — `append` was numbering records starting at 0; the spec requires positive LSNs, so the counter is now incremented before framing (first record gets LSN 1).
2. **`src/codec.py`** — `decode_records` skipped a record with a bad checksum and kept going; per the spec, replay must stop at a corrupt record and discard everything after it, so it now `break`s.
3. **`src/recover.py`** — two bugs: it applied records directly into `checkpoint.state` (mutating the checkpoint), so it now copies the state first; and it only skipped records with `lsn < checkpoint.lsn`, but the record *at* the checkpoint's LSN is already in the snapshot, so the skip is now `lsn <= checkpoint.lsn`.

    -> finish({"summary": "Fixed LSN numbering in Journal.append (start at 1), made decode_records stop at a corrupt record instead of skipping it, and made recover copy the checkpoint's state and skip records with lsn <= checkpoint.lsn."})

       ended
