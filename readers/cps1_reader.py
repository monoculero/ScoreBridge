# readers/cps1_reader.py
from readers.base_reader import BaseHiScoreReader
from core.high_score_table import HighScoreTable
from core.score_entry import ScoreEntry

class CPS1HiScoreReader(BaseHiScoreReader):
    """
    Lector de archivos .hi para placas arcade Capcom CPS-1.
    Estructura típica: Registros de 8 bytes (4 bytes BCD score + 1 byte pad + 3 bytes ASCII iniciales).
    """

    def __init__(self, entry_size=8, score_bytes=4, score_offset=0, name_bytes=3, name_offset=5):
        self.entry_size = entry_size
        self.score_bytes = score_bytes
        self.score_offset = score_offset
        self.name_bytes = name_bytes
        self.name_offset = name_offset

    def read(self, file_path: str) -> HighScoreTable:
        table = HighScoreTable()
        
        with open(file_path, "rb") as f:
            data = f.read()

        num_entries = len(data) // self.entry_size

        for rank in range(num_entries):
            offset = rank * self.entry_size
            block = data[offset : offset + self.entry_size]

            # 1. Decodificar Puntuación (BCD)
            score_data = block[self.score_offset : self.score_offset + self.score_bytes]
            try:
                # El formato hex en BCD traduce directos los nibbles a números
                score_str = score_data.hex()
                score = int(score_str)
            except ValueError:
                score = 0

            # 2. Decodificar Iniciales (ASCII)
            name_data = block[self.name_offset : self.name_offset + self.name_bytes]
            name = name_data.decode("ascii", errors="replace").strip()

            # Agregar entrada a la tabla
            table.add_entry(ScoreEntry(rank=rank + 1, name=name, score=score))

        return table