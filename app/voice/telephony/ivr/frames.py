
from dataclasses import dataclass

from pipecat.frames.frames import DataFrame


@dataclass
class DTMFOutputFrame(DataFrame):
    digit: str = "2"
    duration_ms: int = 200
