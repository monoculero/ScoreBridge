from pathlib import Path

def debug_hi_file(file_path):
    path = Path(file_path)
    if not path.exists():
        print(f"No se encuentra el archivo: {file_path}")
        return
    
    data = path.read_bytes()
    print(f"Tamaño total del archivo: {len(data)} bytes\n")
    print("--- Mostrando los primeros 256 bytes en Hexadecimal ---")
    
    for i in range(0, min(len(data), 256), 16):
        chunk = data[i:i+16]
        hex_str = " ".join(f"{b:02X}" for b in chunk)
        ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        print(f"{i:04X}: {hex_str}  | {ascii_str}")

# Cambia esto por la ruta real de tu fichero .hi de 3wonders si lo necesitas
debug_hi_file("hi/wboy.hi")