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
        Lector corregido para juegos Data East (Bad Dudes / DragonNinja, etc.).
        Estructura: 3 bytes Iniciales + 1 byte relleno + 3 bytes Puntuación BCD + 1 byte extra.
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

            player_bytes = chunk[:3]
            score_bytes = chunk[4:7]

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

    def read_irem_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """
        Lector para juegos Irem M-62 (Kung-Fu Master / Spartan X).
        Estructura por registro (5 bytes): 2 bytes Puntuación BCD (Little-Endian) + 3 bytes Iniciales ASCII.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        data = path.read_bytes()
        entries = []
        entry_size = 5

        num_entries = len(data) // entry_size

        for index in range(num_entries):
            offset = index * entry_size
            chunk = data[offset : offset + entry_size]

            if len(chunk) < 5:
                break

            score_bytes = chunk[:2]
            player_bytes = chunk[2:5]

            player = "".join(chr(b) for b in player_bytes if 32 <= b <= 126).strip()
            score_hex = f"{score_bytes[0]:02X}{score_bytes[1]:02X}"
            
            try:
                score = int(score_hex) * 10
            except ValueError:
                score = 0

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

    def read_konami_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()
        is_gberet = clean_rom in {"gberet", "gbereto"} or len(data) == 63

        if is_gberet:
            num_entries = 5
            
            def decode_gberet_char(b: int) -> str:
                if 0x11 <= b <= 0x2A:
                    return chr(ord('A') + (b - 0x11))
                elif 0x01 <= b <= 0x0A:
                    return str(b - 0x01)
                elif 0x1B <= b <= 0x24:
                    return str(b - 0x1B)
                elif b in (0x00, 0x10, 0x24, 0x25):
                    return " "
                elif 32 <= b <= 126:
                    return chr(b)
                return "?"

            for index in range(num_entries):
                score_offset = index * 3
                name_offset = 0x1E + (index * 3)

                score = 0
                if score_offset + 3 <= len(data):
                    s_bytes = data[score_offset : score_offset + 3]
                    score_str = "".join(f"{b:02X}" for b in s_bytes)
                    try:
                        score = int(score_str)
                    except ValueError:
                        score = 0

                player = "AAA"
                if name_offset + 3 <= len(data):
                    n_bytes = data[name_offset : name_offset + 3]
                    player_chars = [decode_gberet_char(b) for b in n_bytes]
                    extracted = "".join(player_chars).strip()
                    if extracted:
                        player = extracted

                if score > 0:
                    entries.append(
                        ScoreEntry(
                            rank=index + 1,
                            player=player,
                            score=score
                        )
                    )
        else:
            entry_size = 8
            num_entries = min(10, len(data) // entry_size)

            for index in range(num_entries):
                offset = index * entry_size
                chunk = data[offset : offset + entry_size]

                if len(chunk) < 7:
                    break

                score_bytes = chunk[1:3]
                konami_letters = chunk[4:7]

                player_chars = []
                for b in konami_letters:
                    if 0x0D <= b <= 0x26:
                        player_chars.append(chr(ord('A') + (b - 0x0D)))
                    elif b in (0x00, 0x0C, 0x20):
                        player_chars.append(" ")
                    elif 0x01 <= b <= 0x0A:
                        player_chars.append(str(b - 1))
                    else:
                        player_chars.append("?")

                player = "".join(player_chars).strip()
                if not player:
                    player = "AAA"

                score_hex = f"{score_bytes[0]:02X}{score_bytes[1]:02X}"
                try:
                    score = int(score_hex) * 1000
                except ValueError:
                    score = 0

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
            game_name=clean_rom.upper(),
            rom_name=clean_rom,
            entries=entries
        )

    def read_tad_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Lector para juegos de TAD Corporation (Blood Bros, Cabal, Toki, etc.)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        data = path.read_bytes()
        entries = []
        
        start_offset = 0x0028
        entry_size = 8
        max_entries = (len(data) - start_offset) // entry_size

        for index in range(max_entries):
            offset = start_offset + (index * entry_size)
            chunk = data[offset : offset + entry_size]

            if len(chunk) < 8 or all(b == 0 for b in chunk):
                break

            player_bytes = chunk[1:4]
            score_bytes = chunk[4:8]

            player = "".join(chr(b) for b in player_bytes if 32 <= b <= 126).strip()
            hi_part = f"{score_bytes[2]:02X}{score_bytes[3]:02X}"
            lo_part = f"{score_bytes[0]:02X}"
            score_str = f"{hi_part}{lo_part}"
            
            try:
                score = int(score_str) * 10
            except ValueError:
                score = 0

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

    def read_capcom_z80_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Lector unificado para la era Capcom Z80 (1984-1987)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()
        
        is_gng = clean_rom in {"gng", "gnga", "makaimur", "makaimurc"}
        is_commando = clean_rom in {"commando", "commandou", "spacegun"} or (len(data) == 94 and not is_gng)
        is_gunsmoke = clean_rom in {"gunsmoke", "gunsmrom"} or len(data) == 88

        if is_gng:
            start_offset = 0x0014
            entry_size = 7
            num_entries = 10
        elif is_commando:
            start_offset = 0x0000
            entry_size = 13
            num_entries = 7
        elif is_gunsmoke:
            start_offset = 0x0000
            entry_size = 16
            num_entries = 5
        else:
            start_offset = 0x0000
            entry_size = 16
            num_entries = min(10, len(data) // entry_size)

        for index in range(num_entries):
            offset = start_offset + (index * entry_size)
            chunk = data[offset : offset + entry_size]

            if len(chunk) < entry_size:
                break

            if is_gng:
                score_bytes = chunk[:4]
                name_bytes = chunk[4:7]

                player = "".join(chr(b) for b in name_bytes if 32 <= b <= 126).strip()
                if not player:
                    player = "AAA"

                bcd_str = f"{score_bytes[3]:02X}{score_bytes[2]:02X}{score_bytes[1]:02X}{score_bytes[0]:02X}"
                try:
                    raw_score = int(bcd_str)
                    score = raw_score * 100 if raw_score > 0 else 10000
                except ValueError:
                    score = 10000

            elif is_commando:
                score_bytes = chunk[:3]
                name_bytes = chunk[3:13]

                player = "".join(chr(b) for b in name_bytes if 32 <= b <= 126).replace(".", "").strip()
                if not player:
                    player = "AAA"

                bcd_str = f"{score_bytes[0]:02X}{score_bytes[1]:02X}{score_bytes[2]:02X}"
                try:
                    score = int(bcd_str) * 10
                except ValueError:
                    score = 0

            elif is_gunsmoke:
                score_bytes = chunk[0:4]
                name_bytes = chunk[4:16]

                player_chars = []
                for b in name_bytes:
                    if 0x0A <= b <= 0x23:
                        player_chars.append(chr(ord('A') + (b - 0x0A)))
                    elif 32 <= b <= 126 and chr(b).isalnum():
                        player_chars.append(chr(b))

                player = "".join(player_chars).strip()
                if not player or len(player) < 2:
                    player = "AAA"

                score_hex = f"{score_bytes[2]:02X}{score_bytes[1]:02X}{score_bytes[0]:02X}"
                try:
                    raw_score = int(score_hex)
                    score = raw_score * 10 if raw_score > 0 else 10000
                except ValueError:
                    score = 10000

            else:
                score_bytes = chunk[1:5]
                name_bytes = chunk[7:15]

                player_chars = []
                for b in name_bytes:
                    if 0x0A <= b <= 0x23:
                        player_chars.append(chr(ord('A') + (b - 0x0A)))
                    elif b == 0x24:
                        player_chars.append(".")
                    elif b == 0x25:
                        player_chars.append("-")
                    elif b in (0x30, 0x00, 0xFF):
                        player_chars.append(" ")
                    elif 0x01 <= b <= 0x09:
                        player_chars.append(str(b - 1))
                    else:
                        player_chars.append(" ")

                player = "".join(player_chars).strip()
                if not player:
                    player = "AAA"

                score_hex = f"{score_bytes[2]:02X}{score_bytes[1]:02X}{score_bytes[0]:02X}"
                try:
                    score = int(score_hex) * 10
                except ValueError:
                    score = 0

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
            game_name=clean_rom.upper(),
            rom_name=clean_rom,
            entries=entries
        )

    def read_table(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Lee la tabla de puntuaciones para cualquier ROM según su sistema arcade."""
        rom_clean = Path(rom_name).stem.lower().strip()

        capcom_z80_roms = {
            "gng",
            "gnga",
            "makaimur",
            "makaimurc",
            "1942",
            "1943",
            "1943kai",
            "commando", 
            "gunsmoke",
            "vulgus",
            "exedexes", 
            "sectionz",
            "trojan"
        }
        if rom_clean in capcom_z80_roms:
            return self.read_capcom_z80_game(file_path, rom_clean)

        sega_sys16_roms = {
            "shinobi",
            "goldnaxe",
            "altbeast",
            "aliensyn",
            "passsht",
            "fantzone"
        }
        if rom_clean in sega_sys16_roms:
            return self.read_sega_system16(file_path, rom_clean)

        dataeast_roms = {
            "baddudes",
            "drgnninja",
            "slyspy",
            "robocop"
        }
        if rom_clean in dataeast_roms:
            return self.read_dataeast_game(file_path, rom_clean)

        irem_roms = {
            "kungfum",
            "kungfumr",
            "spartanx",
            "ldrun",
            "kidniki"
        }
        if rom_clean in irem_roms:
            return self.read_irem_game(file_path, rom_clean)

        konami_roms = {"gberet", "gbereto", "fastlane", "kicker", "trackfld", "yiear"}
        if rom_clean in konami_roms:
            return self.read_konami_game(file_path, rom_clean)

        tad_roms = {"bloodbro", "bloodbrol", "cabal", "toki"}
        if rom_clean in tad_roms:
            return self.read_tad_game(file_path, rom_clean)

        # Por defecto usa Capcom CPS1/CPS2
        return self.read_cps_game(file_path, rom_clean)

    def get_best_score_for_player(self, file_path: str, rom_name: str, initials: str) -> Optional[ScoreEntry]:
        """Obtiene la puntuación máxima para una o varias iniciales separadas por comas."""
        table = self.read_table(file_path, rom_name)
        target_initials_list = [init.strip().upper() for init in initials.split(",") if init.strip()]

        best_entry = None
        for target in target_initials_list:
            matching = [e for e in table.entries if e.player.strip().upper() == target]
            if matching:
                player_best = max(matching, key=lambda x: x.score)
                if not best_entry or player_best.score > best_entry.score:
                    best_entry = player_best

        return best_entry