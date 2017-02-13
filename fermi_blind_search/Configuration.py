import ConfigParser
import os

#Read the configuration in module variables,
#so the module will act like a singleton and
#the configuration will be read only one time
#per session

configuration                 = ConfigParser.SafeConfigParser()

#Get path of the configuration file
confPath                      = os.path.abspath(os.path.join(os.path.dirname(__file__),'configuration.txt'))

configuration.read([confPath])

#Add the package path in the Internal section
#(which is not written in the configuration file)
configuration.add_section("Internal")

configuration.set("Internal","packagePath",os.path.dirname(confPath))
