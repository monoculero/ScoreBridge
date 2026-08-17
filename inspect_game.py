import sys
from pathlib import Path

def inspect_hi_file(file_path: str, bytes_per_line: int = 8):
    path = Path(file_path)
    if not path.exists():
        print(f"❌ Error: No se encontró el archivo '{file_path}'")
        return

    data = path.read_bytes()
    file_size = len(data)

    print("==========================================================")
    print(f" 🔍 VOLCADO COMPLETO HEXADECIMAL: {path.name} ({file_size} bytes)")
    print("==========================================================")
    print("OFFSET  | BYTES (HEX)             | ASCII")
    print("----------------------------------------------------------")

    for offset in range(0, file_size, bytes_per_line):
        chunk = data[offset : offset + bytes_per_line]
        
        # Representación en Hexadecimal (ej: 41 4C 46 00)
        hex_bytes = " ".join(f"{b:02X}" for b in chunk)
        
        # Representación ASCII (caracteres imprimibles o punto si es un byte de control)
        ascii_text = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        
        # Relleno de espacios si la última línea tiene menos bytes
        hex_padded = f"{hex_bytes:<{bytes_per_line * 3}}"

        print(f"0x{offset:04X}  | {hex_padded} | {ascii_text}")

    print("==========================================================\n")


if __name__ == "__main__":
    target_file = sys.argv[1] if len(sys.argv) > 1 else "hi/pang.hi"
    inspect_hi_file(target_file)