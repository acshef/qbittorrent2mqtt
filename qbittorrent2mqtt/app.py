import functools

import requests
from x2mqtt import App as _App

from .const import *
from .sensor import *


class App(_App[list[dict]]):
    app_name = "qbittorrent2mqtt"
    app_description = "Captures qBitTorrent data and publishes to MQTT for Home Assistant"
    env_var_prefix = "QBITTORRENT2MQTT"

    timeout: float
    host: str
    port: str
    username: str
    password: str

    session: requests.Session

    @functools.cached_property
    def api_base_url(self) -> str:
        return f"http://{self.host}:{self.port}/api/v2"

    def make_entities(self):
        return [
            *super().make_entities(),
            TotalTorrentsSensor.from_app(self),
            DownloadingTorrentsSensor.from_app(self),
            NextETASensor.from_app(self),
            FinalETASensor.from_app(self),
            ProgressTotalSensor.from_app(self),
            ProgressActiveSensor.from_app(self),
            DownloadSpeedSensor.from_app(self),
        ]

    def get_discovery_payload(self, entities):
        payload = super().get_discovery_payload(entities)
        payload.pop("availability_topic", None)
        payload["availability"] = [{"topic": self.availability_topic}]

        return payload

    def setup_api(self):
        self.session = requests.Session()
        if self.username and self.password:
            self.session.post(
                f"{self.api_base_url}/auth/login",
                data={
                    "username": self.username,
                    "password": self.password,
                },
            )

    def get_data(self) -> dict:
        resp = self.session.get(f"{self.api_base_url}/torrents/info", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    @classmethod
    def get_version(cls):
        from . import __version__

        return __version__

    @classmethod
    def setup_app_args(cls, parser):
        super().setup_app_args(parser)

        timeout_kwargs = {}
        try:
            timeout_kwargs["default"] = int(cls.getenv("TIMEOUT"))
        except Exception:
            timeout_kwargs["default"] = DEFAULT_TIMEOUT
        parser.add_argument(
            "--timeout",
            type=float,
            metavar="SEC",
            help=f"Delay before timing out API calls. Defaults to the value of {cls.envname(EnvVar.TIMEOUT)} environment variable or {DEFAULT_TIMEOUT!r} if that's not set",
        )

        parser.add_argument(
            "--host",
            default=cls.getenv(EnvVar.HOST) or DEFAULT_HOST,
            metavar="HOST",
            help=f"WebUI hostname. Defaults to the value of the {cls.envname(EnvVar.HOST)} environment variable or {DEFAULT_HOST!r} if that's not set",
        )
        parser.add_argument(
            "--port",
            default=cls.getenv(EnvVar.PORT) or DEFAULT_PORT,
            metavar="N",
            help=f"WebUI port. Defaults to the value of the {cls.envname(EnvVar.PORT)} environment variable or {DEFAULT_PORT!r} if that's not set",
        )
        parser.add_argument(
            "--username",
            default=cls.getenv(EnvVar.USERNAME),
            metavar="USERNAME",
            help=f"WebUI username. Defaults to the value of the {cls.envname(EnvVar.USERNAME)} environment variable or will try without authentication if that's not set",
        )
        parser.add_argument(
            "--password",
            default=cls.getenv(EnvVar.PASSWORD),
            metavar="PASSWORD",
            help=f"WebUI password. Defaults to the value of the {cls.envname(EnvVar.PASSWORD)} environment variable or will try without authentication if that's not set",
        )
