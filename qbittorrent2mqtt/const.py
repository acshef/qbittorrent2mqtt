import enum


class EnvVar(enum.StrEnum):
    HOST = "HOST"
    PORT = "PORT"
    USERNAME = "USERNAME"
    PASSWORD = "PASSWORD"
    TIMEOUT = "TIMEOUT"


DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8080
DEFAULT_TIMEOUT = 5


class Icon(enum.StrEnum):
    COUNTER = "mdi:counter"
    PROGRESS_DOWNLOAD = "mdi:progress-download"
