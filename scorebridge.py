import sys
import json
from pathlib import Path
from readers.fbneo_reader import FBNeoReader
from iscored_client import IScoredClient


def load_config(config_path="config.json") -> tuple[dict, Path]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Archivo de configuración no encontrado: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f), path


def save_config(config: dict, config_path: Path):
    """Guarda los cambios de vuelta en el config.json manteniendo un formato bonito."""
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def process_game(rom_name: str, game_info: dict, reader: FBNeoReader, iscored_client: IScoredClient, default_initials: str, hi_folder: Path):
    hi_filename = game_info.get("hi_file", f"{rom_name}.hi")
    hi_path = hi_folder / hi_filename
    target_initials = game_info.get("initials", default_initials)

    try:
        best_entry = reader.get_best_score_for_player(
            str(hi_path), rom_name, target_initials
        )

        game_name = game_info.get("name", rom_name)
        print("===================================")
        print(f" JUEGO : {game_name} ({rom_name})")
        print("===================================")

        if best_entry:
            print(f"INICIALES BUSCADAS : {target_initials.upper()}")
            print(f"JUGADOR REGISTRADO : {best_entry.player}")
            print(f"PUESTO EN TABLA    : #{best_entry.rank}")
            print(f"MEJOR PUNTUACIÓN   : {best_entry.score:,}")

            # Envío a iScored (solo si tiene asignado un ID de juego)
            iscored_id = game_info.get("iscored_id")
            if iscored_client and iscored_id:
                iscored_client.submit_score(
                    game_id_or_name=iscored_id,
                    player_name=best_entry.player,
                    score=best_entry.score,
                )
            elif not iscored_id:
                print(" [Info] Juego sin 'iscored_id' asignado. Se omitió la subida a la nube.")
        else:
            print(f"Sin registros para las iniciales '{target_initials}'")

        print("===================================\n")

    except Exception as e:
        print(f"Error procesando {rom_name}: {e}\n")


def main():
    if len(sys.argv) <= 1:
        print("Uso: python scorebridge.py <nombre_rom>")
        return

    config, config_path = load_config("config.json")
    reader = FBNeoReader()

    default_initials = config.get("default_initials", "ALF")
    hi_folder = Path(config.get("hi_folder", "hi"))

    # Configuración iScored
    iscored_cfg = config.get("iscored", {})
    iscored_enabled = iscored_cfg.get("enabled", False)
    gameroom = iscored_cfg.get("gameroom", "")

    iscored_client = IScoredClient(gameroom) if (iscored_enabled and gameroom) else None
    games = config.get("games", {})

    target_rom = sys.argv[1].lower().strip()

    # Si la ROM no está en config.json, la creamos y guardamos el archivo
    if target_rom not in games:
        print(f" [Auto-discovery] Nueva ROM detectada: '{target_rom}'. Añadiendo a config.json...")
        new_game_entry = {
            "name": target_rom.upper(),
            "hi_file": f"{target_rom}.hi",
            "initials": default_initials,
            "iscored_id": None  # Lo dejas listo para ponerle el ID de iScored cuando lo crees en su web
        }
        games[target_rom] = new_game_entry
        config["games"] = games
        save_config(config, config_path)

    # Procesar el juego normalmente
    process_game(target_rom, games[target_rom], reader, iscored_client, default_initials, hi_folder)


if __name__ == "__main__":
    main()