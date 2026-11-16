# -*- coding: utf-8 -*-
"""
斗鱼直播 - 影视仓插件（修正分类与播放地址获取）
支持：分类浏览、直播间列表、播放地址获取
"""

import json
import re
import time
import warnings
from urllib.parse import unquote

import requests

try:
    warnings.filterwarnings("ignore")
    requests.packages.urllib3.disable_warnings()
except Exception:
    pass

try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def getName(self): return ""
        def init(self, extend=""): pass
        def destroy(self): pass
        def homeContent(self, filter): return {"class": [], "list": []}
        def homeVideoContent(self): return {"list": []}
        def categoryContent(self, tid, pg, filter, extend): return {"list": [], "page": 1, "pagecount": 0, "limit": 20, "total": 0}
        def detailContent(self, ids): return {"list": []}
        def searchContent(self, key, quick, pg="1"): return {"list": [], "page": 1}
        def playerContent(self, flag, pid, vipFlags): return {"parse": 0, "playUrl": "", "url": "", "header": {}}
        def isVideoFormat(self, url): return False
        def manualVideoCheck(self): return False
        def localProxy(self, param): return None


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 11; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Referer": "https://m.douyu.com/",
    "Origin": "https://m.douyu.com"
}

# 斗鱼分类 - 参考斗鱼直播.json，仅保留5个主分类
CATEGORIES = {
    "手游休闲": "wzry",
    "网游竞技": "LOL",
    "单机热游": "TVgame",
    "娱乐天地": "ecy",
    "颜值": "yz",
}

CACHE = {}
CACHE_TTL = 300


class Spider(Spider):
    def getName(self):
        return "斗鱼直播"

    def init(self, extend=""):
        self.destroy()
        self.cfg = {}
        if isinstance(extend, dict):
            self.cfg.update(extend)
        elif isinstance(extend, str) and extend:
            try:
                self.cfg.update(json.loads(extend))
            except Exception:
                pass

        self.timeout = self.cfg.get("timeout", 30)
        self.max_retries = self.cfg.get("max_retries", 3)
        self.cache_ttl = self.cfg.get("cache_ttl", CACHE_TTL)

        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.verify = False

        self._categories = list(CATEGORIES.keys())

    def destroy(self):
        try:
            if self.session:
                self.session.close()
        except Exception:
            pass
        self.session = None

    def _cache_get(self, key):
        if key in CACHE:
            ts, val = CACHE[key]
            if time.time() - ts < self.cache_ttl:
                return val
            del CACHE[key]
        return None

    def _cache_set(self, key, val):
        CACHE[key] = (time.time(), val)

    def _fetch_json(self, url, params=None):
        for attempt in range(self.max_retries):
            try:
                r = self.session.get(url, params=params, timeout=self.timeout)
                r.encoding = "utf-8"
                if r.status_code == 200:
                    return r.json()
            except Exception:
                if attempt == self.max_retries - 1:
                    pass
                time.sleep(0.5 * (attempt + 1))
        return None

    def _get_play_url(self, room_id):
        """获取斗鱼真实播放地址 - 单代理版本"""

        # 单代理: https://live.ottiptv.cc/douyu/
        return "https://live.ottiptv.cc/douyu/" + str(room_id)

    def homeContent(self, filter):
        result = {
            "class": [{"type_id": k, "type_name": k} for k in self._categories],
            "list": self._get_live_list("wzry", 1)
        }
        filters = {}
        for cat_name in self._categories:
            filters[cat_name] = [{"key": "cateId", "name": "分类", "value": [{"n": "全部", "v": ""}]}]
        result["filters"] = filters
        return result

    def homeVideoContent(self):
        return {"list": self._get_live_list("wzry", 1)}

    def categoryContent(self, tid, pg, filter, extend):
        cat_name = unquote(str(tid or "")).strip()
        if not cat_name or cat_name not in self._categories:
            return {"list": [], "page": 1, "pagecount": 0, "limit": 20, "total": 0}

        cate_id = CATEGORIES.get(cat_name, "wzry")
        page = int(pg) if str(pg).isdigit() else 1
        return {
            "list": self._get_live_list(cate_id, page),
            "page": page,
            "pagecount": 99,
            "limit": 20,
            "total": 9999
        }

    def _get_live_list(self, cate_id, page):
        ck = "list_" + cate_id + "_" + str(page)
        cached = self._cache_get(ck)
        if cached:
            return cached

        # 使用移动端 API: https://m.douyu.com/api/room/list?page={page}&type={cateId}
        url = "https://m.douyu.com/api/room/list"
        params = {"page": page, "type": cate_id}
        data = self._fetch_json(url, params)
        items = []
        if data and data.get("code") == 0:
            for room in data.get("data", {}).get("list", []):
                if room.get("isLive") != 1:
                    continue
                items.append({
                    "vod_id": str(room.get("rid", "")),
                    "vod_name": room.get("roomName", "未知标题"),
                    "vod_pic": room.get("roomSrc", ""),
                    "vod_remarks": room.get("nickname", "未知主播") + " | \u270f" + str(room.get("hn", ""))
                })
        self._cache_set(ck, items)
        return items

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if str(pg).isdigit() else 1
        # 移动端搜索接口
        url = "https://m.douyu.com/api/search/liveRoom"
        params = {"sk": key, "offset": (page - 1) * 20, "limit": 20}
        data = self._fetch_json(url, params)
        items = []
        if data and data.get("code") == 0:
            for room in data.get("data", {}).get("list", []):
                if room.get("isLive") != 1:
                    continue
                items.append({
                    "vod_id": str(room.get("roomId", "")),
                    "vod_name": room.get("roomName", "未知标题"),
                    "vod_pic": room.get("roomSrc", ""),
                    "vod_remarks": room.get("nickname", "未知主播") + " | \u270f" + str(room.get("hn", ""))
                })
        return {"list": items, "page": page}

    def detailContent(self, ids):
        room_id = ids[0] if isinstance(ids, list) else ids
        # 详情页链接加前缀（参考斗鱼直播.json）
        detail_id = "http://huanqiuzhibo.cn/manifest/douyu.php?id=" + str(room_id)
        play_url = "https://live.ottiptv.cc/douyu/" + str(room_id)

        return {
            "list": [{
                "vod_id": detail_id,
                "vod_name": "斗鱼直播间_" + str(room_id),
                "vod_pic": "",
                "vod_play_from": "斗鱼直播",
                "vod_play_url": "直播$" + play_url
            }]
        }

    def playerContent(self, flag, pid, vipFlags):
        url = str(pid or "").strip()
        if not url:
            return {"parse": 0, "playUrl": "", "url": "", "header": HEADERS}
        header = dict(HEADERS)
        header["Referer"] = "https://m.douyu.com/"
        # 直播流直接播放
        return {"parse": 0, "playUrl": "", "url": url, "header": header}

    def isVideoFormat(self, url):
        return True

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None
