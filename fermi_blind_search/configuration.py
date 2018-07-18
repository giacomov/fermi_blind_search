import ConfigParser

import os


_configuration = None


def get_config(config_file=None):

    global _configuration

    if _configuration is not None:

        return _configuration

    # If we are here the user need to have passed a configuration file in input
    assert config_file is not None, "This is the first time the configuration is built, " \
                                    "but no file was received as input"

    configuration = ConfigParser.SafeConfigParser()

    # if config_file is not None:
    #     print("SETTING CONFIG FILE")
    #     os.environ['LTF_CONFIG_FILE'] = config_file

    # assert os.environ.get("LTF_CONFIG_FILE") is not None, "You have to set up the LTF_CONFIG_FILE env. variable"

    confPath = os.path.abspath(os.path.expandvars(os.path.expanduser(config_file)))

    assert os.path.exists(confPath), "Configuration path %s does not exist! " % confPath

    configuration.read([confPath])

    # Monkey patch adding the filename
    configuration.config_file = confPath

    _configuration = configuration

    return _configuration


# Read the configuration in module variables,
# so the module will act like a singleton and
# the configuration will be read only one time
# per session

# configuration = ConfigParser.SafeConfigParser()
#
# # Get path of the configuration file
# assert os.environ.get("LTF_CONFIG_FILE") is not None, "You have to set up the LTF_CONFIG_FILE env. variable"
#
# confPath = os.path.abspath(os.path.expandvars(os.path.expanduser(os.environ.get("LTF_CONFIG_FILE"))))
#
# assert os.path.exists(confPath), "Configuration path does not exist!"
#
# configuration.read([confPath])
#
# # Monkey patch adding the filename
# configuration.config_file = confPath