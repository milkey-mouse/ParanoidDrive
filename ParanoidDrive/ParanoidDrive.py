from progressbar import ProgressBar, Bar, ETA  # progressbar2
import argparse
import hashlib
import getpass
import base64
import time
import json
import sys
import os


class Config(object):
    def __init__(self, path="~/.paranoid"):
        self._path = os.path.expanduser(path)
        self._config_dict = {}
        try:
            with open(self._path, "r") as config_file:
                self._config_dict = json.load(config_file)
        except FileNotFoundError:
            if path != "~/.paranoid":
                raise FileNotFoundError
            else:
                try:
                    with open(os.path.expanduser("~/.paranoid"), "r") as config_file:
                        print("WARNING: Can't find custom config file, falling back to default location.", file=sys.stderr)
                        self._config_dict = json.read(config_file)
                except FileNotFoundError:
                    pass
        if "newkey" in self:
            if not (len(sys.argv) > 1 and sys.argv[1] == "key"):
                print("To finish re-encrypting your files and eradicate your old key, run", file=sys.stderr)
                print("    " + sys.argv[0] + " key", file=sys.stderr)
                print("", file=sys.stderr)
            self.newkey = self.decode_key(self.newkey)
        if "key" in self:
            self.key = self.decode_key(self.key)
        else:
            print("No encryption key was found. A new one is being generated.")
            self.key = os.urandom(32)
            self.save()

    def __contains__(self, value):
        return value in self._config_dict

    def _get(self, key):
        if key.startswith("_"):
            return self.__dict__[key]
        else:
            return self.__dict__["_config_dict"][key]

    def _set(self, key, val):
        if key.startswith("_"):
            self.__dict__[key] = val
        else:
            self.__dict__["_config_dict"][key] = val

    def _del(self, key):
        if key.startswith("_"):
            del self.__dict__[key]
        else:
            del self.__dict__["_config_dict"][key]

    __getattr__ = __getitem__ = _get
    __setattr__ = __setitem__ = _set
    __delattr__ = __delitem__ = _del

    def decode_key(self, key):
        return base64.b16decode(key.upper().encode("utf-8"))

    def encode_key(self, key):
        return base64.b16encode(key).decode("utf-8").lower()

    def save(self):
        with open(self._path, "w") as config_file:
            save_dict = self._config_dict.copy()
            save_dict["key"] = self.encode_key(save_dict["key"])
            if "newkey" in save_dict:
                save_dict["newkey"] = self.encode_key(save_dict["newkey"])
            json.dump(save_dict, config_file)


class ParanoidDrive:
    def __init__(self):
        parser = argparse.ArgumentParser(description="Upload and download encrypted files to OneDrive.")
        parser.add_argument("-c", "--config-location")
        subparsers = parser.add_subparsers(dest="operation")

        uploader = subparsers.add_parser("upload", help="Upload a file/folder to OneDrive.")
        uploader.add_argument("path", type=argparse.FileType("rb", 0), help="Path to the file/folder you want to upload.", default=".")

        downloader = subparsers.add_parser("download", help="Download a file/folder from OneDrive.")
        downloader.add_argument("path", type=argparse.FileType("wb", 0), help="Path to where you want to save the file/folder to.")

        keyer = subparsers.add_parser("key", help="Set a new encryption key for your files.")
        keyer.add_argument("-k", "--custom-key", help="Specify a custom encryption key instead of generating one.", action="store_true")
        keyer.add_argument("-s", "--hide-key", help="Don't show the keys on the command line.", action="store_false", dest="show_key")

        args = parser.parse_args()

        self.config = Config()

        if args.operation == "upload":
            self.upload(args.path)
        elif args.operation == "download":
            self.download(args.path)
        elif args.operation == "key":
            self.key(args.custom_key, args.show_key)
        else:
            parser.print_help()

    @staticmethod
    def ask_permission(self, prompt="Are you sure?", default=False):
        while True:
            response = input(prompt + (" (Y/n): " if default else " (y/N): ")).lower()
            if response == "y" or response == "yes":
                return True
            elif response == "n" or response == "no":
                return False
            elif response == "":
                return default

    @staticmethod
    def prompt_for_key(self):
        while True:
            ekey = getpass.getpass("Enter new encryption key: ")
            if getpass.getpass("Reenter new encryption key: ") == ekey:
                if len(ekey) != 32:
                    print("This key isn't exactly 32 characters, hashing using SHA-256 to generate the final key.")
                    return hashlib.sha256(ekey).digest()
                return ekey
            else:
                print("Keys don't match.")

    def key(self, custom_key, show_key):
        if "newkey" in self.config:
            print("Continuing to re-encrypt files...")
        else:
            if not self.ask_permission("Are you sure you want to re-encrypt all of your files? This might take a long time!"):
                print("Aborting.")
                return
            if custom_key:
                self.config.newkey = self.prompt_for_key()
            else:
                self.config.newkey = os.urandom(32)
                if show_key:
                    print("Old key (hex-encoded): {}".format(self.config.encode_key(self.config.key)))
                    print("New key (hex-encoded): {}".format(self.config.encode_key(self.config.newkey)))
            self.config.save()
        try:
            with ProgressBar(widgets=["Encrypting ", Bar(), " [", ETA(), "]"], maxval=100) as bar:
                for i in range(101):
                    bar.update(i)
                    time.sleep(0.005)
        except KeyboardInterrupt:
            print("WARNING: ParanoidDrive hasn't finished re-encrypting your files!", file=sys.stderr)
            return
        self.config.key = self.config.newkey
        del self.config.newkey
        self.config.save()


if __name__ == "__main__":
    try:
        ParanoidDrive()
    except KeyboardInterrupt:
        pass
