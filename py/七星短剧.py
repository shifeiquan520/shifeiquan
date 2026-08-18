# coding = utf-8
# !/usr/bin/python

"""
七星短剧 TVBox/影视仓/OK影视 源
API: https://app.whjzjx.cn
Auth: https://u.shytkjgs.com
"""

from Crypto.Util.Padding import unpad
from Crypto.Util.Padding import pad
from urllib.parse import unquote
from Crypto.Cipher import ARC4
from urllib.parse import quote
from base.spider import Spider
from Crypto.Cipher import AES
from bs4 import BeautifulSoup
from base64 import b64decode
import urllib.request
import urllib.parse
import binascii
import requests
import base64
import json
import time
import sys
import re
import os

sys.path.append('..')

# 可通过 extend 热更新的配置
DEFAULT_CFG = {
    "host": "https://app.whjzjx.cn",
    "auth_host": "https://u.shytkjgs.com",
    "auth_key": "B@ecf920Od8A4df7",
    "device_id": "2a50580e69d38388c94c93605241fb306",
    "android_id": "ec1280db12795506",
    "package_name": "com.jz.xydj",
    "first_install_time": 1752505243345,
    "last_update_time": 1752505243345,
    "version_name": "3.8.3.1",
    "remote_config_url": "https://fs-im-kefu.7moor-fs1.com/ly/4d2c3f00-7d4c-11e5-af15-41bf63ae4ea0/1732707176882/jiduo.txt",
    "timeout": 10,
}

xurl = DEFAULT_CFG["host"]

headers = {
    'User-Agent': 'Linux; Android 12; Pixel 3 XL) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.101 Mobile Safari/537.36'
}

headerf = {
    "platform": "1",
    "user_agent": "Mozilla/5.0 (Linux; Android 9; V1938T Build/PQ3A.190705.08211809; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Safari/537.36",
    "content-type": "application/json; charset=utf-8"
}


