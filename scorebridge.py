import sys
import json
import re
import cv2
import subprocess
import tkinter as tk
from pathlib import Path
from readers.fbneo_reader import FBNeoReader
from iscored_client import IScoredClient


def run_toast_gui(title: str, message: str, is_success: bool = True, display_time_ms: int = 3500):
    """
    Renderiza la ventana flotante OSD en su propio proceso independiente.
    """
    try:
        root = tk.Tk()
        root.overrideredirect(True)           # Sin marco ni barra de ventana
        root.wm_attributes("-topmost", True)  # Siempre por encima de Attract-Mode

        bg_color = "#121820"
        border_color = "#2ecc71" if is_success else "#e74c3c"
        text_color = "#ffffff"
        accent_color = "#2ecc71" if is_success else "#e74c3c"

        root.config(bg=bg_color)

        frame = tk.Frame(root, bg=bg_color, highlightbackground=border_color, highlightthickness=2)
        frame.pack(fill="both", expand=True)

        lbl_title = tk.Label(frame, text=title.upper(), font=("Consolas", 10, "bold"), fg=accent_color, bg=bg_color)
        lbl_title.pack(anchor="w", padx=12, pady=(8, 2))

        lbl_msg = tk.Label(frame, text=message, font=("Consolas", 11), fg=text_color, bg=bg_color)
        lbl_msg.pack(anchor="w", padx=12, pady=(0, 8))

        root.update_idletasks()
        width = root.winfo_reqwidth()
        height = root.winfo_reqheight()
        screen_width = root.winfo_screenwidth()

        target_x = screen_width - width - 20
        start_x = screen_width + 10  # Posición fuera de pantalla a la derecha
        y = 20                       # Margen superior

        # Ajuste estricto del tamaño a la franja del toast
        root.geometry(f"{width}x{height}+{start_x}+{y}")

        def animate_slide_in(current_x):
            if current_x > target_x:
                new_x = max(target_x, current_x - 15)
                root.geometry(f"{width}x{height}+{new_x}+{y}")
                root.after(10, lambda: animate_slide_in(new_x))
            else:
                root.after(display_time_ms, root.destroy)

        animate_slide_in(start_x)
        root.mainloop()
    except Exception as e:
        print(f"[WARN] No se pudo desplegar la notificación OSD: {e}")


def show_achievement_toast(title: str, message: str, is_success: bool = True):
    """
    Lanza la notificación en un proceso en segundo plano totalmente independiente.
    """
    try:
        script_path = str(Path(__file__).resolve())
        subprocess.Popen([
            sys.executable,
            script_path,
            "--toast",
            title,
            message,
            "1" if is_success else "0"
        ])
    except Exception as e:
        print(f"[WARN] No se pudo lanzar el toast en segundo plano: {e}")


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


def find_id_in_qr_folder(rom_name: str, game_name: str, qr_folder_path: Path = Path("qrcodes")) -> str:
    """
    Busca en la carpeta 'qrcodes/' una imagen que coincida con la ROM o nombre del juego,
    decodifica el QR y devuelve el iscored_id.
    """
    if not qr_folder_path.exists():
        return ""

    clean_rom = re.sub(r'[^a-zA-Z0-9]', '', rom_name).lower()
    clean_game = re.sub(r'[^a-zA-Z0-9]', '', game_name).lower()

    detector = cv2.QRCodeDetector()

    for qr_file in qr_folder_path.glob("*.*"):
        if qr_file.suffix.lower() not in [".png", ".jpg", ".jpeg", ".bmp"]:
            continue

        clean_filename = re.sub(r'[^a-zA-Z0-9]', '', qr_file.stem).lower()

        if (clean_filename == clean_rom or 
            clean_filename == clean_game or 
            clean_filename in clean_game or 
            clean_game in clean_filename):

            img = cv2.imread(str(qr_file))
            if img is None:
                continue

            decoded_text, _, _ = detector.detectAndDecode(img)
            if decoded_text:
                match = re.search(r'(?:game|score_id|id)=([a-zA-Z0-9_-]+)', decoded_text, re.IGNORECASE)
                if match:
                    return match.group(1)
                num_match = re.search(r'/(\d{5,7})/?$', decoded_text)
                if num_match:
                    return num_match.group(1)

    return ""


