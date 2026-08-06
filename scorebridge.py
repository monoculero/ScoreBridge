import sys
import json
import re
import cv2
import tkinter as tk
from pathlib import Path
from readers.fbneo_reader import FBNeoReader
from iscored_client import IScoredClient


def show_achievement_toast(title: str, message: str, is_success: bool = True, display_time_ms: int = 3500):
    """
    Muestra un mensaje emergente animado arriba a la derecha del escritorio
    simulando la notificación de un logro de RetroArch.
    """
    try:
        root = tk.Tk()
        root.overrideredirect(True)           # Sin marco ni barra de ventana
        root.wm_attributes("-topmost", True)  # Siempre por encima del resto de ventanas

        bg_color = "#121820"
        border_color = "#2ecc71" if is_success else "#e74c3c"
        text_color = "#ffffff"
        accent_color = "#2ecc71" if is_success else "#e74c3c"

        frame = tk.Frame(root, bg=bg_color, highlightbackground=border_color, highlightthickness=2)
        frame.pack(fill="both", expand=True)

        lbl_title = tk.Label(frame, text=title.upper(), font=("Consolas", 10, "bold"), fg=accent_color, bg=bg_color)
        lbl_title.pack(anchor="w", padx=12, pady=(8, 2))

        lbl_msg = tk.Label(frame, text=message, font=("Consolas", 11), fg=text_color, bg=bg_color)
        lbl_msg.pack(anchor="w", padx=12, pady=(0, 8))

        root.update_idletasks()
        width = root.winfo_width()
        screen_width = root.winfo_screenwidth()

        target_x = screen_width - width - 20
        start_x = screen_width + 10  # Posición fuera de pantalla a la derecha
        y = 20                       # Margen superior

        root.geometry(f"+{start_x}+{y}")

        def animate_slide_in(current_x):
            if current_x > target_x:
                new_x = max(target_x, current_x - 15)
                root.geometry(f"+{new_x}+{y}")
                root.after(10, lambda: animate_slide_in(new_x))
            else:
                root.after(display_time_ms, root.destroy)

        animate_slide_in(start_x)
        root.mainloop()
    except Exception as e:
        print(f"[WARN] No se pudo desplegar la notificación OSD: {e}")


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

        # Comprobar coincidencia con la ROM o el nombre
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


def process_game(rom_name: str, game_info: dict, reader: FBNeoReader, iscored_client: IScoredClient, default_initials: str, hi_folder: Path):
    hi_filename = game_info.get("hi_file", f"{rom_name}.hi")
    hi_path = hi_folder / hi_filename
    
    raw_initials = game_info.get("initials", default_initials)
    target_initials_list = [init.strip().upper() for init in raw_initials.split(",") if init.strip()]

    try:
        best_entry = None
        for target_init in target_initials_list:
            entry = reader.get_best_score_for_player(str(hi_path), rom_name, target_init)
            if entry:
                if not best_entry or entry.score > best_entry.score:
                    best_entry = entry

        game_name = game_info.get("name", rom_name)
        print("===================================")
        print(f" JUEGO : {game_name} ({rom_name})")
        print("===================================")

        if best_entry:
            print(f"INICIALES BUSCADAS : {', '.join(target_initials_list)}")
            print(f"JUGADOR REGISTRADO : {best_entry.player}")
            print(f"PUESTO EN TABLA    : #{best_entry.rank}")
            print(f"MEJOR PUNTUACIÓN   : {best_entry.score:,}")

            iscored_id = game_info.get("iscored_id")
            if iscored_client and iscored_id:
                current_score = iscored_client.get_player_score_on_iscored(iscored_id, best_entry.player)
                
                if current_score > 0 and best_entry.score <= current_score:
                    print(f" [Info] Puntuación inferior o igual a la existente ({best_entry.score:,} <= {current_score:,}). Descartada.")
                    show_achievement_toast(
                        title="ℹ️ Puntuación no superada",
                        message=f"La marca de {best_entry.player} ({best_entry.score:,}) no supera el récord.",
                        is_success=False
                    )
                else:
                    res = iscored_client.submit_score(
                        game_id_or_name=iscored_id,
                        player_name=best_entry.player,
                        score=best_entry.score,
                    )
                    
                    if res and getattr(res, "status_code", 200) in (200, 201):
                        show_achievement_toast(
                            title=f"🏆 Puntuación Subida - {game_name}",
                            message=f"{best_entry.player}: {best_entry.score:,}",
                            is_success=True
                        )
                    else:
                        show_achievement_toast(
                            title="⚠️ Error iScored",
                            message="No se pudo subir la puntuación",
                            is_success=False
                        )

            elif not iscored_id:
                print(" [Info] Juego sin 'iscored_id' asignado. Se omitió la subida a la nube.")
                show_achievement_toast(
                    title="ℹ️ iScored",
                    message="Juego sin 'iscored_id' asignado.",
                    is_success=False
                )
        else:
            print(f"Sin registros para las iniciales: {', '.join(target_initials_list)}")
            show_achievement_toast(
                title="？ iScored",
                message="Sin registros para las iniciales indicadas",
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

    default_initials = config.get("default_initials", "ALF")
    hi_folder = Path(config.get("hi_folder", "hi"))

    iscored_cfg = config.get("iscored", {})
    iscored_enabled = iscored_cfg.get("enabled", False)
    gameroom = iscored_cfg.get("gameroom", "")

    iscored_client = IScoredClient(gameroom) if (iscored_enabled and gameroom) else None
    games = config.get("games", {})

    target_rom = sys.argv[1].lower().strip()

    config_updated = False

    # 1. Si la ROM no existe en config.json, la creamos
    if target_rom not in games:
        print(f" [Auto-discovery] Nueva ROM detectada: '{target_rom}'. Añadiendo a config.json...")
        games[target_rom] = {
            "name": target_rom.lower(),
            "hi_file": f"{target_rom}.hi",
            "initials": default_initials,
            "iscored_id": ""
        }
        config_updated = True

    game_info = games[target_rom]

    # 2. Si iscored_id está vacío, buscamos la imagen QR en la carpeta 'qrcodes/'
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

    # Guardar config.json si se añadió la ROM o el ID
    if config_updated:
        config["games"] = games
        save_config(config, config_path)

    # 3. Procesar y subir puntuación
    process_game(target_rom, games[target_rom], reader, iscored_client, default_initials, hi_folder)


if __name__ == "__main__":
    main()