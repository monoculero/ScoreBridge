from dataclasses import dataclass


@dataclass
class Game:
    name: str
    rom_name: str
    system: str
