"""A second suite, on what the code tasks cannot see.

The code half of this benchmark asks a model to write one function from one
fully-specified prompt, with no tools, no prior state and one chance to answer.
That is the capability small models keep longest, which is why a 7B can score
respectably on it and still be useless driving an agent.

This half asks whether a model can operate an instrument: choose among tools,
recover when one refuses, go and find information nobody pushed at it, and stop
when it is done. A good code score does not carry over -- it is a bar a model
can clear and still score zero here. It does not, on the evidence, run the
other way either: gpt-oss-20b and Qwen3-Coder-30B are 23 code points apart and
tie at 75% here, so nothing yet shows the two orderings disagreeing. Keep the
scores apart because this is the harder test, not because they are known to
rank models differently.
"""

from .episodes import EPISODES, Episode, load_episodes
from .loop import EpisodeResult, run_episode
from .runner import detect_protocol, run_toolloop

__all__ = [
    "EPISODES",
    "Episode",
    "EpisodeResult",
    "load_episodes",
    "run_episode",
    "run_toolloop",
    "detect_protocol",
]
