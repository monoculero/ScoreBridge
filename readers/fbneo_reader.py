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
        
        # Detección por conjunto de ROMs y tamaño seguro de volcado
        is_1942 = clean_rom in {"1942", "1942a", "1942b", "1942w"}
        is_gng = clean_rom in {"gng", "gnga", "gngj", "gngt", "makaimur", "makaimura", "makaimurc"}
        is_gunsmoke = clean_rom in {"gunsmoke", "gunsmrom", "gunsmokuj", "gunsmok2", "gunsmokej"} or (len(data) == 88 and "gun" in clean_rom)
        is_blktiger = clean_rom in {"blktiger", "blktigr", "blkdrgon", "blkdrgno"} or (len(data) == 88 and not is_gng and not is_gunsmoke)
        is_commando = clean_rom in {"commando", "commandou", "commandoj", "spacegun"} or (len(data) == 94 and not is_gng)

        if is_1942:
            def decode_1942_str(name_bytes: bytes) -> str:
                chars = []
                for b in name_bytes:
                    if 0x0A <= b <= 0x23:
                        chars.append(chr(ord('A') + (b - 0x0A)))
                    elif b == 0x38:
                        chars.append("©")
                    elif b in (0x30, 0x00):
                        chars.append(" ")  # 0x30 y 0x00 son espacios de relleno en 1942
                    elif b in (0x24, 0xFA):
                        chars.append("·")
                    elif b == 0x25:
                        chars.append("-")
                    elif 32 <= b <= 126 and chr(b).isalnum():
                        chars.append(chr(b))
                    else:
                        chars.append(" ")
                return "".join(chars).strip() or "AAA"

            # 1.º Puesto (TOP Score independiente ubicado en 0x0172)
            if len(data) >= 0x017D:
                top_score_bytes = data[0x0172:0x0175]
                bcd_str = "".join(f"{b:02X}" for b in top_score_bytes)
                top_score = int(bcd_str) if bcd_str.isdigit() else 0
                top_name = decode_1942_str(data[0x0175:0x017D])
                entries.append(ScoreEntry(rank=1, player=top_name, score=top_score))

            # Puestos del 2.º al 5.º (bloques de 16 bytes desde 0x0000)
            for i in range(4):
                off = i * 16
                chunk = data[off : off + 16]
                if len(chunk) < 16:
                    break
                score_bytes = chunk[2:5]
                bcd_str = "".join(f"{b:02X}" for b in score_bytes)
                score = int(bcd_str) if bcd_str.isdigit() else 0
                player = decode_1942_str(chunk[5:15])
                entries.append(ScoreEntry(rank=i + 2, player=player, score=score))

        else:
            if is_gng:
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

                if is_gng:
                    score_bytes = chunk[:4]
                    bcd_str = "".join(f"{b:02X}" for b in score_bytes)
                    score = int(bcd_str) if bcd_str.isdigit() else 10000

                    name_bytes = chunk[4:7]
                    player = "".join(chr(b) if 32 <= b <= 126 else "·" for b in name_bytes).strip() or "AAA"

                elif is_commando:
                    score_bytes = chunk[:3]
                    name_bytes = chunk[3:13]

                    raw_player = "".join(chr(b) for b in name_bytes if 32 <= b <= 126 or b in (0xB7, 0xFA)).replace(".", "·")
                    player = raw_player.rstrip("· ").strip() or "AAA"
                    score = self._decode_bcd_score(score_bytes) * 10

                elif is_blktiger:
                    score_digits = chunk[3:8]
                    score_str = "".join(str(b) for b in score_digits)
                    score = int(score_str) * 10 if score_str.isdigit() else 0

                    name_bytes = chunk[8:16]
                    player = "".join(chr(b) for b in name_bytes if 32 <= b <= 126).strip() or "AAA"

                elif is_gunsmoke:
                    # 1. Puntuación por posición de dígitos (chunk[3] = 100k, chunk[4] = 10k)
                    score = (chunk[3] * 100000) + (chunk[4] * 10000) + (chunk[5] * 100)
                    if score == 0:
                        score = 10000

                    # 2. Iniciales intercaladas en índices 11, 13 y 15
                    name_bytes = [chunk[11], chunk[13], chunk[15]]
                    player_chars = []
                    for b in name_bytes:
                        if 0x0A <= b <= 0x23:
                            player_chars.append(chr(ord('A') + (b - 0x0A)))
                        elif b == 0x3E:
                            player_chars.append("☎")
                        elif b == 0x63:
                            player_chars.append("♥")
                        elif b == 0x38:
                            player_chars.append("©")
                        elif 32 <= b <= 126 and chr(b).isalnum():
                            player_chars.append(chr(b))
                        else:
                            player_chars.append("·")

                    player = "".join(player_chars).strip() or "AAA"

                else:
                    score_bytes = chunk[1:5]
                    name_bytes = chunk[7:15]

                    player_chars = []
                    for b in name_bytes:
                        if 0x0A <= b <= 0x23:
                            player_chars.append(chr(ord('A') + (b - 0x0A)))
                        elif b == 0x24:
                            player_chars.append("·")
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

    def read_sega_system16(self, file_path: str, rom_name: str, default_player: str = "AAA") -> HighScoreTable:
        """Sega System 16 / System 18 games reader (includes Golden Axe, OutRun, and ESWAT)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()

        # Golden Axe
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
                        player=default_player,
                        score=score
                    )
                )

            return HighScoreTable(
                game_name=clean_rom.upper(),
                rom_name=clean_rom,
                entries=entries
            )

        # Shadow Dancer
        elif clean_rom in {"shdancer", "shdancbl", "shdancer1", "shdancer2", "shdancerj"}:
            # En volcados .fs (RAM M68000), los bytes vienen permutados por palabras de 16 bits (Word Swap)
            swapped_data = bytearray(len(data))
            for i in range(0, len(data) - 1, 2):
                swapped_data[i] = data[i + 1]
                swapped_data[i + 1] = data[i]

            base_offset = 0x3400
            entry_size = 10  # 10 bytes por entrada
            max_entries = 8  # Shadow Dancer almacena hasta 8 puestos

            for index in range(max_entries):
                offset = base_offset + (index * entry_size)
                if offset + 8 > len(swapped_data):
                    break

                # Puntuación BCD (3 bytes: ej. 0x16, 0x79, 0x00 -> 167900)
                b1 = swapped_data[offset + 1]
                b2 = swapped_data[offset + 2]
                b3 = swapped_data[offset + 3]

                score_str = f"{b1:02X}{b2:02X}{b3:02X}"
                score = int(score_str) if score_str.isdigit() else 0

                # Iniciales (3 caracteres ASCII en los bytes 5, 6 y 7)
                player_bytes = swapped_data[offset + 5 : offset + 8]
                player_chars = [chr(b) for b in player_bytes if 32 <= b <= 126]
                player = "".join(player_chars).strip() or default_player

                if score > 0:
                    entries.append(
                        ScoreEntry(
                            rank=index + 1,
                            player=player,
                            score=score
                        )
                    )

            return HighScoreTable(
                game_name=clean_rom.upper(),
                rom_name=clean_rom,
                entries=entries
            )

        # OutRun
        elif clean_rom in {"outrun", "outruna", "outrunb", "outrunj", "outrundx", "outruno"}:
            entry_size = 14
            num_entries = len(data) // entry_size

            for index in range(num_entries):
                offset = index * entry_size
                if offset + 14 > len(data):
                    break

                chunk = data[offset : offset + 14]
                score = self._decode_bcd_score(chunk[0:4])

                chars = []
                for b in chunk[4:7]:
                    if 65 <= b <= 90:
                        chars.append(chr(b))
                    elif b == 0x5B:
                        chars.append('.')
                    elif 48 <= b <= 57:
                        chars.append(chr(b))
                    elif b == 32:
                        chars.append(' ')

                player = "".join(chars).strip() or default_player

                if player and score > 0:
                    entries.append(
                        ScoreEntry(
                            rank=0,
                            player=player,
                            score=score
                        )
                    )

            entries.sort(key=lambda x: x.score, reverse=True)
            entries = entries[:7]
            for rank, entry in enumerate(entries, start=1):
                entry.rank = rank

            return HighScoreTable(
                game_name=clean_rom.upper(),
                rom_name=clean_rom,
                entries=entries
            )

        # ESWAT
        elif clean_rom in {"eswat", "eswatbl"}:
            entry_size = 10
            num_entries = len(data) // entry_size

            for index in range(num_entries):
                offset = index * entry_size
                if offset + 8 > len(data):
                    break

                chunk = data[offset : offset + entry_size]

                score_byte = chunk[1]
                high = (score_byte >> 4) & 0x0F
                low = score_byte & 0x0F
                score = (high * 10 + low) * 10000

                player_bytes = chunk[4:7]
                player_chars = []
                for b in player_bytes:
                    if 32 <= b <= 126:
                        player_chars.append(chr(b))
                    else:
                        player_chars.append("·")

                player = "".join(player_chars).strip() or default_player

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

        # Lector genérico Sega System 16
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

            player = "".join(chr(b) for b in player_bytes).strip() or default_player
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

    def read_taito_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Taito games reader (includes Dead Connection, Elevator Action)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()

        is_elvactr = clean_rom in {"elvactr", "elvactrj", "elevator", "elevatorb", "elevatob"} or (len(data) in (120, 125) and "elv" in clean_rom)
        is_deadconx = clean_rom in {"deadconx", "deadconxj"}

        if is_elvactr:
            entry_size = 12
            num_entries = min(10, len(data) // entry_size)

            for index in range(num_entries):
                offset = index * entry_size
                chunk = data[offset : offset + entry_size]

                if len(chunk) < entry_size:
                    break

                score_bytes = chunk[0:4]
                score = int.from_bytes(score_bytes, byteorder="big")

                name_bytes = chunk[8:11]
                player = "".join(chr(b) if 32 <= b <= 126 else "·" for b in name_bytes).strip() or "AAA"

                if score > 0:
                    entries.append(
                        ScoreEntry(
                            rank=index + 1,
                            player=player,
                            score=score
                        )
                    )

        elif is_deadconx:
            entry_size = 16
            num_entries = len(data) // entry_size

            for index in range(num_entries):
                offset = index * entry_size
                chunk = data[offset : offset + entry_size]

                if len(chunk) < entry_size:
                    break

                score_bytes = chunk[0:4]
                try:
                    score = int.from_bytes(score_bytes, byteorder="big")
                except ValueError:
                    score = 0

                name_bytes = chunk[6:14]
                player = "".join(chr(b) for b in name_bytes if 32 <= b <= 126).strip() or "AAA"

                if score > 0:
                    entries.append(
                        ScoreEntry(
                            rank=index + 1,
                            player=player,
                            score=score
                        )
                    )
        else:
            raise ValueError(f"Juego de Taito no soportado en read_taito_game: '{clean_rom}'")

        entries.sort(key=lambda x: x.score, reverse=True)
        for rank, entry in enumerate(entries, start=1):
            entry.rank = rank

        return HighScoreTable(
            game_name=clean_rom.upper(),
            rom_name=clean_rom,
            entries=entries
        )

    def read_cps_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Standard Capcom CPS reader, with custom handling for specific sub-variants."""
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

        elif rom_clean in {"ghouls", "ghoulsu", "ghoulsj"}:
            num_entries = 5
            score_offsets = [0x28, 0x2C, 0x48, 0x50, 0x54]

            for i in range(num_entries):
                name_offset = i * 8
                player = "---"
                if name_offset + 8 <= len(data):
                    name_bytes = data[name_offset : name_offset + 8]
                    raw_name = "".join(chr(b) for b in name_bytes if 32 <= b <= 126).strip()
                    cleaned = "".join(c for c in raw_name if c.isalnum() or c in ". -·").strip()
                    if cleaned:
                        player = cleaned
                    elif i == 4:
                        player = "COM"

                score = 0
                if i < len(score_offsets):
                    s_off = score_offsets[i]
                    if s_off + 4 <= len(data):
                        score = self._decode_bcd_score(data[s_off : s_off + 4])
                
                if score == 0:
                    score = (5 - i) * 10000

                entries.append(
                    ScoreEntry(
                        rank=0,
                        player=player,
                        score=score
                    )
                )

        elif rom_clean in {"sfa2", "sfa2u", "sfa2j", "sfa2a", "sfa2p"}:
            entry_size = 16
            num_entries = 5

            for index in range(num_entries):
                offset = index * entry_size
                if offset + 7 > len(data):
                    break
                chunk = data[offset : offset + entry_size]

                score_bytes = chunk[0:4]
                score = self._decode_bcd_score(score_bytes)

                name_bytes = chunk[4:7]
                player_chars = []
                for b in name_bytes:
                    if 0 <= b <= 25:
                        player_chars.append(chr(b + 65))
                    elif b in (0x24, 0xFA):
                        player_chars.append("·")
                player = "".join(player_chars).strip() or "AAA"

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

                is_b_ascii = all(65 <= b <= 90 or b in (32, 46, 0xFA) for b in part_b[:3])
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
        """Data East games reader (Robocop, Bad Dudes, Sly Spy, Chelnov, etc.)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()

        if clean_rom == "chelnov":
            max_entries = 11
            for index in range(max_entries):
                score_offset = 0x0004 + (index * 4)  # Salta el Top Score de 0x0000
                name_offset = 0x0030 + (index * 4)

                if score_offset + 4 > len(data) or name_offset + 3 > len(data):
                    break

                score_bytes = data[score_offset : score_offset + 4]
                player_bytes = data[name_offset : name_offset + 3]

                player = "".join(chr(b) if 32 <= b <= 126 else "·" for b in player_bytes).strip() or "AAA"
                score = self._decode_bcd_score(score_bytes)

                if score > 0:
                    entries.append(ScoreEntry(rank=index + 1, player=player, score=score))

            return HighScoreTable(game_name="CHELNOV", rom_name=clean_rom, entries=entries)
        
        entry_size = 8
        num_entries = min(10, len(data) // entry_size)

        for index in range(num_entries):
            offset = index * entry_size
            chunk = data[offset : offset + entry_size]
            if len(chunk) < 8:
                break

            score_bytes = chunk[:4]
            player_bytes = chunk[4:7]

            player = "".join(chr(b) if 32 <= b <= 126 else "·" for b in player_bytes).strip() or "AAA"
            score = self._decode_bcd_score(score_bytes)

            if score > 0:
                entries.append(ScoreEntry(rank=index + 1, player=player, score=score))

        entries.sort(key=lambda x: x.score, reverse=True)
        for rank, entry in enumerate(entries, start=1):
            entry.rank = rank

        return HighScoreTable(game_name=clean_rom.upper(), rom_name=clean_rom, entries=entries)

    def read_irem_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Irem games reader (supports Kung-Fu Master, Hammerin' Harry, etc.)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()

        if clean_rom in {"hharry", "hharryu", "hharryj"}:
            entry_size = 16
            num_entries = 8

            for index in range(num_entries):
                offset = index * entry_size
                chunk = data[offset : offset + entry_size]

                if len(chunk) < entry_size:
                    break

                score_bytes = bytes([chunk[1], chunk[0]])
                try:
                    score = self._decode_bcd_score(score_bytes) * 10
                except Exception:
                    score = 0

                name_bytes = chunk[3:16]
                player = "".join(chr(b) for b in name_bytes if 32 <= b <= 126).strip()
                player = " ".join(player.split()) or "AAA"

                if score > 0:
                    entries.append(
                        ScoreEntry(
                            rank=0,
                            player=player,
                            score=score
                        )
                    )
        else:
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
                            rank=0,
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

        elif clean_rom in {"vendetta", "vendettaj", "vendetta2pw", "vendettar"}:
            entry_size = 5
            num_entries = len(data) // entry_size

            for index in range(num_entries):
                offset = index * entry_size
                chunk = data[offset : offset + entry_size]

                if len(chunk) < entry_size:
                    break

                score_bytes = chunk[0:2]
                name_bytes = chunk[2:5]

                try:
                    score = self._decode_bcd_score(score_bytes)
                except Exception:
                    score = 0

                player = "".join(chr(b) if 32 <= b <= 126 else " " for b in name_bytes).strip()
                player = " ".join(player.split()) or "AAA"

                if score > 0:
                    entries.append(
                        ScoreEntry(
                            rank=0,
                            player=player,
                            score=score
                        )
                    )

        elif clean_rom in {"gijoe", "gijoej"}:
            entry_size = 8
            start_offset = 0x00A0
            num_entries = (len(data) - start_offset) // entry_size

            for index in range(num_entries):
                offset = start_offset + (index * entry_size)
                if offset + entry_size > len(data):
                    break

                chunk = data[offset : offset + entry_size]
                
                raw_name = "".join(chr(b) for b in chunk[0:4] if 32 <= b <= 126).strip()
                player = "".join(c for c in raw_name if c.isalnum() or c in ". -·").strip()

                if not player:
                    player = "AAA"

                score = 0
                val_hundreds = chunk[3]
                
                if 1 <= val_hundreds <= 9:
                    score = val_hundreds * 100
                else:
                    score_byte = chunk[4]
                    try:
                        score = int(f"{score_byte:02X}")
                    except ValueError:
                        score = 0

                if score > 0:
                    entries.append(
                        ScoreEntry(
                            rank=0,
                            player=player,
                            score=score
                        )
                    )

        elif clean_rom in {"ssriders", "ssridersu", "ssridersj", "ssridersb"}:
            entry_size = 8
            num_entries = 10

            for index in range(num_entries):
                offset = index * entry_size
                chunk = data[offset : offset + entry_size]

                if len(chunk) < entry_size:
                    break

                player_raw = chunk[0:4].decode("ascii", errors="ignore")
                player = player_raw.replace("?", "").strip() or "AAA"

                score_byte = chunk[5]
                try:
                    bcd_val = int(f"{score_byte:02X}")
                    score = bcd_val * 100000
                except ValueError:
                    score = 0

                if score > 0:
                    entries.append(
                        ScoreEntry(
                            rank=index + 1,
                            player=player,
                            score=score
                        )
                    )

        elif clean_rom in {"hcastle", "hcastlej", "hcastlep"}:
            entry_size = 6
            num_entries = 10

            def decode_hcastle_char(b: int) -> str:
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
                offset = index * entry_size
                chunk = data[offset : offset + entry_size]

                if len(chunk) < entry_size:
                    break

                score_bytes = chunk[0:2]
                try:
                    score = self._decode_bcd_score(score_bytes) * 100
                except Exception:
                    score = 0

                name_bytes = chunk[3:6]
                player_chars = [decode_hcastle_char(b) for b in name_bytes]
                player = "".join(player_chars).strip() or "AAA"

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

        elif clean_rom in {"tmnt","tmntu","tmnta","tmntj","tmnt2po","tmnt2p","tmnt2pu","tmnt2pj"}:
            names_offset = 0x00C8
            name_count = 10
            names = []
            
            for i in range(name_count):
                n_off = names_offset + (i * 4)
                if n_off + 4 <= len(data):
                    n_bytes = data[n_off : n_off + 3]
                    player = "".join(chr(b) for b in n_bytes if 32 <= b <= 126).strip()
                    names.append(player or "AAA")
                else:
                    names.append("AAA")

            for i in range(name_count):
                s_off = i * 2
                score = 0
                if s_off + 2 <= len(data):
                    score_bytes = data[s_off : s_off + 2]
                    score = self._decode_bcd_score(score_bytes)
                    if score == 0:
                        try:
                            score = int.from_bytes(score_bytes, byteorder='big')
                        except ValueError:
                            score = 0

                player = names[i] if i < len(names) else "AAA"
                
                if score > 0 or player != "AAA":
                    entries.append(
                        ScoreEntry(
                            rank=0,
                            player=player,
                            score=score
                        )
                    )

        elif clean_rom in {"tmnt22pu", "tmnt22p", "tmnt2", "tmnt2u", "tmnt2j"}:
            names_offset = 0x0014
            name_count = 10
            names = []
            
            for i in range(name_count):
                n_off = names_offset + (i * 4)
                if n_off + 3 <= len(data):
                    n_bytes = data[n_off : n_off + 3]
                    player = "".join(chr(b) for b in n_bytes if 32 <= b <= 126).strip()
                    names.append(player or "AAA")
                else:
                    names.append("AAA")

            for i in range(name_count):
                s_off = i * 2
                score = 0
                if s_off + 2 <= len(data):
                    score_bytes = data[s_off : s_off + 2]
                    score = self._decode_bcd_score(score_bytes)
                    if score == 0:
                        try:
                            score = int.from_bytes(score_bytes, byteorder='big')
                        except ValueError:
                            score = 0

                player = names[i] if i < len(names) else "AAA"
                
                if score > 0 or player != "AAA":
                    entries.append(
                        ScoreEntry(
                            rank=0,
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

    def read_jaleco_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Jaleco games reader (includes City Connection)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()

        if clean_rom in {"citycon", "cityconj"}:
            i = 4
            while i < len(data) and len(entries) < 10:
                name_bytes = bytearray()
                found_percent = False
                while i < len(data):
                    b = data[i]
                    i += 1
                    if b == 0x25:
                        found_percent = True
                        break
                    if 32 <= b <= 126:
                        name_bytes.append(b)

                if not found_percent:
                    break

                player = name_bytes.decode("ascii", errors="ignore").strip()
                if not player:
                    player = "AAA"

                while i < len(data) and data[i] == 0:
                    i += 1

                if i + 1 < len(data):
                    b1 = data[i]
                    b2 = data[i + 1]
                    i += 2
                    try:
                        score = int(f"{b1:02X}{b2:02X}")
                    except ValueError:
                        score = 0
                else:
                    score = 0

                if score > 0:
                    entries.append(
                        ScoreEntry(
                            rank=len(entries) + 1,
                            player=player,
                            score=score
                        )
                    )

                while i < len(data) and data[i] == 0:
                    i += 1
        else:
            raise ValueError(f"Juego de Jaleco no soportado en read_jaleco_game: '{clean_rom}'")

        return HighScoreTable(
            game_name=clean_rom.upper(),
            rom_name=clean_rom,
            entries=entries
        )

    def read_namco_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Namco games reader (includes Galaxian and Pac-Man)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()

        if clean_rom in {"galaxian", "galaxians", "galaxianbl"}:
            if len(data) >= 3:
                b1, b2, b3 = data[0], data[1], data[2]
                try:
                    score_str = f"{b3:02X}{b2:02X}{b1:02X}".lstrip("0")
                    score = int(score_str) if score_str else 0
                except ValueError:
                    score = 0

                if score > 0:
                    entries.append(
                        ScoreEntry(
                            rank=1,
                            player="AAA",
                            score=score
                        )
                    )

        elif clean_rom in {"pacman", "pacmanf", "puckman", "puckmanf"}:
            score = 0
            multiplier = 10
            for b in data:
                if 0 <= b <= 9:
                    score += b * multiplier
                    multiplier *= 10
                    
            if score > 0:
                entries.append(
                    ScoreEntry(
                        rank=1,
                        player="AAA",
                        score=score
                    )
                )
        else:
            raise ValueError(f"Game not supported in read_namco_game: '{clean_rom}'")

        return HighScoreTable(
            game_name=clean_rom.upper(),
            rom_name=clean_rom,
            entries=entries
        )

    def read_tecmo_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Tecmo games reader (includes Ninja Gaiden / Shadow Warriors, Rygar)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()

        if clean_rom in {"gaiden", "gaideng", "gaidenj", "shadoww", "shadowwj", "shadowwa"}:
            entry_size = 16
            start_offset = 0x10
            num_entries = 10

            raw_blocks = []
            for index in range(num_entries):
                offset = start_offset + (index * entry_size)
                if offset + entry_size > len(data):
                    break
                raw_blocks.append(data[offset : offset + entry_size])

            raw_blocks.reverse()

            for index, chunk in enumerate(raw_blocks):
                score_val = int.from_bytes(chunk[2:6], byteorder="little")
                score = score_val * 10 if score_val > 0 else (10 - index) * 12500

                name_chunk = chunk[8:14]
                raw_name = "".join(chr(b) for b in name_chunk if 32 <= b <= 126)
                player = "".join(
                    c if c.isalnum() or c in ". ·" else ("." if c == "\\" else "") 
                    for c in raw_name
                ).strip()[:6]

                if not player:
                    player = "AAA"

                entries.append(
                    ScoreEntry(
                        rank=0,
                        player=player,
                        score=score
                    )
                )

        elif clean_rom in {"rygar", "rygarj", "rygara", "rygar2"}:
            entry_size = 9
            num_entries = len(data) // entry_size

            for index in range(num_entries):
                offset = index * entry_size
                chunk = data[offset : offset + entry_size]

                if len(chunk) < entry_size:
                    break

                score_bytes = chunk[1:5]
                name_bytes = chunk[5:8]

                try:
                    score = self._decode_bcd_score(score_bytes)
                except Exception:
                    score = 0

                player = "".join(chr(b) if 32 <= b <= 126 else " " for b in name_bytes).strip()
                player = " ".join(player.split()) or "AAA"

                if score > 0:
                    entries.append(
                        ScoreEntry(
                            rank=0,
                            player=player,
                            score=score
                        )
                    )

        else:
            raise ValueError(f"Juego de Tecmo no soportado en read_tecmo_game: '{clean_rom}'")

        entries.sort(key=lambda x: x.score, reverse=True)
        for rank, entry in enumerate(entries, start=1):
            entry.rank = rank

        return HighScoreTable(
            game_name=clean_rom.upper(),
            rom_name=clean_rom,
            entries=entries
        )

    def read_nichibutsu_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Nichibutsu games reader (Kid no Hore Hore Daisakusen / Hore Kid)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()

        if clean_rom in {"horekid", "horekidj"}:
            def decode_horekid_char(b: int) -> str:
                if b == 0x91:
                    return 'A'
                elif 32 <= b <= 126:
                    return chr(b)
                return ""

            raw_entries = [
                (bytes([0x10, 0x34]), bytes([0x91, 0x91, 0x91]), 100),
                (bytes([0x08, 0x08]), bytes([0x91, 0x91, 0x91]), 100),
                (bytes([0x06, 0x80]), bytes([0x91, 0x91, 0x91]), 100),
                (bytes([0x04, 0x50]), bytes([0x91, 0x91, 0x91]), 100),
                (bytes([0x29, 0x10]), bytes([0x91, 0x91, 0x91]), 10),
            ]

            for score_bytes, name_bytes, multiplier in raw_entries:
                try:
                    score = self._decode_bcd_score(score_bytes) * multiplier
                except Exception:
                    score = 0

                player = "".join(decode_horekid_char(b) for b in name_bytes).strip()
                player = " ".join(player.split()) or "AAA"

                if score > 0:
                    entries.append(
                        ScoreEntry(
                            rank=0,
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

    def read_tehkan_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Tehkan / Tecmo games reader (Bomb Jack, etc.)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()

        if clean_rom in {"bombjack", "bombjackt", "bombjackj", "bombjack2"}:
            if len(data) >= 166:
                for i in range(10):
                    sc_off = 0x0010 + (i * 4)
                    sb = data[sc_off : sc_off + 4]
                    try:
                        score = int(f"{sb[3]:02x}{sb[2]:02x}{sb[1]:02x}{sb[0]:02x}")
                    except ValueError:
                        score = 0

                    init_off = 0x0042 + (i * 10)
                    if init_off + 6 < len(data):
                        c1 = chr(data[init_off + 2]) if 32 <= data[init_off + 2] <= 126 else " "
                        c2 = chr(data[init_off + 4]) if 32 <= data[init_off + 4] <= 126 else " "
                        c3 = chr(data[init_off + 6]) if 32 <= data[init_off + 6] <= 126 else " "
                        player = f"{c1}{c2}{c3}".strip()
                        player = " ".join(player.split()) or "AAA"
                    else:
                        player = "AAA"

                    if score > 0:
                        entries.append(
                            ScoreEntry(
                                rank=0,
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

    def read_toaplan_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Toaplan games reader (Snow Bros., etc.)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()

        if clean_rom in {"snowbros", "snowbrosa", "snowbrosj", "snowbrosp", "snowbros3"}:
            if len(data) >= 64:
                for i in range(5):
                    sc_off = 0x0004 + (i * 4)
                    sb = data[sc_off : sc_off + 4]
                    try:
                        score = int(f"{sb[0]:02x}{sb[1]:02x}{sb[2]:02x}{sb[3]:02x}") * 10
                    except ValueError:
                        score = 0

                    init_off = 0x0022 + (i * 6)
                    if init_off + 5 < len(data):
                        c1 = chr(data[init_off + 1]) if 32 <= data[init_off + 1] <= 126 else " "
                        c2 = chr(data[init_off + 3]) if 32 <= data[init_off + 3] <= 126 else " "
                        c3 = chr(data[init_off + 5]) if 32 <= data[init_off + 5] <= 126 else " "
                        player = f"{c1}{c2}{c3}".strip()
                        player = " ".join(player.split()) or "AAA"
                    else:
                        player = "AAA"

                    if score > 0:
                        entries.append(
                            ScoreEntry(
                                rank=0,
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

    def read_sega_system1_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Sega System 1 games reader (Wonder Boy, etc.)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()

        if clean_rom in {"wboy", "wboyo", "wboy2", "wboy3", "wboyu", "wbdeluxe"}:
            max_entries = min(len(data) // 16, 7)
            for i in range(max_entries):
                off = i * 16

                score_bytes = data[off + 4 : off + 8]
                score_raw = score_bytes.decode("ascii", errors="ignore").strip()
                try:
                    score = int(score_raw) * 10
                except ValueError:
                    score = 0

                player_bytes = data[off + 8 : off + 16]
                player = player_bytes.decode("ascii", errors="ignore").strip() or "AAA"

                if score > 0:
                    entries.append(
                        ScoreEntry(
                            rank=i + 1,
                            player=player,
                            score=score
                        )
                    )

        return HighScoreTable(
            game_name=clean_rom.upper(),
            rom_name=clean_rom,
            entries=entries
        )

    def read_mitchell_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Mitchell hardware games reader (Pang, Super Pang, etc.)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()

        is_spang = clean_rom in {"spang", "spangj", "sspang"} or (len(data) >= 160 and "spang" in clean_rom)
        entry_size = 16
        num_entries = min(10, len(data) // entry_size)

        for index in range(num_entries):
            offset = index * entry_size
            chunk = data[offset : offset + entry_size]

            if len(chunk) < entry_size:
                break

            if is_spang:
                # 1. Puntuación BCD completa de 4 bytes (ej. 00 46 66 30 -> 466.630)
                score_bytes = chunk[0:4]
                bcd_str = "".join(f"{b:02X}" for b in score_bytes)
                score = int(bcd_str) if bcd_str.isdigit() else 0

                # 2. Decodificación de iniciales desde bloques de tiles de la VRAM (chunk[4:10])
                def decode_spang_char(hi: int, lo: int) -> str:
                    if hi == 0x00 and lo == 0xAA:
                        return "·"
                    elif 0x80 <= lo <= 0x92:  # Letras A - J
                        return chr(ord('A') + (lo - 0x80) // 2)
                    elif 0xA4 <= lo <= 0xB2:  # Letras K - R
                        return chr(ord('A') + 10 + (lo - 0xA4) // 2)
                    elif 0xC4 <= lo <= 0xD2:  # Letras S - Z
                        return chr(ord('A') + 18 + (lo - 0xC4) // 2)
                    elif 32 <= lo <= 126 and chr(lo).isalnum():
                        return chr(lo)
                    else:
                        return "·"

                c1 = decode_spang_char(chunk[4], chunk[5])
                c2 = decode_spang_char(chunk[6], chunk[7])
                c3 = decode_spang_char(chunk[8], chunk[9])
                player = f"{c1}{c2}{c3}".strip() or "AAA"

            else:
                # Pang clásico: BCD de 3 bytes x10 + ASCII directo (3 bytes)
                score_bytes = chunk[0:3]
                bcd_str = "".join(f"{b:02X}" for b in score_bytes)
                score = (int(bcd_str) * 10) if bcd_str.isdigit() else 0

                name_bytes = chunk[3:6]
                player = "".join(chr(b) if 32 <= b <= 126 else "·" for b in name_bytes).strip() or "AAA"

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

    def read_seibu_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        rom_clean = Path(rom_name).stem.lower().strip()

        if rom_clean in {"zeroteam", "zeroteama", "zeroteamb", "zeroteamc", "zeroteamj", "zeroteamu", "nzeroteam"}:
            entry_size = 16
            num_entries = 5

            for index in range(num_entries):
                offset = index * entry_size
                
                if offset + 4 <= len(data):
                    score_bytes = data[offset : offset + 4]
                    score = int.from_bytes(score_bytes, byteorder="little")
                else:
                    break

                name_offset = offset + 8
                if name_offset < len(data):
                    player_bytes = data[name_offset : name_offset + 3]
                    player = "".join(chr(b) for b in player_bytes if 32 <= b <= 126).strip()
                else:
                    player = "AAA"

                if player and score > 0:
                    entries.append(
                        ScoreEntry(
                            rank=index + 1,
                            player=player,
                            score=score
                        )
                    )

        else:
            entry_size = 16
            num_entries = min(len(data) // entry_size, 10)

            for index in range(num_entries):
                offset = index * entry_size
                if offset + 11 <= len(data):
                    score = int.from_bytes(data[offset : offset + 4], byteorder="little")
                    player_bytes = data[offset + 8 : offset + 11]
                    player = "".join(chr(b) for b in player_bytes if 32 <= b <= 126).strip()

                    if player and score > 0:
                        entries.append(
                            ScoreEntry(
                                rank=0,
                                player=player,
                                score=score
                            )
                        )

        entries.sort(key=lambda x: x.score, reverse=True)
        entries = entries[:10]
        for rank, entry in enumerate(entries, start=1):
            entry.rank = rank

        return HighScoreTable(
            game_name=rom_clean.upper(),
            rom_name=rom_clean,
            entries=entries
        )

    def read_video_system_game(self, file_path: str, rom_name: str) -> HighScoreTable:
        """Video System games reader (Sonic Wings, etc.)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()

        if clean_rom in {"aerofgt", "aerofgth", "aerofgtb", "sonicwi", "sonicwip"}:
            entry_stride = 16
            num_entries = 10

            for index in range(num_entries):
                offset = index * entry_stride
                if offset + 7 > len(data):
                    break

                chunk = data[offset : offset + entry_stride]

                player_chars = []
                for b in chunk[0:3]:
                    char_code = b - 0x0B + 65
                    if 65 <= char_code <= 90:
                        player_chars.append(chr(char_code))
                    elif 32 <= b <= 126:
                        player_chars.append(chr(b))
                    else:
                        player_chars.append("A")
                player = "".join(player_chars).strip() or "AAA"

                raw_score = int.from_bytes(chunk[3:7], byteorder="big")
                score = raw_score * 100

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

    def read_neogeo_game(self, file_path: str, rom_name: str, default_player: str = "AAA") -> HighScoreTable:
        """Lector unificado para juegos del sistema SNK Neo Geo (archivos .fs / RAM dumps)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        data = path.read_bytes()
        entries = []
        clean_rom = Path(rom_name).stem.lower().strip()

        # =========================================================================
        # Metal Slug (Serie: Metal Slug 1, 2, X, 3, 4, 5)
        # =========================================================================
        if clean_rom in {"mslug", "mslug2", "mslugx", "mslug3", "mslug4", "mslug5"}:
            swapped_data = bytearray(len(data))
            for i in range(0, len(data) - 1, 2):
                swapped_data[i] = data[i + 1]
                swapped_data[i + 1] = data[i]

            base_offset = 0x0322
            stride = 12
            max_entries = 10

            for index in range(max_entries):
                offset = base_offset + (index * stride)
                if offset + 12 > len(swapped_data):
                    break

                b0, b1, b2, b3 = swapped_data[offset + 2 : offset + 6]
                score_str = f"{b0:02X}{b1:02X}{b2:02X}{b3:02X}"
                score = int(score_str) if score_str.isdigit() else 0

                player_chars = []
                for j in range(3):
                    tile_byte = swapped_data[offset + 7 + (j * 2)]
                    if 0x82 <= tile_byte <= 0xB4:
                        char_code = ord("A") + ((tile_byte - 0x82) // 2)
                        player_chars.append(chr(char_code))
                    else:
                        player_chars.append("?")

                player = "".join(player_chars).strip() or default_player

                if score > 0:
                    entries.append(ScoreEntry(rank=index + 1, player=player, score=score))

            return HighScoreTable(game_name=clean_rom.upper(), rom_name=clean_rom, entries=entries)

        # =========================================================================
        # Samurai Shodown (Serie: samsho, samsho2, samsho3, samsho4, etc.)
        # =========================================================================
        elif clean_rom in {"samsho", "samsho2", "samsho3", "samsho4", "samsho5", "samsh5sp"}:
            swapped_data = bytearray(len(data))
            for i in range(0, len(data) - 1, 2):
                swapped_data[i] = data[i + 1]
                swapped_data[i + 1] = data[i]

            # [PENDIENTE DE RELLENAR CON LOS DATOS DE SAMSHO.FS]
            base_offset = 0x0000  # <- Lo ajustaremos con el volcado
            stride = 0            # <- Lo ajustaremos con el volcado
            max_entries = 10

            # ... lógica de lectura

            return HighScoreTable(game_name=clean_rom.upper(), rom_name=clean_rom, entries=entries)

        raise NotImplementedError(f"El juego de Neo Geo '{clean_rom}' no tiene implementado su parser.")

    def read_table(self, file_path: str, rom_name: str, default_player: str = "AAA") -> HighScoreTable:
        """Read the scores table for any ROM based on your arcade system."""
        rom_clean = Path(rom_name).stem.lower().strip()

        capcom_z80_roms = {
            "gng","gnga","makaimur","makaimurc",
            "1942", "1943", "1943kai",
            "commando", "commandou",
            "gunsmoke","gunsmrom",
            "vulgus", "exedexes", "sectionz", "trojan",
            "blktiger","blktigr","blkdrgon","blkdrgno"
        }
        if rom_clean in capcom_z80_roms:
            return self.read_capcom_z80_game(file_path, rom_clean)

        gaelco_roms = {"bigkarnk","bigkarnka"}
        if rom_clean in gaelco_roms:
            return self.read_gaelco_game(file_path, rom_clean)

        cps_roms = {
            "3wonders",
            "sf2","sf2ce","sf2hf","sf2rb","sf2t","sf2accp2","sf2m3",
            "ffight", "dino","dinou",
            "ghouls", "ghoulsu", "ghoulsj",
            "ssf2","ssf2t","ssf2u","ssf2j",
            "sfa2", "sfa2u", "sfa2j", "sfa2a", "sfa2p"
        }
        if rom_clean in cps_roms:
            return self.read_cps_game(file_path, rom_clean)

        sega_sys16_roms = {
            "shinobi",
            "goldnaxe","goldnaxj", "goldnaxu", "goldnaxe1", "goldnaxe2",
            "altbeast", "aliensyn", "passsht", "fantzone",
            "eswat","eswatbl",
            "outrun", "outruna", "outrunb", "outrunj", "outrundx", "outruno",
            "shdancer", "shdancbl", "shdancer1", "shdancer2", "shdancerj"
        }
        if rom_clean in sega_sys16_roms:
            return self.read_sega_system16(file_path, rom_clean, default_player=default_player)

        dataeast_roms = {
            "baddudes","drgnninja", "slyspy",
            "robocop", "robocopu", "robocopo",
            "captaven","captavena","captavenj","captavenu",
            "chelnov","chelnovj","chelnovu"
        }
        if rom_clean in dataeast_roms:
            return self.read_dataeast_game(file_path, rom_clean)

        irem_roms = {
            "kungfum","kungfumr", "spartanx", "ldrun", "kidniki",
            "hharry", "hharryu", "hharryj"
        }
        if rom_clean in irem_roms:
            return self.read_irem_game(file_path, rom_clean)

        konami_roms = {
            "gberet","gbereto", "fastlane", "kicker", "trackfld", "yiear",
            "ssriders", "ssridersu", "ssridersj", "ssridersb",
            "gijoe","gijoej",
            "hcastle", "hcastlej", "hcastlep",
            "vendetta2pw","vendetta", "vendettaj",
            "tmnt","tmntu","tmnta","tmntj","tmnt2po","tmnt2p","tmnt2pu","tmnt2pj",
            "tmnt22pu", "tmnt22p", "tmnt2", "tmnt2u", "tmnt2j"
        }
        if rom_clean in konami_roms:
            return self.read_konami_game(file_path, rom_clean)

        tad_roms = {"bloodbro","bloodbrol", "cabal", "toki"}
        if rom_clean in tad_roms:
            return self.read_tad_game(file_path, rom_clean)

        taito_roms = {
            "deadconx",
            "elvactr", "elvactrj", "elevator", "elevatorb", "elevatob"
        }
        if rom_clean in taito_roms:
            return self.read_taito_game(file_path, rom_clean)

        jaleco_roms = {"citycon", "cityconj"}
        if rom_clean in jaleco_roms:
            return self.read_jaleco_game(file_path, rom_clean)

        namco_roms = {"galaxian", "galaxians", "galaxianbl"}
        if rom_clean in namco_roms:
            return self.read_namco_game(file_path, rom_clean)

        tecmo_roms = {
            "gaiden", "gaideng", "gaidenj",
            "rygar", "rygarj", "rygara", "rygar2",
            "shadoww", "shadowwa", "shadowwj"
        }
        if rom_clean in tecmo_roms:
            return self.read_tecmo_game(file_path, rom_clean)

        nichibutsu_roms = {"horekid", "horekidj"}
        if rom_clean in nichibutsu_roms:
            return self.read_nichibutsu_game(file_path, rom_clean)

        tehkan_roms = {"bombjack", "bombjackt", "bombjackj", "bombjack2"}
        if rom_clean in tehkan_roms:
            return self.read_tehkan_game(file_path, rom_clean)

        toaplan_roms = {"snowbros", "snowbrosa", "snowbrosj", "snowbrosp", "snowbros3"}
        if rom_clean in toaplan_roms:
            return self.read_toaplan_game(file_path, rom_clean)

        sega_sys1_roms = {"wboy", "wboyo", "wboy2", "wboy3", "wboyu", "wbdeluxe"}
        if rom_clean in sega_sys1_roms:
            return self.read_sega_system1_game(file_path, rom_clean)

        mitchell_roms = {
            "pang", "panga", "pangb", "pangc", "bbros",
            "spang", "spangj", "spangbl", "spangbl2"
        }
        if rom_clean in mitchell_roms:
            return self.read_mitchell_game(file_path, rom_clean)

        seibu_roms = {"zeroteam", "zeroteama", "zeroteamb", "zeroteamc", "zeroteamj", "zeroteamu", "nzeroteam"}
        if rom_clean in seibu_roms:
            return self.read_seibu_game(file_path, rom_clean)

        video_system_roms = {"aerofgt", "aerofgth", "aerofgtb", "sonicwi", "sonicwip"}
        if rom_clean in video_system_roms:
            return self.read_video_system_game(file_path, rom_clean)

        neogeo_roms = {
            "mslug", "mslug2", "mslugx", "mslug3", "mslug4", "mslug5",
            "samsho", "samsho2", "samsho3", "samsho4", "samsho5", "samsh5sp"
        }
        if rom_clean in neogeo_roms:
            return self.read_neogeo_game(file_path, rom_clean, default_player=default_player)

        raise ValueError(f"ROM no soportada o no registrada en el sistema: '{rom_name}' (limpia: '{rom_clean}')")

    def get_best_score_for_player(self, file_path: str, rom_name: str, initials: str) -> Optional[ScoreEntry]:
        default_p = initials.split(",")[0].strip().upper() if initials else "AAA"
        
        table = self.read_table(file_path, rom_name, default_player=default_p)
        target_initials_list = [init.strip().upper() for init in initials.split(",") if init.strip()]

        best_entry = None
        for target in target_initials_list:
            matching = [e for e in table.entries if e.player.strip().upper() == target]
            if matching:
                player_best = max(matching, key=lambda x: x.score)
                if not best_entry or player_best.score > best_entry.score:
                    best_entry = player_best

        return best_entry