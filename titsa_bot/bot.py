import logging
import os

import requests
from bottle import Bottle, request as bottle_request, response

from .titsa import MessageParser, TitsaService

logging_level = os.getenv("LOGGING_LEVEL", "INFO")

logging.basicConfig(
    level=eval(f"logging.{logging_level}"), format="%(asctime)s - %(levelname)s - %(message)s"
)


class BotHandlerMixin:
    def __init__(self):
        super(BotHandlerMixin, self).__init__()
        self.bot_url = None

    def get_chat_id(self, data):
        return data.get("message", {}).get("chat", {}).get("id")

    def get_message(self, data):
        return data.get("message", {}).get("text", "")

    def send_message(self, response):
        message_url = self.bot_url + "sendMessage"
        requests.post(message_url, json=response)


class TelegramBot(BotHandlerMixin, Bottle):
    BOT_BASE_URL = "https://api.telegram.org/bot"

    def __init__(self, token):
        super(TelegramBot, self).__init__()
        self.bot_url = f"{self.BOT_BASE_URL}{token}/"
        self.route("/", callback=self.post_handler, method="POST")

    def prepare_data_for_answer(self, data):
        message = self.get_message(data)
        stop_id = MessageParser.get_stop_id_from_message(message)
        service = TitsaService(stop_id)
        answer_text = service.get_answer_text()
        return {
            "chat_id": self.get_chat_id(data),
            "text": (
                "\n".join(answer_text) if isinstance(answer_text, list) else answer_text
            ),
        }

    def post_handler(self):
        data = bottle_request.json
        response_body = self.prepare_data_for_answer(data)
        self.send_message(response_body)
        logging.debug(
            f"Sent response to chat ID {response_body['chat_id']}: {response_body['text']}"
        )
        return response


if __name__ == "__main__":
    bot_token = os.getenv("BOT_TOKEN")
    app = TelegramBot(bot_token)
    app.run(host="0.0.0.0", port=8080)
