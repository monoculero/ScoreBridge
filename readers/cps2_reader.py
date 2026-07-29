# readers/cps1_reader.py
from readers.base_reader import BaseHiScoreReader
from core.high_score_table import HighScoreTable
from core.score_entry import ScoreEntry

class CPS2HiScoreReader(BaseHiScoreReader):
    """
    Lector configurable para juegos CPS-2 con bloques separados de Score y Nombres.
    """
    def __init__(self, num_entries=5, score_start=0, score_len=4, name_start=20, name_len=3):
        self.num_entries = num_entries
        self.score_start = score_start
        self.score_len = score_len
        self.name_start = name_start
        self.name_len = name_len

    def read(self, file_path: str) -> HighScoreTable:
        table = HighScoreTable()
        with open(file_path, "rb") as f:
            data = f.read()

        for rank in range(self.num_entries):
            # Lectura de Score BCD
            s_off = self.score_start + (rank * self.score_len)
            score_bytes = data[s_off : s_off + self.score_len]
            score = int(score_bytes.hex()) if score_bytes else 0

            # Lectura de Nombres
            n_off = self.name_start + (rank * self.name_len)
            name_bytes = data[n_off : n_off + self.name_len]
            name = name_bytes.decode("ascii", errors="replace").strip()

            table.add_entry(ScoreEntry(rank=rank + 1, name=name, score=score))

        return table