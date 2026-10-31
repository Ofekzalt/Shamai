import signal
import time

from app.core.config import get_settings
from app.core.logging import configure_logging

configure_logging(get_settings().log_level)


def _stop(*_args: object) -> None:
    raise SystemExit(0)


def main() -> None:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
