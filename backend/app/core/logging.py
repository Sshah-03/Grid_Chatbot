import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

from pythonjsonlogger.json import JsonFormatter


def configure_logging(level: str = "INFO", log_file_path: str = "logs/app.log") -> None:
    formatter = JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    log_path = Path(log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(stream_handler)
    root.addHandler(file_handler)
    root.setLevel(level.upper())
