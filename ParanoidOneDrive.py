import gevent
gevent.monkey.patch_all()
import webbrowser
import operator
import requests
import grequests
import urlparse
import time
import os

# chilidogs fast
try:
    import simplejson as json
except:
    import json

class DictAsClass:
    def __init__(self, infodict, level=None):
        blacklist = ["parentReference", "cTag", "createdBy", "createdDateTime", "webUrl", "fileSystemInfo", "lastModifiedBy", "eTag"]
        if level is None:
            self.level = 0
        else:
            self.level = level
        for key, value in infodict.iteritems():
            if key in blacklist:
                continue
            if key == "@content.downloadUrl":
                key = "downloadUrl"
            if isinstance(value, dict):
                self.__dict__[key] = DictAsClass(value, self.level + 1)
            else:
                self.__dict__[key] = value

    def __repr__(self):
        lines = []
        for key, item in sorted(self.__dict__.items(), key=operator.itemgetter(0)):
            if key == "level":
                continue
            istring = ""
            if key == "downloadUrl":
                istring = item[:55] + "..."
            elif type(item) == unicode:
                istring = item
            else:
                istring = repr(item)
            lines.append((" " * self.level) + key + ": " + istring)
        return "\n" + "\n".join(lines)

class OneDrive:
    def __init__(self, debug=False):
        self.expires = None
        self.access_token = None
        self.refresh_token = None
        self.dirs = {}
        self.debug = debug
        self.do_auth()

    def save_tokens(self):
        with open("onedrive_tokens.json", "w") as odtxt:
            tdict = {
                "expires": self.expires,
                "access_token": self.access_token,
                "refresh_token": self.refresh_token
                }
            odtxt.write(json.dumps(tdict, indent=4, separators=(',', ': ')))

    def load_tokens(self):
        with open("onedrive_tokens.json", "r") as odtxt:
            jason = json.load(odtxt)
            self.expires = jason["expires"]
            self.access_token = jason["access_token"]
            self.refresh_token = jason["refresh_token"]

    def get_code(self):
        webbrowser.open("https://login.live.com/oauth20_authorize.srf?client_id=0000000048169A29&scope=wl.signin,wl.offline_access,onedrive.readwrite&response_type=code&redirect_uri=https://login.live.com/oauth20_desktop.srf", new=1, autoraise=True)
        url = urlparse.urlparse(raw_input("Paste resulting URL here: "))
        query = urlparse.parse_qs(url.query)
        return query["code"][0]

    def update_auth(self, raw_json):
        jason = json.loads(raw_json)
        self.expires = int(round(time.time() + (jason[u"expires_in"] - 10))) # 10 second buffer just in case
        self.access_token = jason[u"access_token"]
        self.refresh_token = jason[u"refresh_token"]

    def get_token(self, code):
        tokendata = {
            "client_id": "0000000048169A29",
            "redirect_uri": "https://login.live.com/oauth20_desktop.srf",
            "client_secret": "whv-rCdol9o9b4F579LM0rzGDMiMpeTk",
            "code": code,
            "grant_type": "authorization_code"
            }
        r = requests.post("https://login.live.com/oauth20_token.srf", data=tokendata)
        self.update_auth(r.text)

    def refresh(self):
        tokendata = {
            "client_id": "0000000048169A29",
            "redirect_uri": "https://login.live.com/oauth20_desktop.srf",
            "client_secret": "whv-rCdol9o9b4F579LM0rzGDMiMpeTk",
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
            }
        r = requests.post("https://login.live.com/oauth20_token.srf", data=tokendata)
        self.update_auth(r.text)
        self.save_tokens()

    def do_auth(self):
        if self.expires and self.access_token and self.refresh_token:
            if not self.check_time():
                self.refresh()
        else:
            if os.path.isfile("onedrive_tokens.json"):
                self.load_tokens()
                if not self.check_time():
                    self.refresh()
            else:
                code = self.get_code()
                self.get_token(code)
                self.save_tokens()
            assert self.expires
            assert self.access_token
            assert self.refresh_token

    def check_time(self):
        return time.time() < self.expires

    def api_call(self, path, method=requests.get, payload=None, extra_headers={}, async=False):
        if self.debug:
            start = time.time()
        root = "https://api.onedrive.com/v1.0"
        headers = {"Authorization": "bearer " + self.access_token}
        if async:
            method = grequests.__dict__[method.__name__]
        if payload is None:
            r = method(root + path, headers=dict(headers, **extra_headers))
        elif type(payload) == dict:
            r = method(root + path, headers=dict(headers, **extra_headers), json=payload)
        else:
            r = method(root + path, headers=dict(headers, **extra_headers), data=payload)
        if async:
            return r
        try:
            jason = json.loads(r.text)
        except:
            return None
        if "error" in jason:
            if jason["error"]["code"] == "unauthenticated":
                self.refresh()
                pval = self.api_call(path)
                if self.debug: print "DEBUG: " + path + " took " + str(time.time() - start)
                return pval
            else:
                error = jason["error"]
                raise Exception("OneDrive API error.\nCode: " + error["code"] + "\nMessage: " + error["message"])
        else:
            if "value" in jason:
                if self.debug: print "DEBUG: " + path + " took " + str(time.time() - start)
                return jason["value"]
            else:
                if self.debug: print "DEBUG: " + path + " took " + str(time.time() - start)
                return jason

    def delete_item_async(self, item):
        return self.delete_by_id_async(item.id)

    def delete_item(self, item):
        self.delete_by_id(item.id)

    def delete_by_id(self, iid):
        self.api_call("/drive/items/" + iid, requests.delete)

    def delete_by_id_async(self, iid):
        return self.api_call("/drive/items/" + iid, requests.delete, async=True)

    def delete_by_path(self, path):
        self.api_call("/drive/root:/" + path, requests.delete)

    def delete_by_path_async(self, path):
        return self.api_call("/drive/root:/" + path, requests.delete, async=True)

    def run_requests(self, rlist, pool_size=5):
        pewl = grequests.Pool(pool_size)
        all_jobs = []
        for r in rlist:
            all_jobs.append(grequests.send(r, pewl))
        results = []
        gevent.joinall(all_jobs)
        return [job.value for job in all_jobs]

    def recursive_ls(self, iid="584799FC90D80FB7%2116612", root=[]):
        files = []
        for item in self.api_call("/drive/items/" + iid + "/children"):
            if "folder" in item:
                newroot = root + [item["name"]]
                files.extend(self.recursive_ls(item["id"], newroot))
            elif "file" in item:
                ditem = DictAsClass(item)
                ditem.path = u"/".join(root + [ditem.name])
                files.append(ditem)
        return files

    def trim_folders(self, iid="584799FC90D80FB7%2116612"):
        trim = True
        for item in self.api_call("/drive/items/" + iid + "/children"):
            # print repr(DictAsClass(item))
            if "folder" in item:
                item = DictAsClass(item)
                if not self.trim_folders(item.id):
                    trim = False
                    break
            elif "file" in item:
                item = DictAsClass(item)
                if item.name != "paranoid.manifest.nsa":
                    trim = False
                    break
        if trim and iid != "584799FC90D80FB7%2116612":
            print "Trimming empty folder " + iid
            self.delete_by_id(iid)
        return trim

    def getdirs(self, iid="584799FC90D80FB7%2116612", root=[], idroot=[]):
        if iid in self.dirs:
            if self.debug:
                print "DEBUG: Cached directory " + iid
            return self.dirs[iid]
        else:
            dirs = []
            for item in self.api_call("/drive/items/" + iid + "/children"):
                if "folder" in item:
                    newroot = root + [item["name"]]
                    newidroot = idroot + [item["id"]]
                    dirs.append((newroot, newidroot))
                    dirs.extend(self.getdirs(item["id"], newroot, newidroot))
            self.dirs[iid] = dirs
            return dirs

    def mkdir(self, root, name):
        payload = {
            "name": name,
            "folder": {}
            }
        print root + " --> " + name
        if root in self.dirs:
            del self.dirs[root]
        result = None
        try:
            result = self.api_call("/drive/items/" + root + "/children", requests.post, payload)["id"]
            self.getdirs(root)
        except:
            for item in self.api_call("/drive/items/" + root + "/children"):
                if "folder" in item:
                    item = DictAsClass(item)
                    if item.name == name:
                        result = item.id
        return result

    def mkdirs(self, path, async=False):
        pathnodes = path.split("/")
        npathnodes = path.split("/")
        iid="584799FC90D80FB7%2116612"
        allfolders = self.getdirs() + [([],[iid])]
        for folder in allfolders:
            if folder[0] == npathnodes:
                return folder[1][-1]
        leave = False
        target = None
        while True:
            tpath = "/".join(npathnodes)
            for folder in allfolders:
                if folder[0] == npathnodes:
                    target = folder
                    leave = True
                    break
            if leave:
                break
            else:
                if npathnodes != []:
                    npathnodes.pop()
                else:
                    target = ([],[iid])
                    break
        croot = target[1][-1]
        pathnodes = pathnodes[len(target[0]):]
        stahp = True
        while pathnodes != []:
            cfmpath = pathnodes.pop(0)
            if async and stahp:
                time.sleep(0.25)
                stahp = False
            croot = self.mkdir(croot, cfmpath)
        return croot

    def get_item(self, file):
        return DictAsClass(self.api_call("/drive/items/" + file.id))

    def simple_upload(self, path, generator):
        if "/" in path:
            filename = path.split("/")[-1]
            path = path[:-len(filename)]
            if path.endswith("/"):
                path = path[:-1]
            folder = self.mkdirs(path)
        else:
            folder = "584799FC90D80FB7%2116612"
            filename = path
        return self.api_call("/drive/items/" + folder + "/children/" + filename + "/content",
                             requests.put,
                             generator,
                             {"Content-Type": "application/octet-stream"})

    def simple_upload_async(self, path, generator):
        if "/" in path:
            filename = path.split("/")[-1]
            path = path[:-len(filename)]
            if path.endswith("/"):
                path = path[:-1]
            folder = self.mkdirs(path, True)
        else:
            folder = "584799FC90D80FB7%2116612"
            filename = path
        return self.api_call("/drive/items/" + folder + "/children/" + filename + "/content",
                             requests.put,
                             generator,
                             {"Content-Type": "application/octet-stream"},
                             async=True)
