import configparser


class Configreader:

    def __init__(self, config_file='config/configs'):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

    def get(self, section, key):
        return self.config.get(section, key)
