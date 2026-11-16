# -*- coding: utf-8 -*-
"""
斗鱼直播 - 影视仓插件
支持：分类浏览、直播间列表、播放地址获取
"""

import json
import re
import time
import requests
from urllib.parse import urlencode

try:
    from base.spider import Spider
except ImportError:
    class Spider:
        pass

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.douyu.com/",
    "Origin": "https://www.douyu.com"
}

# 分类映射：显示名称 -> API 参数
CATEGORIES = {
    "热门推荐": "0_0",
    "英雄联盟": "1_1",
    "王者荣耀": "2_2",
    "和平精英": "3_3",
    "穿越火线": "4_4",
    "DNF": "5_5",
    "主机游戏": "6_6",
    "娱乐天地": "7_7",
    "颜值": "8_8",
    "户外": "9_9",
    "手游休闲": "10_10",
    "网络游戏": "11_11",
    "单机游戏": "12_12",
    "电竞赛事": "13_13",
    "体育": "14_14",
    "教育": "15_15",
    "其它": "16_16"
}

# 缓存
CACHE = {}
CACHE_TTL = 300


class Spider(Spider):
    def getName(self):
        return "斗鱼直播"

    def init(self, extend=""):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.verify = False

    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass

    def _cache_get(self, key):
        if key in CACHE:
            ts, val = CACHE[key]
            if time.time() - ts < CACHE_TTL:
                return val
            del CACHE[key]
        return None

    def _cache_set(self, key, val):
        CACHE[key] = (time.time(), val)

    def _fetch_json(self, url, params=None):
        try:
            r = self.session.get(url, params=params, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def homeContent(self, filter):
        result = {
            "class": [{"type_id": k, "type_name": k} for k in CATEGORIES.keys()],
            "list": self._get_live_list("0_0", 1)
        }
        if filter:
            result["filters"] = self._build_filters()
        return result

    def homeVideoContent(self):
        return {"list": self._get_live_list("0_0", 1)}

    def _build_filters(self):
        filters = {}
        for cat_name in CATEGORIES.keys():
            filters[cat_name] = [{"key": "class", "name": "分类", "value": [{"n": "全部", "v": ""}]}]
        return filters

    def categoryContent(self, tid, pg, filter, extend):
        cat_key = CATEGORIES.get(tid, "0_0")
        page = int(pg) if str(pg).isdigit() else 1
        return {
            "list": self._get_live_list(cat_key, page),
            "page": page,
            "pagecount": 99,
            "limit": 20,
            "total": 9999
        }

    def _get_live_list(self, cat_key, page):
        ck = f"list_{cat_key}_{page}"
        cached = self._cache_get(ck)
        if cached:
            return cached

        url = f"https://www.douyu.com/gapi/rkc/directory/mixList/{cat_key}/{page}"
        data = self._fetch_json(url)
        items = []
        if data and data.get("code") == 0:
            for room in data.get("data", {}).get("rl", []):
                items.append({
                    "vod_id": str(room.get("rid", "")),
                    "vod_name": room.get("rn", "未知标题"),
                    "vod_pic": room.get("rs16", "") or room.get("rs1", ""),
                    "vod_remarks": f"{room.get('nn', '未知主播')} | {room.get('ol', 0)}热度"
                })
        self._cache_set(ck, items)
        return items

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if str(pg).isdigit() else 1
        url = "https://www.douyu.com/japi/search/api/search"
        params = {"kw": key, "page": page, "pageSize": 20}
        data = self._fetch_json(url, params)
        items = []
        if data and data.get("code") == 0:
            for room in data.get("data", {}).get("roomList", []):
                items.append({
                    "vod_id": str(room.get("rid", "")),
                    "vod_name": room.get("rn", "未知标题"),
                    "vod_pic": room.get("rs16", "") or room.get("rs1", ""),
                    "vod_remarks": f"{room.get('nn', '未知主播')} | {room.get('ol', 0)}热度"
                })
        return {"list": items, "page": page}

    def detailContent(self, ids):
        rid = ids[0] if isinstance(ids, list) else ids
        url = f"https://www.douyu.com/lapi/live/getH5Play/{rid}"
        data = self._fetch_json(url)
        play_url = ""
        if data and data.get("code") == 0:
            rtmp = data.get("data", {}).get("rtmp_url", "")
            rtmp_live = data.get("data", {}).get("rtmp_live", "")
            play_url = rtmp + rtmp_live if rtmp and rtmp_live else rtmp_live or rtmp

        if not play_url:
            url2 = f"https://www.douyu.com/betard/{rid}"
            data2 = self._fetch_json(url2)
            if data2 and data2.get("code") == 0:
                play_url = data2.get("data", {}).get("room", {}).get("hls_url", "")

        return {
            "list": [{
                "vod_id": str(rid),
                "vod_name": f"斗鱼直播间_{rid}",
                "vod_pic": "",
                "vod_play_from": "斗鱼直播",
                "vod_play_url": f"直播${play_url}" if play_url else ""
            }]
        }

    def playerContent(self, flag, pid, vipFlags):
        url = str(pid or "").strip()
        if not url:
            return {"parse": 0, "playUrl": "", "url": "", "header": HEADERS}
        header = dict(HEADERS)
        header["Referer"] = "https://www.douyu.com/"
        return {"parse": 0, "playUrl": "", "url": url, "header": header}

    def isVideoFormat(self, url):
        return True

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None
