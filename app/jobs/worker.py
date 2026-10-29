import signal
import time


def _stop(*_args: object) -> None:
    raise SystemExit(0)


def main() -> None:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
