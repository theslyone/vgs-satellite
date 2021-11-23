import logging


LOG_FORMAT = '[%(levelname)s][%(asctime)s][%(processName)s][%(threadName)s] %(message)s'


def configure(log_path: str = None, silent: bool = False, level: str = "INFO"):
    root = logging.getLogger()
    formatter = logging.Formatter(LOG_FORMAT)

    if not silent:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)

    if log_path:
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    if not root.handlers:
        root.addHandler(logging.NullHandler())

    logging.getLogger('alembic').setLevel(logging.WARNING)

    root.setLevel(logging.getLevelName(level))
