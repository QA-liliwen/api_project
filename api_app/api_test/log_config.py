import os
import logging
from logging.handlers import TimedRotatingFileHandler

# 日志根目录
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/logs")
DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"


def get_logger(name, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if logger.handlers:
        return logger
    log_file_name = os.environ.get("LOG_FILE_NAME")
    log_file = os.path.join(LOG_DIR, log_file_name)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(DEFAULT_FORMAT, DEFAULT_DATEFMT))
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(DEFAULT_FORMAT, DEFAULT_DATEFMT))
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger
