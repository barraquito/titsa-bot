import logging
import re

import requests


logger = logging.getLogger(__name__)


class DataCleaner:
    @staticmethod
    def clean_str(s):
        try:
            return s.encode("latin-1").decode("utf-8")
        except UnicodeDecodeError:
            return s


class TitsaApi:
    STOP_INFO_URL = "https://titsa.com/ajax/xGetInfoParada.php"

    def __init__(self, stop_id):
        self.stop_id = stop_id
        self.stop_data = None

    def get_stop_info(self):
        if not self.stop_data:
            response = requests.get(
                self.STOP_INFO_URL, {"id_parada": self.stop_id}, timeout=5
            )
            logger.info(
                f"Successfully fetched data for stop ID: {self.stop_id} ({response.elapsed.total_seconds()}s)"
            )
            self.stop_data = response.json()
        return self.stop_data


class TitsaClient:
    def __init__(self, stop_id):
        self.api = TitsaApi(stop_id)
        self.cleaner = DataCleaner()

    def get_stop_description(self):
        stop_description = (
            self.api.get_stop_info().get("parada", {}).get("descripcion", "")
        )
        return self.cleaner.clean_str(stop_description)

    def get_stop_lines(self):
        lines = self.api.get_stop_info().get("lineas") or []
        return [
            {
                "id": line["id"],
                "time": line["tiempo"],
                "destination": self.cleaner.clean_str(line["destino"]),
            }
            for line in lines
        ]


class MessageParser:
    @staticmethod
    def get_stop_id_from_message(message):
        match = re.search(r"parada (\d+)", message, flags=re.I)
        if match:
            return match.group(1)
        else:
            return


class WaitingTimeEmoji:
    @staticmethod
    def get_waiting_time_emoji(time):
        emojis = {"0": "🟢", "1": "🟠"}
        return emojis.get(str(int(int(time) / 5)), "🔴")


class TitsaService:
    def __init__(self, stop_id):
        self.stop_id = stop_id
        self.titsa_stop = TitsaClient(stop_id)

    def get_answer_text(self):
        if not self.stop_id:
            return (
                "Lo siento, no entiendo tu mensaje. Prueba a incluir la "
                'palabra "parada" seguido del número de parada.'
            )
        try:
            return self._fetch_stop_info()
        except requests.Timeout as exc:
            logger.error(
                f"Failed to fetch data for stop ID {self.stop_id}. Error: {exc}"
            )
            return (
                "No hay información de guaguas cercanas a esta parada. "
                "Inténtalo en unos minutos."
            )

    def _fetch_stop_info(self):
        stop_description = self.titsa_stop.get_stop_description()
        answer_text = [
            f"Las próximas guaguas en la parada {self.stop_id} ({stop_description}) son:"
        ]

        stop_lines = self.titsa_stop.get_stop_lines()

        if not stop_lines:
            answer_text.append("No hay información de guaguas cercanas...")
        else:
            for line in stop_lines:
                emoji = WaitingTimeEmoji.get_waiting_time_emoji(line["time"])
                answer_text.append(
                    f"{emoji} {line['id']} ({line['time']} minutos) con destino {line['destination']}"
                )

        return answer_text
