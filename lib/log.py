import logging
import logging.config
from config import LOG_FILE, LOG_FILE_ERROR


def setup_logging():
    formatter = logging.Formatter("[ %(asctime)s - %(levelname)s - %(pathname)s - %(module)s - %(funcName)s - %(lineno)d ] - %(message)s")
    logger = logging.getLogger('couponservice')
    logger.setLevel(logging.INFO)

    handler = logging.handlers.TimedRotatingFileHandler(LOG_FILE)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)

    errorhandler = logging.handlers.TimedRotatingFileHandler(LOG_FILE_ERROR)
    errorhandler.setLevel(logging.ERROR)
    errorhandler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.addHandler(errorhandler)