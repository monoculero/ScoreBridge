import struct
from pathlib import Path
from typing import List, Optional


class ScoreEntry:
    def __init__(self, rank: int, player: str, score: int):
        self.rank = rank
        self.player = player
        self.score = score

    def __repr__(self):
        return f"<ScoreEntry #{self.rank} {self.player} - {self.score:,}>"


class HighScoreTable:
    def __init__(self, game_name: str, rom_name: str, entries: List[ScoreEntry]):
        self.game_name = game_name
        self.rom_name = rom_name
        self.entries = entries


class FBNeoReader:

    def _decode_bcd_score(self, score_bytes: bytes) -> int:
        """Decodifica un bloque de 4 bytes BCD a un entero."""
        try:
            hex_str = score_bytes.hex()
            return int(hex_str)
        except ValueError:
            return 0

    def read_sega_system16(self, file_path: str, rom_name: str) -> HighScoreTable:
        """
        Lector para Sega System 16 (Shinobi, Golden Axe, Altered Beast, etc.).
        Estructura: 8 bytes (4 bytes BCD Puntuación + 1 byte Ronda + 3 bytes Iniciales ASCII).
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        data = path.read_bytes()
        entries = []
        entry_size = 8
        
        # Leemos los primeros 160 bytes (20 registros principales)
        max_entries = min(20, len(data) // entry_size)

        for index in range(max_entries):
            offset = index * entry_size
            chunk = data[offset : offset + entry_size]

            if len(chunk) < 8:
                break

            score_bytes = chunk[:4]
            # byte 4 es la ronda/stage reached
            player_bytes = chunk[5:8]

            player = "".join(chr(b) for b in player_bytes if 32 <= b <= 126).strip()
            score = self._decode_bcd_score(score_bytes)

            if player and score > 0:
                entries.append(
                    ScoreEntry(
                        rank=index + 1,
                        player=player,
                        score=score
                    )
                )

        entries.sort(key=lambda x: x.score, reverse=True)
        for rank, entry in enumerate(entries, start=1):
            entry.rank = rank

        return HighScoreTable(
            game_name=rom_name.upper(),
            rom_name=rom_name,
            entries=entries
        )

    def read_cps_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Lector genérico para juegos Capcom (CPS1/CPS2)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        data = path.read_bytes()
        entries = []
        entry_size = 8

        num_entries = len(data) // entry_size

        for index in range(num_entries):
            offset = index * entry_size
            chunk = data[offset : offset + entry_size]

            if len(chunk) < 8:
                break

            part_a = chunk[:4]
            part_b = chunk[4:8]

            is_a_ascii = all(65 <= b <= 90 or b == 32 for b in part_a[:3])
            is_b_ascii = all(65 <= b <= 90 or b == 32 for b in part_b[:3])

            if is_b_ascii and not is_a_ascii:
                score_bytes = part_a
                player_bytes = part_b
            else:
                player_bytes = part_a
                score_bytes = part_b

            player = "".join(chr(b) for b in player_bytes if 32 <= b <= 126).strip()
            score = self._decode_bcd_score(score_bytes)

            if player and score > 0:
                entries.append(
                    ScoreEntry(
                        rank=index + 1,
                        player=player,
                        score=score
                    )
                )

        entries.sort(key=lambda x: x.score, reverse=True)
        for rank, entry in enumerate(entries, start=1):
            entry.rank = rank

        return HighScoreTable(
            game_name=rom_name.upper(),
            rom_name=rom_name,
            entries=entries
        )

    def read_dataeast_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """
        Lector para juegos Data East (Bad Dudes / DragonNinja, Sly Spy, etc.).
        Estructura: 3 bytes BCD Puntuación + 3 bytes Iniciales + 2 bytes Estado/Stage.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        data = path.read_bytes()
        entries = []
        entry_size = 8

        num_entries = len(data) // entry_size

        for index in range(num_entries):
            offset = index * entry_size
            chunk = data[offset : offset + entry_size]

            if len(chunk) < 8:
                break

            # En Bad Dudes: los primeros 3 bytes son la puntuación BCD
            score_bytes = chunk[:3]
            player_bytes = chunk[3:6]

            player = "".join(chr(b) for b in player_bytes if 32 <= b <= 126).strip()
            score = self._decode_bcd_score(score_bytes)

            if player and score > 0:
                entries.append(
                    ScoreEntry(
                        rank=index + 1,
                        player=player,
                        score=score
                    )
                )

        entries.sort(key=lambda x: x.score, reverse=True)
        for rank, entry in enumerate(entries, start=1):
            entry.rank = rank

        return HighScoreTable(
            game_name=rom_name.upper(),
            rom_name=rom_name,
            entries=entries
        )

    def read_table(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Lee la tabla de puntuaciones para cualquier ROM según su sistema."""
        rom_clean = rom_name.lower().strip()

        # ROMs de Sega System 16
        sega_sys16_roms = {"shinobi", "goldnaxe", "altbeast", "aliensyn", "passsht", "fantzone"}
        if rom_clean in sega_sys16_roms:
            return self.read_sega_system16(file_path, rom_clean)

        # ROMs de Data East
        dataeast_roms = {"baddudes", "drgnninja", "slyspy", "robocop"}
        if rom_clean in dataeast_roms:
            return self.read_dataeast_game(file_path, rom_clean)

        # Por defecto usa Capcom CPS1/CPS2
        return self.read_cps_game(file_path, rom_clean)

    def get_best_score_for_player(self, file_path: str, rom_name: str, initials: str) -> Optional[ScoreEntry]:
        """Obtiene la puntuación máxima para unas iniciales concretas."""
        table = self.read_table(file_path, rom_name)
        target = initials.strip().upper()

        matching = [e for e in table.entries if e.player.strip().upper() == target]
        return max(matching, key=lambda x: x.score) if matching else None