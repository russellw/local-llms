"""What machine produced a number. Recorded in every results file.

Generation speed on a CPU is a property of the box as much as the model, so a
result without its host is not reproducible and barely comparable.
"""

from __future__ import annotations

import platform
from pathlib import Path


def host_info() -> dict:
    info = {
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "python": platform.python_version(),
    }
    try:
        cpu = [
            l.split(":", 1)[1].strip()
            for l in Path("/proc/cpuinfo").read_text().splitlines()
            if l.startswith("model name")
        ]
        if cpu:
            info["cpu"] = cpu[0]
            info["cpu_threads"] = len(cpu)
        mem = [
            l for l in Path("/proc/meminfo").read_text().splitlines()
            if l.startswith("MemTotal")
        ]
        if mem:
            info["mem_kb"] = int(mem[0].split()[1])
    except OSError:
        pass
    return info
