from x2mqtt import DeviceClass
from x2mqtt import Sensor as _Sensor

from .const import Icon

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


class _IntegerSensor(Sensor):
    def get_discovery_payload(self):
        return {**super().get_discovery_payload(), "suggested_display_precision": 0}


class TotalTorrentsSensor(_IntegerSensor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="Total Torrents", icon=Icon.COUNTER, **kwargs)

    def get_state(self, data):
        if isinstance(data, Exception):
            return 0

        return len(data)


class DownloadingTorrentsSensor(_IntegerSensor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="Downloading Torrents", icon=Icon.COUNTER, **kwargs)

    def get_state(self, data):
        if isinstance(data, Exception):
            return 0

        return len([x for x in data if is_downloading(x)])


class NextETASensor(_IntegerSensor):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            name="Next ETA",
            device_class=DeviceClass.DURATION,
            unit_of_measurement="s",
            **kwargs,
        )

    def get_state(self, data):
        if isinstance(data, Exception):
            return 0

        try:
            return min(self.get_eta(x) for x in data if is_downloading(x))
        except ValueError:
            return 0

    @staticmethod
    def get_eta(data: dict) -> int:
        return data["eta"]


class FinalETASensor(_IntegerSensor):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            name="Final ETA",
            device_class=DeviceClass.DURATION,
            unit_of_measurement="s",
            **kwargs,
        )

    def get_state(self, data):
        if isinstance(data, Exception):
            return 0

        try:
            return max(self.get_eta(x) for x in data if is_downloading(x))
        except ValueError:
            return 0

    @staticmethod
    def get_eta(data: dict) -> int:
        return data["eta"]


class ProgressTotalSensor(Sensor):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            name="Total Progress",
            unit_of_measurement="%",
            icon=Icon.PROGRESS_DOWNLOAD,
            **kwargs,
        )

    def get_state(self, data):
        if isinstance(data, Exception):
            return 100

        if not data:
            return 100

        total = 0
        progress = 0

        for x in data:
            total += x["total_size"]
            progress += x["progress"] * x["total_size"]

        return progress / total * 100


class ProgressActiveSensor(Sensor):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            name="Active Progress",
            unit_of_measurement="%",
            icon=Icon.PROGRESS_DOWNLOAD,
            **kwargs,
        )

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
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            name="Download Speed",
            unit_of_measurement="B/s",
            device_class=DeviceClass.DATA_RATE,
            **kwargs,
        )

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
