# -*- coding: utf-8 -*-
import json
import urllib.request
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    def init(self, extend=""):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.host = None

    def _load_host(self):
        try:
            with open("映像星球.host", "r") as f:
                host = f.read().strip()
                if host:
                    return host
        except:
            pass
        return None

    def _save_host(self, host):
        try:
            with open("映像星球.host", "w") as f:
                f.write(host)
        except:
            pass

    def _check(self, host):
        try:
            url = f"https://{host}/api.php/provide/vod/at/json/?ac=list&t=1&pg=1&pagesize=1"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            urllib.request.urlopen(req, timeout=3)
            return True
        except:
            return False

    def _ensure_host(self):
        if self.host:
            return
        cached = self._load_host()
        if cached and self._check(cached):
            self.host = cached
            return
        if self._check("www.qkys2.cc"):
            self.host = "www.qkys2.cc"
            self._save_host("www.qkys2.cc")
            return
        for i in range(1, 101):
            host = f"www.yxxq{i}.cc"
            if self._check(host):
                self.host = host
                self._save_host(host)
                return
        for i in range(1, 101):
            host = f"www.qkys{i}.cc"
            if self._check(host):
                self.host = host
                self._save_host(host)
                return
        self.host = "www.yxxq42.cc"

    def getName(self):
        return "映像星球"

    def homeContent(self, filter):
        return {"class": [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "7", "type_name": "纪录片"},
            {"type_id": "39", "type_name": "短剧"},
            {"type_id": "53", "type_name": "体育"},
        ]}

    def _norm(self, items):
        for it in items:
            it["vod_id"] = str(it.get("vod_id", ""))
            it.setdefault("vod_pic", "")
            it.setdefault("vod_remarks", "")
            it.setdefault("vod_name", "")
        return items

    def homeVideoContent(self):
        self._ensure_host()
        html = self._get(f"https://{self.host}/api.php/provide/vod/at/json/?ac=videolist&t=1&pg=1&pagesize=36")
        data = json.loads(html)
        items = self._norm(data.get("list", []))
        return {"list": items}

    def categoryContent(self, tid, pg, filter, extend):
        self._ensure_host()
        html = self._get(f"https://{self.host}/api.php/provide/vod/at/json/?ac=videolist&t={tid}&pg={pg}&pagesize=50")
        data = json.loads(html)
        items = self._norm(data.get("list", []))
        pagecount = data.get("pagecount", 1)
        return {"list": items, "page": int(pg), "pagecount": pagecount, "limit": 50, "total": data.get("total", 0)}

    def detailContent(self, ids):
        self._ensure_host()
        vid = ids[0].split(",")[0].strip()
        html = self._get(f"https://{self.host}/api.php/provide/vod/at/json/?ac=detail&ids={vid}")
        data = json.loads(html)
        items = data.get("list", [])
        if items:
            it = items[0]
            it["vod_id"] = str(it.get("vod_id", ""))
            it.setdefault("vod_pic", "")
            it.setdefault("vod_remarks", "")
            it.setdefault("vod_name", "")
            it.setdefault("vod_play_from", "")
            it.setdefault("vod_play_url", "")
            it.setdefault("vod_content", "")
            it.setdefault("vod_actor", "")
            it.setdefault("vod_director", "")
            return {"list": [it]}
        return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        self._ensure_host()
        html = self._get(f"https://{self.host}/api.php/provide/vod/at/json/?ac=videolist&wd={key}&pg={pg}&pagesize=50")
        data = json.loads(html)
        items = self._norm(data.get("list", []))
        return {"list": items, "page": int(pg), "pagecount": 1, "limit": 50, "total": data.get("total", 0)}

    def playerContent(self, flag, id, vipFlags):
        return {"parse": 0, "url": id}

    def localProxy(self, param=""):
        return {}

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def _get(self, url):
        try:
            rsp = self.fetch(url, headers=self.headers)
            if rsp:
                return rsp.text
            return "{}"
        except:
            return "{}"
