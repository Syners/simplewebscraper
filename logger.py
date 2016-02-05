# Source: https://bitbucket.org/richardpenman/webscraping/src/caea72b9331674b8295fc9b33f0bfaea04f6b28c/common.py
import logging
import logging.handlers
import sys


class ConsoleHandler(logging.StreamHandler):
    """Log to stderr for errors else stdout
    """
    def __init__(self):
        logging.StreamHandler.__init__(self)
        self.stream = None

    def emit(self, record):
        if record.levelno >= logging.ERROR:
            self.stream = sys.stderr
        else:
            self.stream = sys.stdout
        logging.StreamHandler.emit(self, record)


def get_logger(output_file, level=logging.INFO, maxbytes=0):
    """Create a logger instance

    output_file:
        file where to save the log
    level:
        the minimum logging level to save
    maxbytes:
        the maxbytes allowed for the log file size. 0 means no limit.
        :param maxbytes:
    """
    logger = logging.getLogger(output_file)
    # avoid duplicate handlers
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        try:
            if not maxbytes:
                file_handler = logging.FileHandler(output_file)
            else:
                file_handler = logging.handlers.RotatingFileHandler(output_file, maxBytes=maxbytes)
        except IOError:
            pass # can not write file
        else:
            file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
            logger.addHandler(file_handler)

        console_handler = ConsoleHandler()
        console_handler.setLevel(level)
        logger.addHandler(console_handler)
    return logger

if __name__ == "__main__":
    logger = get_logger("test.log", maxbytes=2*1024*1024*1024)