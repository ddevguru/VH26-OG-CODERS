import logging
import sys
from rich.logging import RichHandler


def get_logger(name: str = "leakguard") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = RichHandler(rich_tracebacks=True, show_time=False, show_path=False)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
