import abc
import datetime
import functools
import typing as t

from x2mqtt import DeviceClass, Payload
from x2mqtt import Sensor as _Sensor

from .const import Icon

if t.TYPE_CHECKING:
    from .app import App

__all__ = [
    "TotalTorrentsSensor",
    "DownloadingTorrentsSensor",
    "NextETASensor",
    "FinalETASensor",
    "ProgressTotalSensor",
    "ProgressActiveSensor",
    "DownloadSpeedSensor",
]

Sensor = _Sensor[list[dict]]


class _SelfAvailableSensor(Sensor):
    device_availability_topic: str

    def __init__(self, *args, device_availability_topic: str, **kwargs):
        self.device_availability_topic = device_availability_topic
        super().__init__(*args, **kwargs)

    @functools.cached_property
    def availability_topic(self) -> str:
        return f"{self.base_topic}/availability"

    def get_discovery_payload(self):
        return {
            **super().get_discovery_payload(),
            "availability": [
                {"topic": self.availability_topic},
                {"topic": self.device_availability_topic},
            ],
            "availability_mode": "all",
        }

    def publish_availability(self, online: bool, /):
        value = Payload.ONLINE if online else Payload.OFFLINE
        self._publish(self.availability_topic, value)

    @classmethod
    def from_app(cls, app: "App", *args, **kwargs) -> t.Self:
        return cls(
            *args,
            client=app.client,
            qos=app.mqtt_qos,
            device_availability_topic=app.availability_topic,
            topic_prefix=app.topic_prefix,
            log=app.log,
            **kwargs,
        )


class _IntegerSensor(Sensor):
    def get_discovery_payload(self):
        return {
            **super().get_discovery_payload(),
            "suggested_display_precision": 0,
        }


class TotalTorrentsSensor(_IntegerSensor):
    name = "Total Torrents"
    icon = Icon.COUNTER

    def get_state(self, data):
        if isinstance(data, Exception):
            return 0

        return len(data)

    def get_attributes(self, data):
        if isinstance(data, Exception):
            return

        return {"names": sorted(x["name"] for x in data)}


class DownloadingTorrentsSensor(_IntegerSensor):
    name = "Downloading Torrents"
    icon = Icon.COUNTER

    def get_state(self, data):
        if isinstance(data, Exception):
            return 0

        return len([x for x in data if is_downloading(x)])

    def get_attributes(self, data):
        if isinstance(data, Exception):
            return

        return {"names": sorted(x["name"] for x in data if is_downloading(x))}


class _ETASensor(_SelfAvailableSensor, metaclass=abc.ABCMeta):
    device_class = DeviceClass.TIMESTAMP

    @functools.cached_property
    def local_tz(self) -> datetime.tzinfo:
        return datetime.datetime.now().astimezone().tzinfo

    def get_state(self, data):
        eta_dt = datetime.datetime.now().replace(microsecond=0, tzinfo=self.local_tz)
        try:
            if isinstance(data, Exception):
                raise data
            agg_value = self.aggregate(self.get_eta(x) for x in data if is_downloading(x))
            eta_dt += datetime.timedelta(seconds=agg_value)
            self.publish_availability(True)
        except Exception:
            self.publish_availability(False)

        return eta_dt.isoformat()

    @abc.abstractmethod
    def aggregate(self, values: t.Iterable[int]) -> int: ...

    @staticmethod
    def get_eta(data: dict) -> int:
        return data["eta"]


class NextETASensor(_ETASensor):
    name = "Next ETA"

    def aggregate(self, values):
        return min(values)

    def get_attributes(self, data):
        if isinstance(data, Exception):
            return

        downloading_torrents = list(x for x in data if is_downloading(x))

        for x in sorted(downloading_torrents, key=self.get_eta):
            # The torrent with the soonest eta is sorted first
            return {"name": x["name"]}


class FinalETASensor(_ETASensor):
    name = "Final ETA"

    def aggregate(self, values):
        return max(values)


class ProgressTotalSensor(Sensor):
    name = "Total Progress"
    unit_of_measurement = "%"
    icon = Icon.PROGRESS_DOWNLOAD

    def get_state(self, data):
        if isinstance(data, Exception):
            return 100

        if not data:
            return 100

        total = 0  # Bytes
        progress = 0  # Bytes

        for x in data:
            this_total_size = x["total_size"]
            if this_total_size < 0:
                continue
            total += this_total_size
            progress += x["progress"] * this_total_size

        return progress / total * 100


class ProgressActiveSensor(Sensor):
    name = "Active Progress"
    unit_of_measurement = "%"
    icon = Icon.PROGRESS_DOWNLOAD

    def get_state(self, data):
        if isinstance(data, Exception):
            return 100

        if not data:
            return 100

        active = list(x for x in data if is_downloading(x))

        if not active:
            return 0

        total = 0
        progress = 0

        for x in active:
            total += x["total_size"]
            progress += x["progress"] * x["total_size"]

        return progress / total * 100


class DownloadSpeedSensor(Sensor):
    name = "Download Speed"
    unit_of_measurement = "B/s"
    device_class = DeviceClass.DATA_RATE

    def get_state(self, data):
        if isinstance(data, Exception):
            return 0

        if not data:
            return 0

        try:
            return sum(x["dlspeed"] for x in data)
        except ValueError:
            return 0


def is_downloading(data: dict) -> bool:
    return (
        data["state"] in ("downloading", "forcedDL")
        and data["eta"] < 8640000
        and data["dlspeed"] > 0
    )
