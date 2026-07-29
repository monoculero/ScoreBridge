from readers.fbneo_reader import FBNeoReader

def main():
    reader = FBNeoReader()
    hi_path = "hi/dino.hi"  # Ajusta la ruta a tu archivo dino.hi

    try:
        table = reader.read_table(hi_path, "dino")

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