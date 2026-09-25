"""Hidden test suite. Curated one-line failures only; never a traceback."""

import sys
from zlib import crc32

from src.codec import encode_record, decode_records
from src.journal import Journal
from src.store import Checkpoint
from src.recover import recover

FAILURES = []
PASSED = 0


def check(name, fn):
    global PASSED
    try:
        fn()
    except AssertionError as e:
        FAILURES.append(f"{name}: {e}")
    except Exception as e:
        FAILURES.append(f"{name}: raised {type(e).__name__}: {e}")
    else:
        PASSED += 1


def eq(got, want, what):
    if got != want:
        raise AssertionError(f"{what} was {got!r}, expected {want!r}")


def journal_of(*pairs):
    j = Journal()
    for key, delta in pairs:
        j.append(key, delta)
    return j.bytes


# -- framing -----------------------------------------------------------

def round_trip_one_record():
    eq(decode_records(encode_record(1, "a", 5)), [(1, "a", 5)], "decoded record")


def round_trip_negative_delta():
    eq(decode_records(encode_record(7, "b", -12)), [(7, "b", -12)], "decoded record")


def round_trip_many():
    blob = journal_of(("a", 1), ("b", 2), ("a", 3))
    eq(decode_records(blob), [(1, "a", 1), (2, "b", 2), (3, "a", 3)], "decoded records")


def empty_journal():
    eq(decode_records(b""), [], "decoded records from nothing")


# -- applying ----------------------------------------------------------

def recovers_every_record_from_a_fresh_checkpoint():
    blob = journal_of(("a", 1), ("b", 2), ("a", 3))
    eq(recover(Checkpoint(), blob), {"a": 4, "b": 2}, "recovered state")


def new_keys_start_at_zero():
    eq(recover(Checkpoint(), journal_of(("z", -5))), {"z": -5}, "recovered state")


def records_at_or_below_the_checkpoint_are_skipped():
    # lsn 1 and 2 are already in the snapshot; only lsn 3 is pending.
    blob = journal_of(("a", 1), ("b", 2), ("a", 3))
    cp = Checkpoint({"a": 1, "b": 2}, lsn=2)
    eq(recover(cp, blob), {"a": 4, "b": 2}, "recovered state")


def the_record_at_the_checkpoint_lsn_is_not_replayed():
    # The classic off-by-one. lsn 1 is in the snapshot; replaying it makes a=2.
    blob = journal_of(("a", 1))
    cp = Checkpoint({"a": 1}, lsn=1)
    eq(recover(cp, blob), {"a": 1}, "recovered state")


def a_fully_covered_journal_changes_nothing():
    blob = journal_of(("a", 1), ("b", 2))
    cp = Checkpoint({"a": 1, "b": 2}, lsn=2)
    eq(recover(cp, blob), {"a": 1, "b": 2}, "recovered state")


# -- the checkpoint is not the caller's to modify ----------------------

def recover_does_not_mutate_the_checkpoint():
    cp = Checkpoint({"a": 1}, lsn=1)
    recover(cp, journal_of(("a", 1), ("a", 10)))
    eq(cp.state, {"a": 1}, "checkpoint state after recovery")


def recovering_twice_gives_the_same_answer():
    cp = Checkpoint({"a": 1}, lsn=1)
    blob = journal_of(("a", 1), ("a", 10))
    # Copied: if recover returns the checkpoint's own dict, `first` would be
    # mutated by the second call and compare equal to itself no matter what.
    first = dict(recover(cp, blob))
    second = dict(recover(cp, blob))
    eq(second, first, "second recovery")


# -- a torn tail -------------------------------------------------------

def a_payload_cut_short_is_discarded():
    blob = journal_of(("a", 1), ("b", 2))
    torn = blob[:-3]
    eq(decode_records(torn), [(1, "a", 1)], "records from a torn journal")


def a_header_cut_short_is_discarded():
    blob = journal_of(("a", 1), ("b", 2))
    # Keep the first record whole and only five bytes of the next header.
    first_len = len(encode_record(1, "a", 1))
    eq(decode_records(blob[:first_len + 5]), [(1, "a", 1)],
       "records from a journal ending inside a header")


def a_torn_tail_does_not_raise():
    blob = journal_of(("a", 1), ("b", 2))
    for cut in range(1, len(blob)):
        decode_records(blob[:cut])


