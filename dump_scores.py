from pathlib import Path
from readers.fbneo_reader import FBNeoReader

def main():
    reader = FBNeoReader()
    
    # CAMBIA EL NOMBRE DE LA ROM SOLO AQUÍ
    rom_name = "aerofgt"
    
    # La ruta del archivo se genera automáticamente usando el nombre de la rom
    hi_path = f"hi/{rom_name}.hi"

    try:
        table = reader.read_table(hi_path, rom_name)

        print("===================================")
        print(f" TABLA COMPLETA: {table.game_name}")
        print("===================================")
        print("POS  | JUGADOR    | PUNTUACIÓN")
        print("-----------------------------------")

        for entry in table.entries:
            print(f"{entry.rank:<4} | {entry.player:<10} | {entry.score:>12,}")

        print("===================================")

    except FileNotFoundError:
        print(f"No se encontró el archivo en: {hi_path}")
    except Exception as e:
        print(f"Error al leer la tabla: {e}")

if __name__ == "__main__":
    main()