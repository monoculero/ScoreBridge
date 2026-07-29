from dataclasses import dataclass, field

from core.score_entry import ScoreEntry


@dataclass
class HighScoreTable:
    game_name: str
    rom_name: str
    entries: list[ScoreEntry] = field(default_factory=list)