def recovery_over_a_torn_tail():
    blob = journal_of(("a", 1), ("b", 2))
    eq(recover(Checkpoint(), blob[:-3]), {"a": 1}, "recovered state")


# -- a corrupt record stops replay -------------------------------------

def _corrupt_second_record(blob):
    """Flip a byte inside the second record's payload."""
    first = len(encode_record(1, "a", 1))
    i = first + 8  # first byte of the second record's payload
    return blob[:i] + bytes([blob[i] ^ 0xFF]) + blob[i + 1:]


def a_corrupt_record_is_discarded():
    blob = _corrupt_second_record(journal_of(("a", 1), ("b", 2), ("c", 3)))
    got = decode_records(blob)
    if got and got[0] != (1, "a", 1):
        raise AssertionError(f"first record was {got[0]!r}, expected (1, 'a', 1)")
    if any(r[1] == "b" for r in got):
        raise AssertionError("the corrupt record was returned as if it were intact")


def everything_after_a_corrupt_record_is_discarded_too():
    # The third record is perfectly valid. It must still be dropped: replay
    # stops at the corruption rather than skipping over it.
    blob = _corrupt_second_record(journal_of(("a", 1), ("b", 2), ("c", 3)))
    eq(decode_records(blob), [(1, "a", 1)], "records after a corrupt one")


def a_corrupt_record_does_not_raise():
    _corrupt_second_record(journal_of(("a", 1), ("b", 2), ("c", 3)))
    decode_records(_corrupt_second_record(journal_of(("a", 1), ("b", 2), ("c", 3))))


def recovery_stops_at_the_corruption():
    blob = _corrupt_second_record(journal_of(("a", 1), ("b", 2), ("c", 3)))
    eq(recover(Checkpoint(), blob), {"a": 1}, "recovered state")


def the_checksum_covers_the_payload_only():
    # Rebuild a record with a checksum taken over header+payload and it must
    # be rejected -- which also pins down what a correct checksum covers.
    import struct
    payload = b"\x00".join([b"1", b"a", b"1"])
    header = struct.pack(">II", len(payload), crc32(struct.pack(">I", len(payload)) + payload) & 0xFFFFFFFF)
    eq(decode_records(header + payload), [], "records from a wrongly-checksummed journal")


CHECKS = [
    ("round_trip_one_record", round_trip_one_record),
    ("round_trip_negative_delta", round_trip_negative_delta),
    ("round_trip_many", round_trip_many),
    ("empty_journal", empty_journal),
    ("recovers_every_record_from_a_fresh_checkpoint", recovers_every_record_from_a_fresh_checkpoint),
    ("new_keys_start_at_zero", new_keys_start_at_zero),
    ("records_at_or_below_the_checkpoint_are_skipped", records_at_or_below_the_checkpoint_are_skipped),
    ("the_record_at_the_checkpoint_lsn_is_not_replayed", the_record_at_the_checkpoint_lsn_is_not_replayed),
    ("a_fully_covered_journal_changes_nothing", a_fully_covered_journal_changes_nothing),
    ("recover_does_not_mutate_the_checkpoint", recover_does_not_mutate_the_checkpoint),
    ("recovering_twice_gives_the_same_answer", recovering_twice_gives_the_same_answer),
    ("a_payload_cut_short_is_discarded", a_payload_cut_short_is_discarded),
    ("a_header_cut_short_is_discarded", a_header_cut_short_is_discarded),
    ("a_torn_tail_does_not_raise", a_torn_tail_does_not_raise),
    ("recovery_over_a_torn_tail", recovery_over_a_torn_tail),
    ("a_corrupt_record_is_discarded", a_corrupt_record_is_discarded),
    ("everything_after_a_corrupt_record_is_discarded_too", everything_after_a_corrupt_record_is_discarded_too),
    ("a_corrupt_record_does_not_raise", a_corrupt_record_does_not_raise),
    ("recovery_stops_at_the_corruption", recovery_stops_at_the_corruption),
    ("the_checksum_covers_the_payload_only", the_checksum_covers_the_payload_only),
]

for name, fn in CHECKS:
    check(name, fn)

for f in FAILURES:
    print("FAIL: " + f)
print(f"RESULT {PASSED} passed {len(FAILURES)} failed")
sys.exit(1 if FAILURES else 0)
