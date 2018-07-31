import os
import sys

from fermi_blind_search import myLogging

_logger = myLogging.log.getLogger("make_directory")

# Now overwrite stdout and stderr so they will go to the logger
sl = myLogging.StreamToLogger(_logger, myLogging.log.DEBUG)
sys.stdout = sl

sl = myLogging.StreamToLogger(_logger, myLogging.log.ERROR)
sys.stderr = sl


def make_dir_if_not_exist(path):

    global _logger

    # check if the directory already exists
    if not os.path.exists(path):
        # it doesn't! so we try to make it
        try:
            os.makedirs(path)
        except:
            _logger.error("Could not make the directory %s" % path)
            raise
        else:
            _logger.info("successfully created dir %s" % path)