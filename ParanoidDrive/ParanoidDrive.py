import progressbar
import argparse
import base64
import time
import json
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="Upload and download encrypted files to OneDrive.")
    subparsers = parser.add_subparsers(dest="operation")
    
    uploader = subparsers.add_parser("upload", help="Upload a file/folder to OneDrive.")
    uploader.add_argument('path', type=argparse.FileType('rb', 0), help="Path to the file/folder you want to upload.", default=".")
    
    downloader = subparsers.add_parser("download", help="Download a file/folder from OneDrive.")
    downloader.add_argument('path', type=argparse.FileType('wb', 0), help="Path to where you want to save the file/folder to.")
    
    keyer = subparsers.add_parser("key", help="Set a new encryption key for your files.")
    keyer.add_argument("-c", "--custom-key", help="Specify a custom encryption key instead of generating one.", action="store_true")
    keyer.add_argument("-s", "--hide-key", help="Don't show the keys on the command line.", action="store_false", dest="show_key")
    
    args = parser.parse_args()
    if args.operation == "upload":
        upload(args.path)
    elif args.operation == "download":
        download(args.path)
    elif args.operation == "key":
        key(args.custom_key, args.show_key)
    else:
        parser.print_help()

def ask_permission(prompt="Are you sure?", default=False):
    while True:
        response = input(prompt + (" (Y/n): " if default else " (y/N): ")).lower()
        if response == "y" or response == "yes":
            return True
        elif response == "n" or response == "no":
            return False
        elif response == "":
            return default

def get_config():
    
        

def prompt_for_key():
    while True:
        ekey = getpass.getpass("Enter new encryption key: ")
        if getpass.getpass("Reenter new encryption key: ") == ekey:
            return ekey
        else:
            print("Keys don't match.")

def key(custom_key, show_key):
    if not ask_permission("Are you sure you want to re-encrypt all of your files? This will take a long time!"):
        print("Aborting.")
        return
    newkey = ""
    if custom_key:
        newkey = get_custom_key()
    else:
        newkey = os.urandom(32)
        if show_key:
            print("New key (hex-encoded): {}".format(base64.b16encode(newkey).decode("utf-8").lower()))
    try:
        with progressbar.ProgressBar(widgets=["Encrypting ",progressbar.Bar()," [",progressbar.ETA(),"]"]) as bar:
            for i in range(999):
                bar.update(i)
                time.sleep(0.05)
    except ValueError:
        #weird progressbar bug
        pass
    except KeyboardInterrupt:
        print("WARNING: ParanoidDrive hasn't finished re-encrypting your files!", file=sys.stderr)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
