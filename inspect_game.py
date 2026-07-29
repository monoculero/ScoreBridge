from pathlib import Path

hi_path = Path("hi/shinobi.hi")

if not hi_path.exists():
    print(f"No se encuentra el archivo en {hi_path}")
else:
    data = hi_path.read_bytes()
    print(f"Tamaño total del archivo: {len(data)} bytes")
    print(f"Hex dump completo:\n{data.hex()}")
    
    # Probamos a imprimirlo en bloques de 10 bytes y 12 bytes
    print("\n--- Vista preliminar (bloques de 10 bytes) ---")
    for i in range(0, len(data), 10):
        chunk = data[i:i+10]
        print(f"Bloque {i//10 + 1}: {chunk.hex()} | ASCII: {''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)}")