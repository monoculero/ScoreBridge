import os
import re
from pathlib import Path
import cv2
from scorebridge import load_config, save_config


def extract_id_from_qr_url(url: str) -> str | None:
    """Extrae el parámetro del ID de la URL decodificada del QR."""
    match = re.search(r'(?:game|score_id|id)=([a-zA-Z0-9_-]+)', url, re.IGNORECASE)
    if match:
        return match.group(1)
    # Si la URL termina directamente en un ID numérico de 5 a 7 dígitos
    num_match = re.search(r'/(\d{5,7})/?$', url)
    return num_match.group(1) if num_match else None


def update_config_from_qrcodes(qr_folder_path: str = "qrcodes"):
    """
    Lee todas las imágenes QR de la carpeta especificada, decodifica el ID de iScored
    y lo asigna al juego correspondiente en config.json basándose en el nombre de archivo.
    """
    config, config_path = load_config("config.json")
    games = config.get("games", {})
    qr_folder = Path(qr_folder_path)

    if not qr_folder.exists():
        print(f"❌ La carpeta '{qr_folder}' no existe.")
        print(f"Crea la carpeta '{qr_folder_path}' en la raíz y coloca ahí las imágenes de los QR.")
        return

    detector = cv2.QRCodeDetector()
    updated_count = 0

    print(f"🔍 Escaneando archivos de imagen en '{qr_folder.resolve()}'...\n")

    for qr_file in sorted(qr_folder.glob("*.*")):
        if qr_file.suffix.lower() not in [".png", ".jpg", ".jpeg", ".bmp"]:
            continue

        raw_filename = qr_file.stem  # Ej: "Bad Dudes" o "baddudes"
        clean_filename = re.sub(r'[^a-zA-Z0-9]', '', raw_filename).lower()

        # Decodificar el código QR usando OpenCV
        img = cv2.imread(str(qr_file))
        if img is None:
            print(f" ⚠️ No se pudo leer la imagen: {qr_file.name}")
            continue

        decoded_text, _, _ = detector.detectAndDecode(img)
        if not decoded_text:
            print(f" ⚠️ No se detectó código QR en: {qr_file.name}")
            continue

        score_id = extract_id_from_qr_url(decoded_text)
        if not score_id:
            print(f" ⚠️ QR decodificado sin ID reconocible ({decoded_text}) en: {qr_file.name}")
            continue

        print(f"📷 Imagen: '{qr_file.name}' -> ID: {score_id}")

        # Emparejar con los juegos definidos en config.json
        matched = False
        for rom_name, game_info in games.items():
            game_name = game_info.get("name", rom_name)
            clean_game = re.sub(r'[^a-zA-Z0-9]', '', game_name).lower()
            clean_rom = re.sub(r'[^a-zA-Z0-9]', '', rom_name).lower()

            # Comprobar si el nombre del archivo QR coincide con el nombre o ROM del config
            if (clean_filename == clean_game or 
                clean_filename == clean_rom or 
                clean_filename in clean_game or 
                clean_game in clean_filename):
                
                game_info["iscored_id"] = score_id
                print(f"   └─ ✅ Asignado a ROM '{rom_name}' ({game_name})")
                updated_count += 1
                matched = True
                break

        if not matched:
            print(f"   └─ ❓ Sin coincidencia en config.json para el archivo '{raw_filename}'")

    if updated_count > 0:
        save_config(config, config_path)
        print(f"\n🎉 ¡Proceso completado! Se actualizaron {updated_count} IDs en config.json.")
    else:
        print("\n⚠️ No se realizaron cambios en config.json.")


if __name__ == "__main__":
    # Nombre de la carpeta donde descomprimas los QR de iScored
    update_config_from_qrcodes("qrcodes")