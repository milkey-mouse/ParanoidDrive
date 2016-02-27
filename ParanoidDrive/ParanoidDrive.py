from progressbar import ProgressBar, Bar, ETA  # progressbar2
import argparse
import base64
import time
import json
import sys
import os


class Config(object):
    def __init__(self, path="~/.paranoid"):
        self.path = os.path.expanduser(path)
        self.key = None
        try:
            with open(self.path, "r") as config_file:
                self.__dict__.update(json.read(config_file))
        except FileNotFoundError:
            if path != "~/.paranoid":
                raise FileNotFoundError
            else:

                try:
                    with open(os.path.expanduser("~/.paranoid"), "r") as config_file:
                        print("WARNING: Can't find custom config file, falling back to default location.", file=sys.stderr)
                        self.__dict__.update(json.read(config_file))
                except FileNotFoundError:
                    pass
        if self.key:
            self.key = base64.b16decode(self.key)
        else:


    def save(self):
        with open(self.path) as config_file:
            json.dump({k:v for k, v in A.__dict__.items() if callable(k) and not k == "path"}, config_file)


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
                return ekey
            else:
                print("Keys don't match.")

    def key(self, custom_key, show_key):
        if not ask_permission("Are you sure you want to re-encrypt all of your files? This might take a long time!"):
            print("Aborting.")
            return
        newkey = ""
        if custom_key:
            newkey = get_custom_key()
        else:
            newkey = os.urandom(32)
            if show_key:
                print("Old key (hex-encoded): {}".format(base64.b16encode(newkey).decode("utf-8").lower()))
                print("New key (hex-encoded): {}".format(base64.b16encode(newkey).decode("utf-8").lower()))
        try:
            #with ProgressBar(widgets=["Encrypting ", Bar(), " [", ETA(), "]"], maxval=100) as bar:
            #    for i in range(101):
            #        bar.update(i)
            #        time.sleep(0.005)
            raise NotImplementedError()
        except KeyboardInterrupt:
            print("WARNING: ParanoidDrive hasn't finished re-encrypting your files!", file=sys.stderr)

if __name__ == "__main__":
    try:
        ParanoidDrive().main()
    except KeyboardInterrupt:
        pass
