"""Content hashes and fingerprints. See docs/design.md."""

import hashlib


def digest(data):
    """The content hash of some bytes."""
    return hashlib.sha256(data).hexdigest()


def fingerprint(target, input_hashes):
    """What a run of `target` depends on, as one string.

    `input_hashes` maps each of the target's dependencies to its content hash.
    """
    h = hashlib.sha256()
    # The recipe version is an input too: bumping it must make the target run.
    h.update(f"version={target.version}\n".encode())
    # Sorted, so that listing the same dependencies in another order is not a
    # change.
    for dep in sorted(target.deps):
        h.update(f"{dep}={input_hashes[dep]}\n".encode())
    return h.hexdigest()
