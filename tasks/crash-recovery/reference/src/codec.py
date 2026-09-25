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
        # The header is part of the record: a journal that ends inside the
        # payload is torn, and forgetting these 8 bytes accepts garbage.
        if pos + HEADER.size + length > len(blob):
            break
        payload = blob[pos + HEADER.size:pos + HEADER.size + length]
        if crc32(payload) & 0xFFFFFFFF != checksum:
            # Stop, do not skip. A journal is a sequence; records after a
            # gap cannot be trusted to mean what they say.
            break
        out.append(_parse(payload))
        pos += HEADER.size + length
    return out
