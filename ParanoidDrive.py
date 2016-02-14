from gevent.monkey import patch_all
patch_all()
import cStringIO as StringIO
from gevent.pool import Pool
import hashlib
import base64
import string
import time
import zlib
import bz2
import sys
import os

try:
    from scandir import walk
except ImportError:
    from os import walk

from Crypto.Cipher import AES
from ctypes import windll
import requests

import ParanoidOneDrive

with open("ascii_logo.txt", "r") as logotxt:
    print logotxt.read()


def get_drives():
    drives = []
    bitmask = windll.kernel32.GetLogicalDrives()
    for letter in string.uppercase:
        if bitmask & 1:
            drives.append(letter)
        bitmask >>= 1
    return drives


def find_key():
    for drive in get_drives():
        if os.path.isfile(drive + ":\\.paranoid"):
            return drive + ":\\.paranoid"
    return None


def read_key():
    keypath = find_key()
    if keypath is None:
        print "Couldn't find key file. Are you trying to h4x us?"
        sys.exit()
    with open(keypath, "r") as keyfile:
        return hashlib.sha1(keyfile.read()).hexdigest()[:32]

secret = read_key()

print "Got cipher key."

iv = os.urandom(16)
cipher = AES.new(secret, AES.MODE_CFB, iv)


def get_remote_hash(key, link):
    riv = requests.get(link, headers={"Range": "bytes=0-15"}).content
    end = int(requests.head(link).headers["Content-Length"])
    fhash = requests.get(link, headers={"Range": "bytes=" + str(end - 128) + "-" + str(end)}).content
    c = AES.new(key, AES.MODE_CFB, riv)
    return c.decrypt(fhash)


def get_local_hash(path):
    with open(path, "rb") as infile:
        hasher = hashlib.sha512()
        while True:
            buf = infile.read(1024)
            if not buf:
                break
            hasher.update(buf)
        return hasher.hexdigest()[:128]


def encrypt_generator(key, inpath):
    with open(inpath, "rb") as infile:
        compressor = bz2.BZ2Compressor()
        hasher = hashlib.sha512()
        iv = os.urandom(16)
        c = AES.new(key, AES.MODE_CFB, iv)
        yield iv
        while True:
            buf = infile.read(1024)
            if not buf:
                break
            hasher.update(buf)
            data = compressor.compress(c.encrypt(buf))
            if data:
                yield data
        data = compressor.flush()
        if data:
            yield data
        c = AES.new(key, AES.MODE_CFB, iv)
        yield c.encrypt(hasher.hexdigest()[:128])


def encrypt_file(key, inpath, outpath):
    with open(inpath, "rb") as infile, open(outpath, "wb") as outfile:
        gen = encrypt_generator(key, inpath)
        for block in gen:
            outfile.write(block)


def get_file_text(filename):
    with open(filename, "r") as infile:
        return infile.read()


def crc(filename):
    with open(filename, "r") as infile:
        prev = 0
        while True:
            buf = infile.read(8192)
            if not buf:
                break
            prev = zlib.crc32(buf, prev)
        return prev


def get_immediate_subdirectories(a_dir):
        return [name for name in os.listdir(a_dir)
                if os.path.isdir(os.path.join(a_dir, name))]


def create_manifests(dir):
    delete_manifests(path)
    for dirpath, _, filenames in walk(dir, topdown=False):
        total = 0
        for filepath in filenames:
            ccrc = crc(os.path.join(dirpath, filepath))
            if ccrc < 0:
                ccrc = -ccrc * 2
            total += ccrc
        dirfs = [hex(total)[2:]]
        for dirp in get_immediate_subdirectories(dirpath):
            pmpath = os.path.join(dirp, "paranoid.manifest")
            print pmpath
            pmpath = os.path.join(dir, pmpath)
            if os.path.isfile(pmpath):
                with open(pmpath, "r") as pman:
                    dirfs.append(pman.read())
        with open(os.path.join(dirpath, "paranoid.manifest"), "w") as pman:
            for item in dirfs:
                pman.write(item)
                

def delete_manifests(dir):
    for dirpath, _, filenames in walk(dir):
        for filepath in filenames:
            if filepath == "paranoid.manifest":
                os.remove(os.path.join(dirpath, filepath))


def decrypt_string(key, instring):
        infile = StringIO.StringIO(instring)
        outfile = []
        compressor = bz2.BZ2Decompressor()
        hasher = hashlib.sha512()
        iv = infile.read(16)
        c = AES.new(key, AES.MODE_CFB, iv)
        while True:
            buf = infile.read(1024)
            if not buf:
                break
            decrypted = c.decrypt(compressor.decompress(buf))
            hasher.update(decrypted)
            outfile.append(decrypted)
        c = AES.new(key, AES.MODE_CFB, iv)
        infile.seek(-128, 2)
        filehash = c.decrypt(infile.read(128))
        if hasher.hexdigest()[:128] != filehash:
            print "WARNING: Hashes don't match for decrypted string."
        return "".join(outfile)


