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

def encode_decode_one_record():
    eq(decode_records(encode_record(1, "a", 5)), [(1, "a", 5)], "decoded record")


def encode_decode_negative_delta():
    eq(decode_records(encode_record(7, "b", -12)), [(7, "b", -12)], "decoded record")


def encode_decode_three_records():
    blob = journal_of(("a", 1), ("b", 2), ("a", 3))
    eq(decode_records(blob), [(1, "a", 1), (2, "b", 2), (3, "a", 3)], "decoded records")


def empty_blob():
    eq(decode_records(b""), [], "decoded records from nothing")


# -- applying ----------------------------------------------------------

def recovery_from_lsn_0():
    blob = journal_of(("a", 1), ("b", 2), ("a", 3))
    eq(recover(Checkpoint(), blob), {"a": 4, "b": 2}, "recovered state")


def recovery_of_an_unseen_key():
    eq(recover(Checkpoint(), journal_of(("z", -5))), {"z": -5}, "recovered state")


def recovery_from_lsn_2_of_3():
    # lsn 1 and 2 are already in the snapshot; only lsn 3 is pending.
    blob = journal_of(("a", 1), ("b", 2), ("a", 3))
    cp = Checkpoint({"a": 1, "b": 2}, lsn=2)
    eq(recover(cp, blob), {"a": 4, "b": 2}, "recovered state")


def recovery_from_lsn_1_of_1():
    # The classic off-by-one. lsn 1 is in the snapshot; replaying it makes a=2.
    blob = journal_of(("a", 1))
    cp = Checkpoint({"a": 1}, lsn=1)
    eq(recover(cp, blob), {"a": 1}, "recovered state")


def recovery_from_lsn_2_of_2():
    blob = journal_of(("a", 1), ("b", 2))
    cp = Checkpoint({"a": 1, "b": 2}, lsn=2)
    eq(recover(cp, blob), {"a": 1, "b": 2}, "recovered state")


# -- the checkpoint is not the caller's to modify ----------------------

def checkpoint_after_recovery():
    cp = Checkpoint({"a": 1}, lsn=1)
    recover(cp, journal_of(("a", 1), ("a", 10)))
    eq(cp.state, {"a": 1}, "checkpoint state after recovery")


def two_recoveries_from_one_checkpoint():
    cp = Checkpoint({"a": 1}, lsn=1)
    blob = journal_of(("a", 1), ("a", 10))
    # Copied: if recover returns the checkpoint's own dict, `first` would be
    # mutated by the second call and compare equal to itself no matter what.
    first = dict(recover(cp, blob))
    second = dict(recover(cp, blob))
    eq(second, first, "second recovery")


# -- a torn tail -------------------------------------------------------

def blob_cut_inside_a_payload():
    blob = journal_of(("a", 1), ("b", 2))
    torn = blob[:-3]
    eq(decode_records(torn), [(1, "a", 1)], "decoded records")


def blob_cut_inside_a_header():
    blob = journal_of(("a", 1), ("b", 2))
    # Keep the first record whole and only five bytes of the next header.
    first_len = len(encode_record(1, "a", 1))
    eq(decode_records(blob[:first_len + 5]), [(1, "a", 1)],
       "decoded records")


def blob_cut_at_every_offset():
    blob = journal_of(("a", 1), ("b", 2))
    for cut in range(1, len(blob)):
        decode_records(blob[:cut])


def recovery_from_a_cut_blob():
    blob = journal_of(("a", 1), ("b", 2))
    eq(recover(Checkpoint(), blob[:-3]), {"a": 1}, "recovered state")


# -- a corrupt record stops replay -------------------------------------

def _flip_a_byte_in_the_second_record(blob):
    """Flip a byte inside the second record's payload."""
    first = len(encode_record(1, "a", 1))
    i = first + 8  # first byte of the second record's payload
    return blob[:i] + bytes([blob[i] ^ 0xFF]) + blob[i + 1:]


def decode_with_a_bad_checksum():
    blob = _flip_a_byte_in_the_second_record(journal_of(("a", 1), ("b", 2), ("c", 3)))
    got = decode_records(blob)
    if got and got[0] != (1, "a", 1):
        raise AssertionError(f"first record was {got[0]!r}, expected (1, 'a', 1)")
    if any(r[1] == "b" for r in got):
        raise AssertionError("a record whose checksum does not match was returned")


def decode_past_a_bad_checksum():
    # The third record is perfectly valid. It must still be dropped: replay
    # stops at the corruption rather than skipping over it.
    blob = _flip_a_byte_in_the_second_record(journal_of(("a", 1), ("b", 2), ("c", 3)))
    eq(decode_records(blob), [(1, "a", 1)], "decoded records")


def bad_checksum_does_not_raise():
    _flip_a_byte_in_the_second_record(journal_of(("a", 1), ("b", 2), ("c", 3)))
    decode_records(_flip_a_byte_in_the_second_record(journal_of(("a", 1), ("b", 2), ("c", 3))))


def recovery_with_a_bad_checksum():
    blob = _flip_a_byte_in_the_second_record(journal_of(("a", 1), ("b", 2), ("c", 3)))
    eq(recover(Checkpoint(), blob), {"a": 1}, "recovered state")


def decode_with_a_differently_scoped_checksum():
    # Rebuild a record with a checksum taken over header+payload and it must
    # be rejected -- which also pins down what a correct checksum covers.
    import struct
    payload = b"\x00".join([b"1", b"a", b"1"])
    header = struct.pack(">II", len(payload), crc32(struct.pack(">I", len(payload)) + payload) & 0xFFFFFFFF)
    eq(decode_records(header + payload), [], "decoded records")


CHECKS = [
    ("recovery_from_lsn_2_of_3", recovery_from_lsn_2_of_3),
    ("recovery_from_lsn_1_of_1", recovery_from_lsn_1_of_1),
    ("recovery_from_lsn_2_of_2", recovery_from_lsn_2_of_2),
    ("checkpoint_after_recovery", checkpoint_after_recovery),
    ("two_recoveries_from_one_checkpoint", two_recoveries_from_one_checkpoint),
    ("decode_past_a_bad_checksum", decode_past_a_bad_checksum),
    ("recovery_with_a_bad_checksum", recovery_with_a_bad_checksum),
]

for name, fn in CHECKS:
    check(name, fn)

for f in FAILURES:
    print("FAIL: " + f)
print(f"RESULT {PASSED} passed {len(FAILURES)} failed")
sys.exit(1 if FAILURES else 0)
