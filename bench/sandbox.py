"""Run model-generated code under a timeout and resource caps.

This is a guard against *accidents* -- runaway loops, memory bombs, a stray
`while True` -- not against hostile code. Model output is executed with your
user's privileges. See the security note in README.md.
"""

from __future__ import annotations

import os
import resource
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass

MEM_LIMIT_BYTES = 2 * 1024**3  # 2 GiB: plenty for a unit test, fatal to a bomb.


@dataclass
class ExecResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool = False

    @property
    def summary(self) -> str:
        if self.timed_out:
            return "timeout"
        if self.ok:
            return "pass"
        tail = (self.stderr or self.stdout).strip().splitlines()
        return tail[-1][:200] if tail else f"exit {self.returncode}"


def _limits() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (MEM_LIMIT_BYTES, MEM_LIMIT_BYTES))
    resource.setrlimit(resource.RLIMIT_NPROC, (256, 256))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024**2, 64 * 1024**2))
    os.setsid()  # own process group, so a timeout kills grandchildren too


def run_python_tests(solution: str, tests: str, timeout: float = 30.0) -> ExecResult:
    """Write `solution` as solution.py, run `tests` against it, report the verdict."""
    workdir = tempfile.mkdtemp(prefix="bench-")
    try:
        with open(os.path.join(workdir, "solution.py"), "w") as f:
            f.write(solution)
        test_path = os.path.join(workdir, "run_tests.py")
        with open(test_path, "w") as f:
            f.write(tests)

        env = {
            "PATH": "/usr/bin:/bin",
            "HOME": workdir,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": workdir,
        }
        try:
            proc = subprocess.run(
                [sys.executable, test_path],
                cwd=workdir,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                preexec_fn=_limits,
            )
        except subprocess.TimeoutExpired as e:
            return ExecResult(
                ok=False,
                stdout=_dec(e.stdout),
                stderr=_dec(e.stderr),
                returncode=-1,
                timed_out=True,
            )
        return ExecResult(
            ok=proc.returncode == 0,
            stdout=proc.stdout[-4000:],
            stderr=proc.stderr[-4000:],
            returncode=proc.returncode,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _dec(b) -> str:
    if b is None:
        return ""
    return b.decode(errors="replace") if isinstance(b, bytes) else str(b)
