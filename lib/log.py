import logging
import logging.config
import logging.handlers
from config import LOG_FILE, LOG_FILE_ERROR


def setup_logging():
    formatter = logging.Formatter("[ %(asctime)s - %(levelname)s - %(pathname)s - %(module)s - %(funcName)s - %(lineno)d ] - %(message)s")
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = logging.handlers.TimedRotatingFileHandler(LOG_FILE)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)

    errorhandler = logging.handlers.TimedRotatingFileHandler(LOG_FILE_ERROR)
    errorhandler.setLevel(logging.ERROR)
    errorhandler.setFormatter(formatter)

    # if env is not 'production':
    #     consoleHandler = logging.StreamHandler()
    #     consoleHandler.setLevel(logging.ERROR)
    #     consoleHandler.setFormatter(formatter)
    #     logger.addHandler(consoleHandler)

    logger.addHandler(handler)
    logger.addHandler(errorhandler)