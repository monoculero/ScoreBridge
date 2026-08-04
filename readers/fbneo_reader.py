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
        """Decodes a BCD block of any length to an integer."""
        try:
            hex_str = score_bytes.hex()
            return int(hex_str)
        except ValueError:
            return 0

    def read_capcom_z80_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Capcom Z80 games reader (1984-1987)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()
        
        is_1942 = clean_rom in {"1942", "1942a", "1942b", "1942w"}
        is_gng = clean_rom in {"gng", "gnga", "makaimur", "makaimurc"}
        is_commando = clean_rom in {"commando", "commandou", "spacegun"} or (len(data) == 94 and not is_gng)
        is_blktiger = clean_rom in {"blktiger", "blktigr", "blkdrgon", "blkdrgno"} or len(data) == 88
        is_gunsmoke = (clean_rom in {"gunsmoke", "gunsmrom"}) or (len(data) == 80 and not is_blktiger)

        if is_1942:
            start_offset = 0x0000
            entry_size = 16
            num_entries = 5
        elif is_gng:
            start_offset = 0x0014
            entry_size = 7
            num_entries = 10
        elif is_commando:
            start_offset = 0x0000
            entry_size = 13
            num_entries = 7
        elif is_blktiger:
            start_offset = 0x0000
            entry_size = 16
            num_entries = 5
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

            if is_1942:
                score_bytes = chunk[1:5]
                score = self._decode_bcd_score(score_bytes)

                name_bytes = chunk[5:13]
                player_chars = []
                for b in name_bytes:
                    if 0x0A <= b <= 0x23:
                        player_chars.append(chr(ord('A') + (b - 0x0A)))
                    elif b == 0x24:
                        player_chars.append(".")
                    elif b == 0x25:
                        player_chars.append("-")
                    elif 32 <= b <= 126 and chr(b).isalnum():
                        player_chars.append(chr(b))
                    else:
                        player_chars.append(" ")

                player = "".join(player_chars).strip() or "AAA"

            elif is_gng:
                score_bytes = chunk[:4]
                name_bytes = chunk[4:7]

                player = "".join(chr(b) for b in name_bytes if 32 <= b <= 126).strip() or "AAA"

                bcd_str = f"{score_bytes[3]:02X}{score_bytes[2]:02X}{score_bytes[1]:02X}{score_bytes[0]:02X}"
                try:
                    raw_score = int(bcd_str)
                    score = raw_score * 100 if raw_score > 0 else 10000
                except ValueError:
                    score = 10000

            elif is_commando:
                score_bytes = chunk[:3]
                name_bytes = chunk[3:13]

                player = "".join(chr(b) for b in name_bytes if 32 <= b <= 126).replace(".", "").strip() or "AAA"
                score = self._decode_bcd_score(score_bytes) * 10

            elif is_blktiger:
                score_bytes = chunk[4:8]
                score_str = "".join(f"{b:X}" for b in score_bytes)
                try:
                    score = int(score_str) * 100
                except ValueError:
                    score = 0

                name_bytes = chunk[8:16]
                player = "".join(chr(b) for b in name_bytes if 32 <= b <= 126).strip() or "AAA"

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

                player = "".join(player_chars).strip() or "AAA"

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

    def read_sega_system16(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Sega System 16 / System 18 games reader (includes Golden Axe and ESWAT)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()

        # Manejo específico para Golden Axe
        if clean_rom in {"goldnaxe", "goldnaxj", "goldnaxu", "goldnaxe1", "goldnaxe2"}:
            scores = []
            if len(data) >= 2:
                top_record = int.from_bytes(data[0:2], byteorder="big")
                if top_record > 0:
                    scores.append(top_record)

            for i in range(10):
                off = 4 + (i * 2)
                if off + 2 <= len(data):
                    val = int.from_bytes(data[off : off + 2], byteorder="big")
                    if val > 0 and val not in scores:
                        scores.append(val)

            scores.sort(reverse=True)

            for rank, score in enumerate(scores, start=1):
                entries.append(
                    ScoreEntry(
                        rank=rank,
                        player="---",
                        score=score
                    )
                )

            return HighScoreTable(
                game_name=clean_rom.upper(),
                rom_name=clean_rom,
                entries=entries
            )

        # Manejo específico para ESWAT (Bloques de 10 bytes)
        if clean_rom in {"eswat", "eswatbl"}:
            entry_size = 10
            num_entries = len(data) // entry_size

            for index in range(num_entries):
                offset = index * entry_size
                if offset + 8 > len(data):
                    break

                chunk = data[offset : offset + entry_size]

                # La puntuación está codificada en el byte de la posición 1
                score_byte = chunk[1]
                high = (score_byte >> 4) & 0x0F
                low = score_byte & 0x0F
                score = (high * 10 + low) * 10000

                # Las iniciales ocupan los bytes de las posiciones 4, 5 y 6
                player_bytes = chunk[4:7]
                player_chars = []
                for b in player_bytes:
                    if 32 <= b <= 126:
                        player_chars.append(chr(b))
                    else:
                        player_chars.append(".")

                player = "".join(player_chars).strip() or "..."

                if score > 0:
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

        # Lector genérico para el resto de juegos de Sega System 16
        entry_size = 8
        max_entries = min(20, len(data) // entry_size)

        for index in range(max_entries):
            offset = index * entry_size
            chunk = data[offset : offset + entry_size]

            if len(chunk) < 8:
                break

            score_bytes = chunk[:4]
            player_bytes = chunk[5:8]

            if not all(32 <= b <= 126 for b in player_bytes):
                break

            player = "".join(chr(b) for b in player_bytes).strip()
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
            game_name=clean_rom.upper(),
            rom_name=clean_rom,
            entries=entries
        )

    def read_cps_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Standard Capcom CPS reader, with custom handling for specific sub-variants like 3wonders."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        
        rom_clean = Path(rom_name).stem.lower().strip()

        if rom_clean == "3wonders":
            for i in range(0, len(data) - 4):
                chunk = data[i : i + 3]
                if all(65 <= b <= 90 or b == 32 for b in chunk):
                    player = "".join(chr(b) for b in chunk).strip()
                    if len(player) >= 2 and i >= 4:
                        score_bytes = data[i - 4 : i]
                        score = self._decode_bcd_score(score_bytes)
                        if score == 0:
                            try:
                                score = int.from_bytes(score_bytes, byteorder='big')
                            except ValueError:
                                score = 0
                        if score > 0 and not any(e.score == score and e.player == player for e in entries):
                            entries.append(ScoreEntry(rank=0, player=player, score=score))

        elif rom_clean in {"dino", "dinou"}:
            entry_size = 16
            max_entries = 10

            for index in range(min(len(data) // entry_size, max_entries)):
                offset = index * entry_size
                chunk = data[offset : offset + entry_size]

                if len(chunk) < 8:
                    break

                score = self._decode_bcd_score(chunk[0:4])
                player = chunk[4:8].decode("ascii", errors="ignore").strip()
                player = " ".join(player.split()) or "AAA"

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
            num_entries = len(data) // entry_size
            for index in range(num_entries):
                offset = index * entry_size
                chunk = data[offset : offset + entry_size]
                if len(chunk) < 8:
                    break
                
                part_a = chunk[:4]
                part_b = chunk[4:8]

                is_b_ascii = all(65 <= b <= 90 or b == 32 for b in part_b[:3])
                if is_b_ascii:
                    score_bytes = part_a
                    player_bytes = part_b
                else:
                    score_bytes = part_b
                    player_bytes = part_a

                player = "".join(chr(b) for b in player_bytes if 32 <= b <= 126).strip()
                score = self._decode_bcd_score(score_bytes)

                if player and score > 0:
                    entries.append(ScoreEntry(rank=0, player=player, score=score))

        entries.sort(key=lambda x: x.score, reverse=True)
        entries = entries[:10]
        for rank, entry in enumerate(entries, start=1):
            entry.rank = rank

        return HighScoreTable(
            game_name=rom_clean.upper(),
            rom_name=rom_clean,
            entries=entries
        )

    def read_dataeast_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """
        Data East games reader.
        Uses an algorithmic mathematical formula to decode font tiles for Captain America.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()

        is_captaven = clean_rom in {"captaven", "captavena", "captavenj", "captavenu"}

        if is_captaven:
            entry_size = 32
            num_entries = min(5, len(data) // entry_size)

            def decode_captaven_char(b: int) -> str:
                if b == 0 or b == 0xFF:
                    return ""
                
                # Símbolos especiales (ej: el punto '.')
                if b == 0x30:
                    return "."

                # Mayúsculas: Base 0x58, saltos de 4 en 4
                if (b - 0x58) % 4 == 0:
                    idx = (b - 0x58) // 4
                    if 0 <= idx < 26:
                        return chr(ord('A') + idx)

                # Minúsculas: Base 0xC0, saltos de 4 en 4
                if (b - 0xC0) % 4 == 0:
                    idx = (b - 0xC0) // 4
                    if 0 <= idx < 26:
                        return chr(ord('a') + idx)

                return ""

            for index in range(num_entries):
                offset = index * entry_size
                chunk = data[offset : offset + entry_size]

                if len(chunk) < 16:
                    break

                # Puntuación en uint32 Little-Endian (bytes 0..3)
                score_bytes = chunk[0:4]
                try:
                    score = struct.unpack("<I", score_bytes)[0]
                except struct.error:
                    score = 0

                # Extracción algorítmica de iniciales en offsets 4, 8 y 12
                c1 = decode_captaven_char(chunk[4])
                c2 = decode_captaven_char(chunk[8])
                c3 = decode_captaven_char(chunk[12])

                player = f"{c1}{c2}{c3}".strip() or "AAA"

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
            game_name=clean_rom.upper(),
            rom_name=clean_rom,
            entries=entries
        )

    def read_irem_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Irem M-62 games reader (Kung-Fu Master / Spartan X)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

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
            score = self._decode_bcd_score(score_bytes) * 10

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
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()

        if clean_rom in {"gberet", "gbereto"}:
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
                    score = self._decode_bcd_score(s_bytes)

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

        elif clean_rom == "kicker":
            header_offset = 24
            entry_size = 8
            
            ranking_data = data[header_offset:]
            num_entries = len(ranking_data) // entry_size

            def decode_kicker_char(b: int) -> str:
                if 0x11 <= b <= 0x2A:
                    return chr(ord('A') + (b - 0x11))
                elif b in (0x1C, 0x2C, 0x2D):
                    return "."
                elif 0x01 <= b <= 0x0A:
                    return str(b - 1)
                elif b in (0x00, 0x10):
                    return " "
                return ""

            for index in range(min(num_entries, 8)):
                offset = index * entry_size
                chunk = ranking_data[offset : offset + entry_size]

                if len(chunk) < 6:
                    break

                score = self._decode_bcd_score(chunk[0:3])

                name_bytes = chunk[3:6]
                player_chars = [decode_kicker_char(b) for b in name_bytes]
                player = "".join(player_chars).strip()
                player = " ".join(player.split()) or "AAA"

                if score > 0:
                    entries.append(
                        ScoreEntry(
                            rank=len(entries) + 1,
                            player=player,
                            score=score
                        )
                    )

        elif clean_rom == "fastlane":
            entry_size = 8
            num_entries = 10

            def decode_fastlane_char(b: int) -> str:
                if 0x11 <= b <= 0x2A:
                    return chr(ord('A') + (b - 0x11))
                elif b in (0x0C, 0x0D, 0x1C, 0x2D):
                    return "."
                elif 0x01 <= b <= 0x0A:
                    return str(b - 1)
                elif b in (0x00, 0x10):
                    return " "
                return ""

            for index in range(num_entries):
                offset = index * entry_size
                chunk = data[offset : offset + entry_size]

                if len(chunk) < entry_size:
                    break

                score = self._decode_bcd_score(chunk[0:4])

                name_bytes = chunk[4:7]
                player_chars = [decode_fastlane_char(b) for b in name_bytes]
                player = "".join(player_chars).strip()
                player = " ".join(player.split()) or "AAA"

                if score > 0:
                    entries.append(
                        ScoreEntry(
                            rank=len(entries) + 1,
                            player=player,
                            score=score
                        )
                    )

        elif clean_rom == "yiear":
            start_offset = 18
            entry_size = 14
            max_entries = (len(data) - start_offset) // entry_size

            def decode_yiear_char(b: int) -> str:
                if 0x11 <= b <= 0x2A:
                    return chr(ord('A') + (b - 0x11))
                elif b in (0x1C, 0x2B, 0x2D):
                    return "."
                elif 0x01 <= b <= 0x0A:
                    return str(b - 1)
                elif b in (0x00, 0x10):
                    return " "
                return ""

            for index in range(max_entries):
                offset = start_offset + (index * entry_size)
                chunk = data[offset : offset + entry_size]

                if len(chunk) < entry_size:
                    break

                name_offset_adjust = index + 1
                target_offset = start_offset + (name_offset_adjust * entry_size)
                
                if target_offset + 9 <= len(data):
                    name_chunk = data[target_offset : target_offset + 9]
                else:
                    name_chunk = chunk[0:9]

                player_chars = [decode_yiear_char(b) for b in name_chunk]
                player = "".join(player_chars).strip()
                player = " ".join(player.split()) or "AAA"

                score_bytes = chunk[11:13]
                score = self._decode_bcd_score(score_bytes) * 10 if len(score_bytes) == 2 else 0

                if score > 0:
                    entries.append(
                        ScoreEntry(
                            rank=len(entries) + 1,
                            player=player,
                            score=score
                        )
                    )

        elif clean_rom in {"trackfld"}:
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

                player = "".join(player_chars).strip() or "AAA"
                score = self._decode_bcd_score(score_bytes) * 1000

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
        """Lector para juegos de TAD Corporation."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()

        if clean_rom == "cabal":
            i = 0
            while i < len(data) - 7:
                chunk = data[i : i + 3]
                if all(65 <= b <= 90 for b in chunk):
                    player = "".join(chr(b) for b in chunk).strip()
                    if len(player) == 3:
                        score_bytes = data[i + 4 : i + 8]
                        
                        score = self._decode_bcd_score(score_bytes)
                        if score == 0:
                            try:
                                score = int.from_bytes(score_bytes, byteorder='little')
                            except ValueError:
                                score = 0

                        if score > 0:
                            real_score = score // 100
                            entries.append(
                                ScoreEntry(
                                    rank=0,
                                    player=player,
                                    score=real_score
                                )
                            )
                            i += 7
                            continue
                i += 1
        elif clean_rom == "bloodbro":
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
                
                try:
                    score = int(f"{hi_part}{lo_part}") * 10
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
        elif clean_rom == "toki":
            for i in range(20):
                score_offset = i * 4
                name_offset = 0x0050 + (i * 4)
                
                if score_offset + 4 > len(data) or name_offset + 4 > len(data):
                    break
                
                score_bytes = data[score_offset : score_offset + 4]
                name_bytes = data[name_offset : name_offset + 4]
                
                score = self._decode_bcd_score(score_bytes)
                if score == 0:
                    try:
                        score = int.from_bytes(score_bytes, byteorder='big')
                    except ValueError:
                        score = 0
                
                player = "".join(chr(b) for b in name_bytes if 32 <= b <= 126).strip() or "TAD"
                
                if score > 0:
                    entries.append(
                        ScoreEntry(
                            rank=i + 1,
                            player=player,
                            score=score
                        )
                    )

        entries.sort(key=lambda x: x.score, reverse=True)
        entries = entries[:10]
        for rank, entry in enumerate(entries, start=1):
            entry.rank = rank

        return HighScoreTable(
            game_name=clean_rom.upper(),
            rom_name=clean_rom,
            entries=entries
        )

    def read_gaelco_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Gaelco games reader (Big Karnak, etc.)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        
        entry_size = 16
        num_entries = 10

        for index in range(num_entries):
            offset = index * entry_size
            chunk = data[offset : offset + entry_size]

            if len(chunk) < entry_size:
                break

            score_bytes = chunk[:4]
            try:
                score = struct.unpack(">I", score_bytes)[0]
            except (struct.error, ValueError):
                score = 0

            name_bytes = chunk[4:11]
            player_chars = []
            for b in name_bytes:
                if b == 0xFF:
                    break
                if 32 <= b <= 126:
                    player_chars.append(chr(b))

            player = "".join(player_chars).strip() or "AAA"

            if score > 0:
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

        clean_rom = Path(rom_name).stem.lower().strip()
        return HighScoreTable(
            game_name=clean_rom.upper(),
            rom_name=clean_rom,
            entries=entries
        )

    def read_table(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Read the scores table for any ROM based on your arcade system."""
        rom_clean = Path(rom_name).stem.lower().strip()

        capcom_z80_roms = {
            "gng","gnga","makaimur","makaimurc",
            "1942",
            "1943",
            "1943kai",
            "commando", "commandou",
            "gunsmoke","gunsmrom",
            "vulgus",
            "exedexes", 
            "sectionz",
            "trojan",
            "blktiger","blktigr","blkdrgon","blkdrgno"
        }
        if rom_clean in capcom_z80_roms:
            return self.read_capcom_z80_game(file_path, rom_clean)

        gaelco_roms = {
            "bigkarnk","bigkarnka"
        }
        if rom_clean in gaelco_roms:
            return self.read_gaelco_game(file_path, rom_clean)

        cps_roms = {
            "3wonders",
            "sf2",
            "ffight",
            "dino","dinou"
        }
        if rom_clean in cps_roms:
            return self.read_cps_game(file_path, rom_clean)

        sega_sys16_roms = {
            "shinobi",
            "goldnaxe","goldnaxj", "goldnaxu", "goldnaxe1", "goldnaxe2",
            "altbeast",
            "aliensyn",
            "passsht",
            "fantzone",
            "eswat","eswatbl"
        }
        if rom_clean in sega_sys16_roms:
            return self.read_sega_system16(file_path, rom_clean)

        dataeast_roms = {
            "baddudes","drgnninja",
            "slyspy",
            "robocop",
            "captaven","captavena","captavenj","captavenu"
        }
        if rom_clean in dataeast_roms:
            return self.read_dataeast_game(file_path, rom_clean)

        irem_roms = {
            "kungfum","kungfumr",
            "spartanx",
            "ldrun",
            "kidniki"
        }
        if rom_clean in irem_roms:
            return self.read_irem_game(file_path, rom_clean)

        konami_roms = {
            "gberet","gbereto",
            "fastlane",
            "kicker",
            "trackfld",
            "yiear"
        }
        if rom_clean in konami_roms:
            return self.read_konami_game(file_path, rom_clean)

        tad_roms = {
            "bloodbro","bloodbrol",
            "cabal",
            "toki"
        }
        if rom_clean in tad_roms:
            return self.read_tad_game(file_path, rom_clean)

        raise ValueError(f"ROM no soportada o no registrada en el sistema: '{rom_name}' (limpia: '{rom_clean}')")

    def get_best_score_for_player(self, file_path: str, rom_name: str, initials: str) -> Optional[ScoreEntry]:
        """Get the highest score for one or more players separated by commas."""
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