"""A second suite, on the axis the code tasks cannot see.

The code half of this benchmark asks a model to write one function from one
fully-specified prompt, with no tools, no prior state and one chance to answer.
That is the capability small models keep longest, which is why a 7B can score
respectably on it and still be useless driving an agent.

This half asks whether a model can operate an instrument: choose among tools,
recover when one refuses, go and find information nobody pushed at it, and stop
when it is done. Those are separate abilities from writing code, they fail in a
different order, and on the evidence they do not track model size.
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
