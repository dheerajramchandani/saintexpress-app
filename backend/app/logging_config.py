import logging

# logging_config.py
import logging

def setup_logging(level=logging.INFO):
    logger = logging.getLogger("app")
    logger.setLevel(level)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)

    # IMPORTANT: do not propagate to root
    logger.propagate = False
