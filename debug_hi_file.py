from pathlib import Path

def debug_hi_file():
    hi_path = Path("hi/gberet.hi")
    if not hi_path.exists():
        print(f"No se encuentra el archivo en: {hi_path}")
        return

    data = hi_path.read_bytes()
    print(f"Tamaño del archivo: {len(data)} bytes\n")

    print("--- Primeros 32 bytes en HEX y ASCII ---")
    for i in range(0, min(32, len(data)), 8):
        chunk = data[i:i+8]
        hex_str = " ".join(f"{b:02X}" for b in chunk)
        ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        print(f"0x{i:04X} | {hex_str:<23} | {ascii_str}")

if __name__ == "__main__":
    debug_hi_file()