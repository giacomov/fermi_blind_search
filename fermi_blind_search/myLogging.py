import logging as log
# LEAVE THIS HERE: it is used by other modules
import logging.config as logconfig


def set_level(level):
    # Set up the logger
    numeric_level = getattr(log, level.upper(), None)
    log.basicConfig(format='%(asctime)s : %(levelname)s from %(funcName)s in %(module)s: %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p', level=numeric_level)


class StreamToLogger(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """

    def __init__(self, logger, log_level=log.DEBUG):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():

            if line.find("WARNING") >= 0:

                self.logger.log(log.WARNING, line.rstrip().replace("WARNING", ""))

            else:

                self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        # Do nothing, the log is already flushed every call
        pass

    def close(self):
        log.shutdown()
