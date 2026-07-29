from urllib.parse import quote
import requests


class IScoredClient:

    def __init__(self, gameroom: str):
        self.gameroom = gameroom.strip()
        self.base_url = "https://www.iscored.info/api"

    def get_player_score_on_iscored(self, game_id_or_name: str, player_name: str) -> int:
        """Consulta en iScored la puntuación actual que tiene guardada ese jugador."""
        encoded_gameroom = quote(self.gameroom)
        encoded_game = quote(str(game_id_or_name))

        # Endpoint de lectura de puntuaciones del juego
        endpoint = f"{self.base_url}/{encoded_gameroom}/{encoded_game}"

        try:
            response = requests.get(endpoint, timeout=5)
            if response.status_code == 200:
                data = response.json()
                scores = data.get("scores", [])
                target = player_name.strip().upper()
                
                # Buscamos la puntuación del jugador en la lista
                for s in scores:
                    if s.get("name", "").strip().upper() == target:
                        return int(s.get("score", 0))
        except Exception:
            # En caso de fallo en la lectura, devolvemos 0 para permitir el intento de envío
            pass
            
        return 0

    def submit_score(self, game_id_or_name: str, player_name: str, score: int) -> bool:
        """
        Envía una puntuación a la API de iScored tras comprobar si supera la existente.
        """
        # 1. Comprobación previa antes de llamar a la API
        current_iscored_score = self.get_player_score_on_iscored(game_id_or_name, player_name)
        if current_iscored_score > 0 and score <= current_iscored_score:
            print(
                f" [iScored Info] Puntuación local ({score:,}) NO supera "
                f"la existente en iScored ({current_iscored_score:,}). No se enviará."
            )
            return False

        # 2. Envío a la API si es superior
        endpoint = f"{self.base_url}/{quote(self.gameroom)}/{quote(str(game_id_or_name))}/submitScore"
        payload = {
            "playerName": player_name,
            "score": int(score)
        }

        try:
            response = requests.post(endpoint, data=payload, timeout=10)

            if response.status_code == 200:
                res_json = response.json()

                if "submittedScore" in res_json:
                    sub = res_json["submittedScore"]
                    print(
                        f" [iScored] ¡NUEVO RÉCORD SUBIDO! {sub.get('name')} - "
                        f"{int(sub.get('score', 0)):,} pts (Puesto #{sub.get('rank')})"
                    )
                    return True
                else:
                    print(" [iScored Info] El servidor iScored no actualizó la puntuación (récord previo mayor o igual).")
                    return False
            else:
                print(f" [iScored Error {response.status_code}]: {response.text}")
                return False

        except Exception as e:
            print(f" [iScored Error] Excepción al enviar datos: {e}")
            return False