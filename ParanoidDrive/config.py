import os

class Config(object):
    def __init__(self, path="~\.paranoid")):
        self.path = os.path.expanduser(path)
        try:
            with open(self.path, "r") as config_file:
                self.__dict__.update(json.read(config_file))
        except FileNotFoundError:
            pass

    def save(self):
        with open(self
        json.dump({k:v for k, v in A.__dict__.items() if callable(k) and not k == "path"}, )
        
s