def decrypt_file(key, inpath, outpath):
    with open(inpath, "rb") as infile, open(outpath, "wb") as outfile:
        compressor = bz2.BZ2Decompressor()
        hasher = hashlib.sha512()
        iv = infile.read(16)
        c = AES.new(key, AES.MODE_CFB, iv)
        while True:
            buf = infile.read(1024)
            if not buf:
                break
            decrypted = c.decrypt(compressor.decompress(buf))
            hasher.update(decrypted)
            outfile.write(decrypted)
        c = AES.new(key, AES.MODE_CFB, iv)
        infile.seek(-128, 2)
        filehash = c.decrypt(infile.read(128))
        if hasher.hexdigest()[:128] != filehash:
            print "WARNING: Hashes don't match for file " + outpath


path = "X:\\"

if path.endswith("\\"):
    path = path[:-1]

print "Authenticating on OneDrive..."
od = ParanoidOneDrive.OneDrive(True)
print "Listing remote files..."
onedrive_files = od.recursive_ls()
onedrive_paths = [file.path.replace(".nsa", "") for file in onedrive_files]
print "Got all paths and metadata from OneDrive."
print "Creating manifests..."
create_manifests(path)
print "Diffing against local files..."
local_only = []
remote_only = onedrive_paths
remote_and_local = []

for dirpath, _, filenames in walk(path):
    for filepath in filenames:
        fpath = os.path.join(dirpath, filepath)[len(path) + 1:].replace("\\", "/")
        if fpath not in onedrive_paths:
            local_only.append(fpath)
        else:
            remote_only.remove(fpath)
            remote_and_local.append(fpath)

print "Deleting remote-only files..."

delete_requests = []
for fpath in remote_only:
    print fpath
    for file in onedrive_files:
        print file.path
        if file.path == fpath:
            delete_requests.append(od.delete_item_async(file))
od.run_requests(delete_requests)


def upload(file):
    print file
    if os.path.getsize(os.path.join(path, file)) < 40 * 1024 * 1024:  # 40 MB
        print "File size is below 40 MB, uploading via simple transfer."
        od.simple_upload(file + ".nsa", encrypt_generator(secret, os.path.join(path, file)))
    else:
        print "NotImplementedException on " + file

upload_local = Pool(15)
jawbs = []
print "Uploading local-only files..."
uploads = []
for file in local_only:
    jawbs.append(upload_local.spawn(upload, file))
upload_local.join()

print "Checking for changes in files and directories that are both remote and local..."

skip_directories = []
all_directories = []
for file in onedrive_files:
    if file.name == "paranoid.manifest.nsa":
        fpdir = os.path.dirname(file.path)
        if not os.path.isfile(os.path.join(path, fpdir) + "/paranoid.manifest"):
            continue
        remote = decrypt_string(secret, requests.get(file.downloadUrl).content).encode("utf-8")
        local = get_file_text(os.path.join(path, fpdir) + "/paranoid.manifest")
        if remote == local:
            print "Skipping directory " + fpdir
            skip_directories.append(fpdir)
        else:
            print "Not skipping changed directory " + fpdir


def check_hashes(fpath, dlink, secret, path):
    local = get_local_hash(os.path.join(path, fpath))
    remote = get_remote_hash(secret, dlink)
    if local != remote:
        print "Hashes don't match for file " + fpath
        print base64.b64encode(remote)[:25] + "... --> " + base64.b64encode(local)[:25] + "..."
        return fpath
    else:
        return None

hash_greenlets = Pool()
jawbs = []
for fpath in remote_and_local:
    dlink = None
    if os.path.dirname(fpath) in skip_directories:
        continue
    print fpath
    for file in onedrive_files:
        if file.path == fpath + ".nsa":
            dlink = file.downloadUrl
            break
    if dlink is not None:
        continue
    jawbs.append(hash_greenlets.spawn(check_hashes, fpath, dlink, secret, path))
hash_greenlets.join()
print "Uploading changes..."
upload_greenlets = Pool(5)
jawbs = []
for hashz in [jawb.value for jawb in jawbs if jawb.value is not None]:
    jawbs.append(upload_greenlets.spawn(upload, hashz))
upload_greenlets.join()

print "Deleting temporary manifests..."
delete_manifests(path)
time.sleep(2.5)

print "Trimming folders..."
od.trim_folders()
