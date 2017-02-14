import ConfigParser

import os

# Read the configuration in module variables,
# so the module will act like a singleton and
# the configuration will be read only one time
# per session

configuration = ConfigParser.SafeConfigParser()

# Get path of the configuration file
assert os.environ.get("LTF_CONFIG_FILE") is not None, "You have to set up the LTF_CONFIG_FILE env. variable"

confPath = os.path.abspath(os.path.expandvars(os.path.expanduser(os.environ.get("LTF_CONFIG_FILE"))))

assert os.path.exists(confPath), "Configuration path does not exist!"

configuration.read([confPath])