def process_game(rom_name: str, game_info: dict, reader: FBNeoReader, iscored_client: IScoredClient, players_cfg: list, hi_folder: Path):
    hi_filename = game_info.get("hi_file", f"{rom_name}.hi")
    hi_path = hi_folder / hi_filename

    best_match = None

    try:
        # Recorremos cada jugador configurado en la lista global "players"
        for p_info in players_cfg:
            raw_initials = p_info.get("initials", "")
            p_name = p_info.get("name", "Player").strip()
            
            target_initials_list = [init.strip().upper() for init in raw_initials.split(",") if init.strip()]

            for target_init in target_initials_list:
                entry = reader.get_best_score_for_player(str(hi_path), rom_name, target_init)
                if entry:
                    if not best_match or entry.score > best_match["entry"].score:
                        best_match = {
                            "entry": entry,
                            "iscored_name": p_name
                        }

        game_name = game_info.get("name", rom_name)
        print("===================================")
        print(f" JUEGO : {game_name} ({rom_name})")
        print("===================================")

        if best_match:
            best_entry = best_match["entry"]
            iscored_player_name = best_match["iscored_name"]

            print(f"INICIALES EN NVRAM : {best_entry.player}")
            print(f"JUGADOR EN ISCORED : {iscored_player_name}")
            print(f"PUESTO EN TABLA    : #{best_entry.rank}")
            print(f"MEJOR PUNTUACIÓN   : {best_entry.score:,}")

            iscored_id = game_info.get("iscored_id")

            # Si no tiene iscored_id, se intenta obtener leyendo la carpeta qrcodes/
            if not iscored_id:
                found_id = find_id_in_qr_folder(rom_name, game_name, Path("qrcodes"))
                if found_id:
                    print(f" [Auto-discovery] ¡ID '{found_id}' detectado en QR! Actualizando config.json...")
                    iscored_id = found_id
                    game_info["iscored_id"] = found_id

                    # Guardar el nuevo ID en el config.json
                    try:
                        cfg_data, cfg_path = load_config("config.json")
                        if "games" in cfg_data and rom_name in cfg_data["games"]:
                            cfg_data["games"][rom_name]["iscored_id"] = found_id
                            save_config(cfg_data, cfg_path)
                    except Exception as err:
                        print(f" [WARN] No se pudo guardar el ID en config.json: {err}")

            # Subida a iScored
            if iscored_client and iscored_id:
                # Comprobamos en iScored usando el nombre completo mapeado
                current_score = iscored_client.get_player_score_on_iscored(iscored_id, iscored_player_name)
                
                if current_score > 0 and best_entry.score <= current_score:
                    print(f" [Info] Puntuación inferior o igual a la existente ({best_entry.score:,} <= {current_score:,}). Descartada.")
                    show_achievement_toast(
                        title="ℹ️ Puntuación no superada",
                        message=f"La marca de {iscored_player_name} ({best_entry.score:,}) no supera el récord.",
                        is_success=False
                    )
                else:
                    res = iscored_client.submit_score(
                        game_id_or_name=iscored_id,
                        player_name=iscored_player_name,
                        score=best_entry.score,
                    )
                    
                    if res and getattr(res, "status_code", 200) in (200, 201):
                        show_achievement_toast(
                            title=f"🏆 Puntuación Subida - {game_name}",
                            message=f"{iscored_player_name}: {best_entry.score:,}",
                            is_success=True
                        )
                    else:
                        show_achievement_toast(
                            title="⚠️ Error iScored",
                            message="No se pudo subir la puntuación",
                            is_success=False
                        )

            else:
                print(" [Info] Juego sin 'iscored_id' asignado (no se encontró QR). Se omitió la subida a la nube.")
                show_achievement_toast(
                    title="ℹ️ iScored",
                    message="Juego sin 'iscored_id' asignado.",
                    is_success=False
                )
        else:
            print("Sin registros para las iniciales configuradas en 'players'.")
            show_achievement_toast(
                title="？ iScored",
                message="Sin registros para los jugadores configurados",
                is_success=False
            )

        print("===================================\n")

    except Exception as e:
        print(f"Error procesando {rom_name}: {e}\n")
        show_achievement_toast(
            title="❌ Error ScoreBridge",
            message=str(e),
            is_success=False
        )


def main():
    if len(sys.argv) <= 1:
        print("Uso: python scorebridge.py <nombre_rom>")
        return

    config, config_path = load_config("config.json")
    reader = FBNeoReader()

    players_cfg = config.get("players", [{"initials": "ALF", "name": "Alfredo"}])
    hi_folder = Path(config.get("hi_folder", "hi"))

    iscored_cfg = config.get("iscored", {})
    iscored_enabled = iscored_cfg.get("enabled", False)
    gameroom = iscored_cfg.get("gameroom", "")

    iscored_client = IScoredClient(gameroom) if (iscored_enabled and gameroom) else None
    games = config.get("games", {})

    target_rom = sys.argv[1].lower().strip()
    config_updated = False

    if target_rom not in games:
        print(f" [Auto-discovery] Nueva ROM detectada: '{target_rom}'. Añadiendo a config.json...")
        games[target_rom] = {
            "name": target_rom.lower(),
            "hi_file": f"{target_rom}.hi",
            "iscored_id": ""
        }
        config_updated = True

    game_info = games[target_rom]

    if not game_info.get("iscored_id"):
        game_name = game_info.get("name", target_rom)
        print(f" [Auto-discovery] Buscando código QR local para '{game_name}' ({target_rom})...")
        found_id = find_id_in_qr_folder(target_rom, game_name, Path("qrcodes"))

        if found_id:
            print(f" [Auto-discovery] ¡ID obtenido desde el QR local!: '{found_id}'")
            game_info["iscored_id"] = found_id
            config_updated = True
        else:
            print(" [Auto-discovery] No se encontró una imagen QR en 'qrcodes/'. El ID se mantendrá vacío.")

    if config_updated:
        config["games"] = games
        save_config(config, config_path)

    process_game(target_rom, games[target_rom], reader, iscored_client, players_cfg, hi_folder)


if __name__ == "__main__":
    # Modo de ejecución de la notificación OSD
    if len(sys.argv) > 1 and sys.argv[1] == "--toast":
        toast_title = sys.argv[2] if len(sys.argv) > 2 else "Notificación"
        toast_msg = sys.argv[3] if len(sys.argv) > 3 else ""
        toast_success = sys.argv[4] == "1" if len(sys.argv) > 4 else True
        run_toast_gui(toast_title, toast_msg, toast_success)
    else:
        main()