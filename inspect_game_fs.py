import sys
from pathlib import Path


def inspect_fs_file(file_path: str | Path, bytes_per_line: int = 16) -> None:
    """Muestra las líneas no vacías de un save-state .fs de RetroArch."""
    path = Path(file_path)
    if not path.exists():
        print(f"❌ Error: No se encontró el archivo '{path}'")
        return

    if bytes_per_line <= 0:
        raise ValueError("bytes_per_line debe ser mayor que cero")

    data = path.read_bytes()
    total_lines = (len(data) + bytes_per_line - 1) // bytes_per_line
    non_empty_lines = [
        (offset, data[offset:offset + bytes_per_line])
        for offset in range(0, len(data), bytes_per_line)
        if any(data[offset:offset + bytes_per_line])
    ]
    non_empty_bytes = sum(byte != 0 for byte in data)

    print("==========================================================")
    print(f" 🔍 VOLCADO HEXADECIMAL DE LÍNEAS NO VACÍAS: {path.name}")
    print(f" Tamaño total: {len(data):,} bytes | Bytes no vacíos: {non_empty_bytes:,}")
    print(f" Líneas mostradas: {len(non_empty_lines):,} de {total_lines:,}")
    print("==========================================================")

    if not non_empty_lines:
        print("El archivo solo contiene bytes 00.\n")
        return

    print("OFFSET  | BYTES (HEX)                                     | ASCII")
    print("-------------------------------------------------------------------")
    for offset, chunk in non_empty_lines:
        hex_bytes = " ".join(f"{byte:02X}" for byte in chunk)
        ascii_text = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in chunk)
        print(f"0x{offset:04X}  | {hex_bytes:<{bytes_per_line * 3 - 1}} | {ascii_text}")

    print("==========================================================\n")


if __name__ == "__main__":
    target_file = sys.argv[1] if len(sys.argv) > 1 else "hi/samsho.fs"
    inspect_fs_file(target_file)