class Spider(Spider):
    def __init__(self):
        super().__init__()
        self.cfg = dict(DEFAULT_CFG)
        self._token = None
        self._token_expire = 0
        self._headerx = None
        self._jumps_cache = None
        self._jumps_expire = 0

    def init(self, extend):
        if isinstance(extend, dict):
            self.cfg.update(extend)

    def getName(self):
        return "七星短剧"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    # ---------- 认证 token 懒加载 + 缓存 ----------
    def _get_headerx(self):
        now = int(time.time() * 1000)
        if self._headerx and now < self._token_expire:
            return self._headerx

        try:
            times = int(time.time() * 1000)
            data = {
                "device": self.cfg.get("device_id"),
                "package_name": self.cfg.get("package_name"),
                "android_id": self.cfg.get("android_id"),
                "install_first_open": True,
                "first_install_time": self.cfg.get("first_install_time"),
                "last_update_time": self.cfg.get("last_update_time"),
                "report_link_url": "",
                "authorization": "",
                "timestamp": times
            }
            plain_text = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
            key = self.cfg.get("auth_key")
            key_bytes = key.encode('utf-8')
            plain_bytes = plain_text.encode('utf-8')
            cipher = AES.new(key_bytes, AES.MODE_ECB)
            padded_data = pad(plain_bytes, AES.block_size)
            ciphertext = cipher.encrypt(padded_data)
            encrypted = base64.b64encode(ciphertext).decode('utf-8')

            resp = requests.post(
                f"{self.cfg.get('auth_host')}/user/v3/account/login",
                headers=headerf,
                data=encrypted,
                timeout=self.cfg.get("timeout", 10),
                verify=False
            )
            resp.raise_for_status()
            token = resp.json().get('data', {}).get('token', '')
            if token:
                self._token = token
                # JWT 通常 24h 过期，这里设 20h 刷新
                self._token_expire = int(time.time() * 1000) + 20 * 3600 * 1000
                self._headerx = {
                    'authorization': token,
                    'platform': '1',
                    'version_name': self.cfg.get("version_name")
                }
        except Exception as e:
            print("七星短剧获取 token 失败:", e)
        return self._headerx

    # ---------- 远程跳转配置（带缓存 + 兜底） ----------
    def _get_jumps(self):
        now = time.time()
        if self._jumps_cache and now < self._jumps_expire:
            return self._jumps_cache

        try:
            resp = requests.get(
                self.cfg.get("remote_config_url"),
                timeout=self.cfg.get("timeout", 10),
                verify=False
            )
            if resp.status_code == 200:
                code = resp.text
                s1 = self.extract_middle_text(code, "s1='", "'", 0)
                s2 = self.extract_middle_text(code, "s2='", "'", 0)
                self._jumps_cache = (s1, s2)
                self._jumps_expire = now + 3600  # 1h 缓存
                return self._jumps_cache
        except Exception as e:
            print("七星短剧获取远程配置失败:", e)
        return ("", "")

    # ---------- 通用请求封装 ----------
    def _api_get(self, path, params=None):
        hx = self._get_headerx()
        if not hx:
            return None
        url = f"{self.cfg['host']}{path}"
        try:
            r = requests.get(url, headers=hx, params=params, timeout=self.cfg.get("timeout", 10), verify=False)
            if r.status_code == 401:
                # token 失效，清空重试一次
                self._token = None
                self._token_expire = 0
                self._headerx = None
                hx = self._get_headerx()
                if hx:
                    r = requests.get(url, headers=hx, params=params, timeout=self.cfg.get("timeout", 10), verify=False)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print("七星短剧请求失败:", e)
        return None

    def _api_post(self, path, json_data):
        hx = self._get_headerx()
        if not hx:
            return None
        url = f"{self.cfg['host']}{path}"
        try:
            r = requests.post(url, headers=hx, json=json_data, timeout=self.cfg.get("timeout", 10), verify=False)
            if r.status_code == 401:
                self._token = None
                self._token_expire = 0
                self._headerx = None
                hx = self._get_headerx()
                if hx:
                    r = requests.post(url, headers=hx, json=json_data, timeout=self.cfg.get("timeout", 10), verify=False)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print("七星短剧请求失败:", e)
        return None

    # ---------- 原有解析工具 ----------
    def extract_middle_text(self, text, start_str, end_str, pl, start_index1: str = '', end_index2: str = ''):
        if pl == 3:
            plx = []
            while True:
                start_index = text.find(start_str)
                if start_index == -1:
                    break
                end_index = text.find(end_str, start_index + len(start_str))
                if end_index == -1:
                    break
                middle_text = text[start_index + len(start_str):end_index]
                plx.append(middle_text)
                text = text.replace(start_str + middle_text + end_str, '')
            if len(plx) > 0:
                purl = ''
                for i in range(len(plx)):
                    matches = re.findall(start_index1, plx[i])
                    output = ""
                    for match in matches:
                        match3 = re.search(r'(?:^|[^0-9])(\d+)(?:[^0-9]|$)', match[1])
                        if match3:
                            number = match3.group(1)
                        else:
                            number = 0
                        if 'http' not in match[0]:
                            output += f"#{match[1]}${number}{xurl}{match[0]}"
                        else:
                            output += f"#{match[1]}${number}{match[0]}"
                    output = output[1:]
                    purl = purl + output + "$$$"
                purl = purl[:-3]
                return purl
            else:
                return ""
        else:
            start_index = text.find(start_str)
            if start_index == -1:
                return ""
            end_index = text.find(end_str, start_index + len(start_str))
            if end_index == -1:
                return ""

        if pl == 0:
            middle_text = text[start_index + len(start_str):end_index]
            return middle_text.replace("\\", "")

        if pl == 1:
            middle_text = text[start_index + len(start_str):end_index]
            matches = re.findall(start_index1, middle_text)
            if matches:
                jg = ' '.join(matches)
                return jg

        if pl == 2:
            middle_text = text[start_index + len(start_str):end_index]
            matches = re.findall(start_index1, middle_text)
            if matches:
                new_list = [f'{item}' for item in matches]
                jg = '$$$'.join(new_list)
                return jg
        return ""

    # ---------- 首页 ----------
    def homeContent(self, filter):
        classes = [
            {"type_id": "1", "type_name": "七星剧场"},
            {"type_id": "3", "type_name": "七星新剧"},
            {"type_id": "2", "type_name": "七星热播"},
            {"type_id": "7", "type_name": "七星星选"},
            {"type_id": "5", "type_name": "七星阳光"},
        ]
        result = {"class": classes, "list": self.homeVideoContent().get("list", [])}
        if filter:
            result["filters"] = {}
        return result

    def homeVideoContent(self):
        videos = []
        data = self._api_get("/v1/theater/home_page", {"theater_class_id": "1", "class2_id": "4", "page_num": "1", "page_size": "24"})
        if data and data.get("code") == "ok":
            for vod in data.get('data', {}).get('list', []):
                theater = vod.get('theater', {})
                videos.append({
                    "vod_id": theater.get('id', ''),
                    "vod_name": theater.get('title', ''),
                    "vod_pic": theater.get('cover_url', ''),
                    "vod_remarks": theater.get('play_amount_str', '')
                })
        return {'list': videos}

    # ---------- 分类 ----------
    def categoryContent(self, cid, pg, filter, ext):
        pg = int(pg or 1)
        videos = []
        data = self._api_get("/v1/theater/home_page", {"theater_class_id": str(cid), "page_num": str(pg), "page_size": "24"})
        if data and data.get("code") == "ok":
            for vod in data.get('data', {}).get('list', []):
                theater = vod.get('theater', {})
                videos.append({
                    "vod_id": theater.get('id', ''),
                    "vod_name": theater.get('title', ''),
                    "vod_pic": theater.get('cover_url', ''),
                    "vod_remarks": theater.get('theme', '')
                })
        result = {'list': videos, 'page': pg, 'pagecount': 9999, 'limit': 24, 'total': 999999}
        return result

    # ---------- 详情 ----------
    def detailContent(self, ids):
        did = ids[0] if isinstance(ids, list) else ids
        data = self._api_get(f"/v2/theater_parent/detail", {"theater_parent_id": str(did)})
        if not data or data.get("code") != "ok":
            return {"list": []}

        detail = data.get('data', {})
        theaters = detail.get('theaters', [])
        accessible_count = int(detail.get('accessible_episode_cnt', 0))
        total = int(detail.get('episode_cnt', len(theaters)))

        # 远程跳转配置（兜底）
        s1, s2 = self._get_jumps()

        content = '剧情：' + detail.get('introduction', '')
        area = detail.get('desc_tags', [''])[0] if detail.get('desc_tags') else ''
        remarks = detail.get('filing', '') or f"可播{accessible_count}集/全{total}集"

        xianlu = ''
        bofang = ''

        if theaters:
            playable = theaters[:accessible_count] if accessible_count > 0 else theaters
            for sou in playable:
                eid = sou.get('son_video_url', '')
                name = sou.get('num', '')
                if eid and name:
                    bofang += f"{name}${eid}#"
            bofang = bofang.rstrip('#')
            xianlu = '七星'
        else:
            # 单集兜底
            if detail.get('video_url'):
                bofang = f"1${detail['video_url']}"
                xianlu = '七星'
            else:
                bofang = s2
                xianlu = s1 or '1'

        vod = {
            "vod_id": did,
            "vod_name": detail.get('series_name', ''),
            "vod_pic": detail.get('series_cover', ''),
            "vod_content": '剧情：' + detail.get('introduction', ''),
            "vod_remarks": remarks,
            "vod_area": area,
            "vod_actor": " / ".join([c.get('nickname', '') + (" " + c.get('sub_title', '') if c.get('sub_title') else '') for c in detail.get('celebrities', [])]),
            "vod_director": "",
            "vod_play_from": xianlu,
            "vod_play_url": bofang
        }
        return {"list": [vod]}

    # ---------- 播放 ----------
    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0,
            "playUrl": "",
            "url": id,
            "header": headers
        }

    # ---------- 搜索 ----------
    def searchContentPage(self, key, quick, page):
        videos = []
        payload = {"text": key}
        data = self._api_post("/v3/search", payload)
        if data and data.get("code") == "ok":
            for vod in data.get('data', {}).get('theater', {}).get('search_data', []):
                videos.append({
                    "vod_id": vod.get('id', ''),
                    "vod_name": vod.get('title', ''),
                    "vod_pic": vod.get('cover_url', ''),
                    "vod_remarks": vod.get('score_str', '')
                })
        return {'list': videos, 'page': int(page), 'pagecount': 9999, 'limit': 24, 'total': 999999}

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    # ---------- 代理（保留原接口） ----------
    def localProxy(self, params):
        if params.get('type') == "m3u8":
            return self.proxyM3u8(params)
        elif params.get('type') == "media":
            return self.proxyMedia(params)
        elif params.get('type') == "ts":
            return self.proxyTs(params)
        return None