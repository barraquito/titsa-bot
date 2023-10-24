import unittest
from unittest import mock

import requests_mock

from titsa_bot.bot import BotHandlerMixin, TelegramBot


class TestBotHandlerMixin(unittest.TestCase):
    def setUp(self):
        self.mixin = BotHandlerMixin()

    def test_get_chat_id(self):
        data = {"message": {"chat": {"id": 12345}}}
        self.assertEqual(self.mixin.get_chat_id(data), 12345)

    def test_get_message(self):
        data = {"message": {"text": "Hello"}}
        self.assertEqual(self.mixin.get_message(data), "Hello")

    @requests_mock.Mocker()
    def test_send_message(self, mocker):
        self.mixin.bot_url = "https://fakeurl.com/"
        mocker.post(self.mixin.bot_url + "sendMessage")

        response = {"chat_id": 12345, "text": "Hello"}
        self.mixin.send_message(response)
        self.assertTrue(mocker.called)
        self.assertEqual(mocker.last_request.json(), response)


class TestTelegramBot(unittest.TestCase):
    def setUp(self):
        self.bot = TelegramBot("dummy_token")

    @mock.patch(
        "titsa_bot.titsa.MessageParser.get_stop_id_from_message", return_value="123"
    )
    @mock.patch(
        "titsa_bot.titsa.TitsaService.get_answer_text",
        return_value="Bus arriving in 10 mins",
    )
    def test_prepare_data_for_answer(
        self, mocked_get_answer_text, mocked_get_stop_id_from_message
    ):
        data = {"message": {"chat": {"id": 12345}, "text": "Stop 123"}}
        expected_response = {
            "chat_id": 12345,
            "text": "Bus arriving in 10 mins",
        }
        self.assertEqual(self.bot.prepare_data_for_answer(data), expected_response)

    @mock.patch.object(TelegramBot, "send_message")
    @mock.patch(
        "titsa_bot.bot.bottle_request",
        new=mock.Mock(json={"message": {"chat": {"id": 12345}, "text": "Stop 123"}}),
    )
    def test_post_handler(self, mocked_send):
        self.bot.post_handler()
        mocked_send.assert_called()
