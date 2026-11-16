# -*- coding: utf-8 -*-
"""
虎牙直播 - 影视仓插件
支持：分类浏览、直播间列表、播放地址获取
"""

import json
import re
import time
import requests
import hashlib
import random

try:
    from base.spider import Spider
except ImportError:
    class Spider:
        pass

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.huya.com/",
    "Origin": "https://www.huya.com"
}

# 游戏分类映射：显示名称 -> gameId
CATEGORIES = {
    "热门推荐": "0",
    "英雄联盟": "1",
    "王者荣耀": "2633",
    "和平精英": "2793",
    "穿越火线": "2168",
    "DNF": "36",
    "绝地求生": "2828",
    "主机游戏": "2837",
    "娱乐天地": "1994",
    "颜值": "2130",
    "户外": "2160",
    "手游休闲": "3027",
    "网络游戏": "2020",
    "单机游戏": "2019",
    "电竞赛事": "2015",
    "体育": "2028",
    "教育": "2026",
    "其它": "2000"
}

# 缓存
CACHE = {}
CACHE_TTL = 300


class Spider(Spider):
    def getName(self):
        return "虎牙直播"

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
            "list": self._get_live_list("0", 1)
        }
        if filter:
            result["filters"] = self._build_filters()
        return result

    def homeVideoContent(self):
        return {"list": self._get_live_list("0", 1)}

    def _build_filters(self):
        filters = {}
        for cat_name in CATEGORIES.keys():
            filters[cat_name] = [{"key": "class", "name": "分类", "value": [{"n": "全部", "v": ""}]}]
        return filters

    def categoryContent(self, tid, pg, filter, extend):
        game_id = CATEGORIES.get(tid, "0")
        page = int(pg) if str(pg).isdigit() else 1
        return {
            "list": self._get_live_list(game_id, page),
            "page": page,
            "pagecount": 99,
            "limit": 20,
            "total": 9999
        }

    def _get_live_list(self, game_id, page):
        ck = f"list_{game_id}_{page}"
        cached = self._cache_get(ck)
        if cached:
            return cached

        url = "https://www.huya.com/cache.php"
        params = {
            "m": "LiveList",
            "do": "getLiveListByPage",
            "gameId": game_id,
            "page": page,
            "pageSize": 20
        }
        data = self._fetch_json(url, params)
        items = []
        if data and data.get("status") == 200:
            for room in data.get("data", {}).get("datas", []):
                items.append({
                    "vod_id": str(room.get("profileRoom", "")),
                    "vod_name": room.get("roomName", "未知标题"),
                    "vod_pic": room.get("screenshot", "") or room.get("avatar180", ""),
                    "vod_remarks": f"{room.get('nick', '未知主播')} | {room.get('totalCount', 0)}热度"
                })
        self._cache_set(ck, items)
        return items

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if str(pg).isdigit() else 1
        url = "https://search.huya.com/api/search"
        params = {"kw": key, "page": page, "pageSize": 20}
        data = self._fetch_json(url, params)
        items = []
        if data and data.get("status") == 200:
            for room in data.get("data", {}).get("list", []):
                items.append({
                    "vod_id": str(room.get("roomId", "")),
                    "vod_name": room.get("roomName", "未知标题"),
                    "vod_pic": room.get("roomPic", ""),
                    "vod_remarks": f"{room.get('nick', '未知主播')} | {room.get('totalCount', 0)}热度"
                })
        return {"list": items, "page": page}

    def _get_anti_code(self, room_id):
        """获取虎牙防盗链签名"""
        try:
            t = str(int(time.time() * 1000))
            seq = str(random.randint(100000, 999999))
            s = f"{room_id}{t}{seq}huya"
            md5 = hashlib.md5(s.encode()).hexdigest()
            return md5, t, seq
        except Exception:
            return "", "", ""

    def detailContent(self, ids):
        room_id = ids[0] if isinstance(ids, list) else ids
        # 获取播放地址
        anti_code, tt, seq = self._get_anti_code(room_id)
        url = "https://www.huya.com/liveapi/room/getLiveUrl"
        params = {
            "roomId": room_id,
            "antiCode": anti_code,
            "tt": tt,
            "seq": seq,
            "line": "hls"
        }
        data = self._fetch_json(url, params)
        play_url = ""
        if data and data.get("status") == 200:
            stream = data.get("data", {}).get("stream", {})
            # 优先 HLS (m3u8)
            if "hls" in stream and stream["hls"]:
                play_url = stream["hls"][0].get("url", "")
            # 备用 FLV
            elif "flv" in stream and stream["flv"]:
                play_url = stream["flv"][0].get("url", "")

        return {
            "list": [{
                "vod_id": str(room_id),
                "vod_name": f"虎牙直播间_{room_id}",
                "vod_pic": "",
                "vod_play_from": "虎牙直播",
                "vod_play_url": f"直播${play_url}" if play_url else ""
            }]
        }

    def playerContent(self, flag, pid, vipFlags):
        url = str(pid or "").strip()
        if not url:
            return {"parse": 0, "playUrl": "", "url": "", "header": HEADERS}
        header = dict(HEADERS)
        header["Referer"] = "https://www.huya.com/"
        return {"parse": 0, "playUrl": "", "url": url, "header": header}

    def isVideoFormat(self, url):
        return True

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None
