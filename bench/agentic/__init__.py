"""One suite: realistic coding work, driven through a tool loop.

A task is a small broken Python project and a test suite the model cannot read
but can run as often as it likes. Passing means the suite passes against what
the model left on disk -- so a model has to operate the tools, navigate code it
did not write, work out what is wrong, change it correctly, and check. Those
abilities fail in different places, and the report keeps them in separate
columns rather than averaging them into one number.
"""

from .tasks import Task, load_tasks
from .loop import TaskResult, run_task
from .runner import detect_protocol, run_suite
from . import report

__all__ = [
    "Task",
    "TaskResult",
    "load_tasks",
    "run_task",
    "run_suite",
    "detect_protocol",
    "report",
]
