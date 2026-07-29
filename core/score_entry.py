from dataclasses import dataclass


@dataclass
class ScoreEntry:
    rank: int
    player: str
    score: int
