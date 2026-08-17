from pathlib import Path
from readers.fbneo_reader import FBNeoReader

def main():
    reader = FBNeoReader()
    
    # CAMBIA EL NOMBRE DE LA ROM AQUÍ (da igual si pones "shdancer", "shdancer.hi" o "shdancer.fs")
    rom_input = "pang"
    clean_rom = Path(rom_input).stem.lower().strip()
    
    hi_dir = Path("hi")
    
    # Definimos las dos rutas posibles dentro de la carpeta 'hi'
    hi_file = hi_dir / f"{clean_rom}.hi"
    fs_file = hi_dir / f"{clean_rom}.fs"

    # Prioridad: busca .hi primero; si no está, intenta con .fs
    if hi_file.exists():
        target_file = hi_file
    elif fs_file.exists():
        target_file = fs_file
    else:
        print(f"Error: No se encontró '{clean_rom}.hi' ni '{clean_rom}.fs' en la carpeta '{hi_dir}'.")
        return

    try:
        table = reader.read_table(str(target_file), clean_rom)

        print("===================================")
        print(f" TABLA COMPLETA: {table.game_name} ({target_file.name})")
        print("===================================")
        print("POS  | JUGADOR    | PUNTUACIÓN")
        print("-----------------------------------")

        for entry in table.entries:
            print(f"{entry.rank:<4} | {entry.player:<10} | {entry.score:>12,}")

        print("===================================")

    except Exception as e:
        print(f"Error al leer la tabla de {target_file.name}: {e}")

if __name__ == "__main__":
    main()