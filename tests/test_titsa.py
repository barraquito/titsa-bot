import unittest

import requests
import requests_mock

from titsa_bot.titsa import (
    DataCleaner,
    MessageParser,
    TitsaApi,
    TitsaClient,
    TitsaService,
    TitsaStopDoesNotExist,
    WaitingTimeEmoji,
)


class TestDataCleaner(unittest.TestCase):
    def setUp(self):
        self.cleaner = DataCleaner()

    def test_clean_str(self):
        s = "RAM\u00c3\u0093N Y CAJAL"
        r = "RAMÓN Y CAJAL"
        self.assertEqual(self.cleaner.clean_str(s), r)

        s = "FINCA ESPA\u00c3\u0091A"
        r = "FINCA ESPAÑA"
        self.assertEqual(self.cleaner.clean_str(s), r)

        # str already cleaned should return same str
        s = "RAMÓN Y CAJAL"
        r = "RAMÓN Y CAJAL"
        self.assertEqual(self.cleaner.clean_str(s), r)


class TestTitsaApi(unittest.TestCase):
    def setUp(self):
        self.api = TitsaApi("123")

    @requests_mock.Mocker()
    def test_get_stop_info(self, m):
        url = TitsaApi.STOP_INFO_URL
        response_json = {"some_key": "some_value"}
        m.get(url, json=response_json)
        self.assertEqual(self.api.get_stop_info(), response_json)

    @requests_mock.Mocker()
    def test_timeout(self, m):
        url = TitsaApi.STOP_INFO_URL
        m.get(url, exc=requests.Timeout)
        with self.assertRaises(requests.Timeout):
            self.api.get_stop_info()


class TestTitsaClient(unittest.TestCase):
    def setUp(self):
        self.client = TitsaClient("123")

    @requests_mock.Mocker()
    def test_get_stop_description(self, m):
        url = TitsaApi.STOP_INFO_URL
        response_json = {"parada": {"descripcion": "Some description"}}
        m.get(url, json=response_json)
        self.assertEqual(self.client.get_stop_description(), "Some description")

    @requests_mock.Mocker()
    def test_get_stop_description_stop_does_not_exist(self, m):
        url = TitsaApi.STOP_INFO_URL
        response_json = {"parada": {}}
        m.get(url, json=response_json)
        with self.assertRaises(TitsaStopDoesNotExist):
            self.client.get_stop_description()

    @requests_mock.Mocker()
    def test_get_stop_lines(self, m):
        url = TitsaApi.STOP_INFO_URL
        response_json = {
            "lineas": [{"id": "1", "tiempo": "5", "destino": "Destination 1"}]
        }
        m.get(url, json=response_json)
        expected_result = [{"id": "1", "time": "5", "destination": "Destination 1"}]
        self.assertEqual(self.client.get_stop_lines(), expected_result)

    @requests_mock.Mocker()
    def test_get_stop_lines_no_lines(self, m):
        url = TitsaApi.STOP_INFO_URL
        response_json = {}
        m.get(url, json=response_json)
        expected_result = []
        self.assertEqual(self.client.get_stop_lines(), expected_result)


class TestMessageParser(unittest.TestCase):
    def test_get_stop_id_from_message(self):
        message = "Información sobre la parada 123, por favor."
        self.assertEqual(MessageParser.get_stop_id_from_message(message), "123")
        message = "Información sobre la parada."
        self.assertIsNone(MessageParser.get_stop_id_from_message(message))


class TestWaitingTimeEmoji(unittest.TestCase):
    def test_get_waiting_time_emoji(self):
        self.assertEqual(WaitingTimeEmoji.get_waiting_time_emoji("0"), "🟢")
        self.assertEqual(WaitingTimeEmoji.get_waiting_time_emoji("5"), "🟠")
        self.assertEqual(WaitingTimeEmoji.get_waiting_time_emoji("10"), "🔴")


class TestTitsaService(unittest.TestCase):
    def setUp(self):
        self.service = TitsaService("123")

    @requests_mock.Mocker()
    def test_get_answer_text(self, m):
        url = TitsaApi.STOP_INFO_URL
        response_json = {
            "parada": {"descripcion": "Some description"},
            "lineas": [{"id": 1, "tiempo": 5, "destino": "Destination 1"}],
        }
        m.get(url, json=response_json)
        expected_result = [
            "Las próximas guaguas en la parada 123 (Some description) son:",
            "🟠 1 (5 minutos) con destino Destination 1",
        ]
        self.assertEqual(self.service.get_answer_text(), expected_result)

    @requests_mock.Mocker()
    def test_get_answer_text_no_lines(self, m):
        url = TitsaApi.STOP_INFO_URL
        response_json = {"parada": {"descripcion": "Some description"}}
        m.get(url, json=response_json)
        expected_result = [
            "Las próximas guaguas en la parada 123 (Some description) son:",
            "No hay información de guaguas cercanas...",
        ]
        self.assertEqual(self.service.get_answer_text(), expected_result)

    @requests_mock.Mocker()
    def test_get_answer_text_stop_does_not_exist(self, m):
        url = TitsaApi.STOP_INFO_URL
        response_json = {"parada": {}}
        m.get(url, json=response_json)
        expected_result = (
            "El número de parada parece incorrecto. Compruebálo y vuelve a intentarlo."
        )
        self.assertEqual(self.service.get_answer_text(), expected_result)

    @requests_mock.Mocker()
    def test_get_answer_text_raise_timeout(self, m):
        url = TitsaApi.STOP_INFO_URL
        m.get(url, exc=requests.Timeout)
        expected_result = "No hay información de guaguas cercanas a esta parada. Inténtalo en unos minutos."
        self.assertEqual(self.service.get_answer_text(), expected_result)
