"""Resource caps for running model-written code.

This is a guard against *accidents* -- runaway loops, memory bombs, a stray
`while True` -- not against hostile code. Model output is executed with your
user's privileges. See the security note in README.md.
"""

from __future__ import annotations

import os
import resource

MEM_LIMIT_BYTES = 2 * 1024**3  # 2 GiB: plenty for a test suite, fatal to a bomb.


def _limits() -> None:
    """Applied in the child between fork and exec."""
    resource.setrlimit(resource.RLIMIT_AS, (MEM_LIMIT_BYTES, MEM_LIMIT_BYTES))
    resource.setrlimit(resource.RLIMIT_NPROC, (256, 256))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024**2, 64 * 1024**2))
    os.setsid()  # own process group, so a timeout kills grandchildren too
