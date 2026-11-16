# -*- coding: utf-8 -*-
"""
虎牙直播 - 影视仓插件（严格对齐 JS 版签名算法）
支持：分类浏览、直播间列表、播放地址获取
"""

import json
import re
import time
import warnings
import hashlib
import base64
from urllib.parse import unquote, urlparse

import requests

try:
    warnings.filterwarnings('ignore')
    requests.packages.urllib3.disable_warnings()
except Exception:
    pass

try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def getName(self): return ''
        def init(self, extend=''): pass
        def destroy(self): pass
        def homeContent(self, filter): return {'class': [], 'list': []}
        def homeVideoContent(self): return {'list': []}
        def categoryContent(self, tid, pg, filter, extend): return {'list': [], 'page': 1, 'pagecount': 0, 'limit': 20, 'total': 0}
        def detailContent(self, ids): return {'list': []}
        def searchContent(self, key, quick, pg='1'): return {'list': [], 'page': 1}
        def playerContent(self, flag, pid, vipFlags): return {'parse': 0, 'playUrl': '', 'url': '', 'header': {}}
        def isVideoFormat(self, url): return False
        def manualVideoCheck(self): return False
        def localProxy(self, param): return None


MOBILE_UA = "Mozilla/5.0 (Linux; Android 11; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"

HEADERS = {
    "User-Agent": MOBILE_UA,
    "Referer": "https://m.huya.com/",
    "Origin": "https://m.huya.com"
}

CATEGORIES = {
    "热门推荐": "2168",
    "王者荣耀": "2336",    
    "娱乐天地": "100022", 
    "户外": "2165",
    "一起看": "2135", 
    "英雄联盟": "1",
    "和平精英": "3203", 
    "主机游戏": "100032",
    "我的世界": "1732",
    "单机热游": "100002",
    "手游休闲": "100004",
}

CACHE = {}
CACHE_TTL = 300


class Spider(Spider):
    def getName(self):
        return "虎牙直播"

    def init(self, extend=''):
        self.destroy()
        self.cfg = {}
        if isinstance(extend, dict):
            self.cfg.update(extend)
        elif isinstance(extend, str) and extend:
            try:
                self.cfg.update(json.loads(extend))
            except Exception:
                pass

        self.timeout = self.cfg.get('timeout', 30)
        self.max_retries = self.cfg.get('max_retries', 3)
        self.cache_ttl = self.cfg.get('cache_ttl', CACHE_TTL)

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
                r.encoding = 'utf-8'
                if r.status_code == 200:
                    return r.json()
            except Exception:
                if attempt == self.max_retries - 1:
                    pass
                time.sleep(0.5 * (attempt + 1))
        return None

    # ===== 核心签名算法：严格移植 JS 版 getRealUrl =====
    def _get_real_flv_url(self, live_url):
        """
        JS 逻辑：
        1. let [i, b] = live_url.split('?');
        2. let r = i.split('/').pop();
        3. let s = r.replace(/\.(flv|m3u8)/, '');
        4. let c_tmp = b.split('&').filter(n => n);
        5. 前3个参数进 n 对象，其余进 c_tmp2 数组
        6. c_tmp2 最后一个也合并进 n
        7. fm = decodeURIComponent(n.fm).split('&')[0];
        8. u = base64Decode(fm); p = u.split('_')[0];
        9. f = timestamp+'0000'; ll = n.wsTime; t = '0';
        10. h = [p, t, s, f, ll].join('_'); m = md5(h);
        11. 返回 i + '?wsSecret=' + m + '&wsTime=' + ll + '&u=' + t + '&seqid=' + f + '&' + c_tmp2.pop()
        12. 替换 hls/m3u8 -> flv
        """
        try:
            # 1. 分离 base_url 和 query
            if '?' not in live_url:
                return live_url.replace('hls', 'flv').replace('m3u8', 'flv')
            
            i, b = live_url.split('?', 1)
            
            # 2. 提取 s (文件名去后缀)
            r = i.split('/')[-1]
            s = r
            if s.endswith('.flv'):
                s = s[:-4]
            elif s.endswith('.m3u8'):
                s = s[:-5]
            
            # 3. 解析 query 参数，按顺序处理
            c_tmp = [x for x in b.split('&') if x]
            n = {}
            c_tmp2 = []
            
            for idx, tmp in enumerate(c_tmp):
                if '=' in tmp:
                    k, v = tmp.split('=', 1)
                    if idx < 3:
                        n[k] = v
                    else:
                        c_tmp2.append(tmp)
            
            # 4. c_tmp2 最后一个合并进 n
            if c_tmp2:
                last = c_tmp2[-1]
                if '=' in last:
                    k, v = last.split('=', 1)
                    n[k] = v
            
            # 5. 处理 fm 参数
            fm = n.get('fm', '')
            if not fm:
                return live_url.replace('hls', 'flv').replace('m3u8', 'flv')
            
            # decodeURIComponent -> unquote
            fm = unquote(fm)
            # split('&')[0]
            fm = fm.split('&')[0]
            
            # base64 解码
            try:
                u = base64.b64decode(fm).decode('utf-8')
            except Exception:
                return live_url.replace('hls', 'flv').replace('m3u8', 'flv')
            
            p = u.split('_')[0]
            
            # 6. 时间戳参数
            f = str(int(time.time() * 1000)) + '0000'
            ll = n.get('wsTime', '0')
            t = '0'
            
            # 7. 计算签名
            h = '_'.join([p, t, s, f, ll])
            m = hashlib.md5(h.encode()).hexdigest()
            
            # 8. 重组 URL
            # c_tmp2.pop() 取最后一个
            last_param = ''
            if c_tmp2:
                last_param = '&' + c_tmp2[-1]
            
            real_url = f"{i}?wsSecret={m}&wsTime={ll}&u={t}&seqid={f}{last_param}"
            
            # 9. 强制 flv
            return real_url.replace('hls', 'flv').replace('m3u8', 'flv')
            
        except Exception:
            return live_url.replace('hls', 'flv').replace('m3u8', 'flv')

    def _get_play_url(self, room_id):
        """获取真实播放地址"""
        # 请求 profileRoom 接口
        url = f"https://mp.huya.com/cache.php?m=Live&do=profileRoom&roomid={room_id}"
        data = self._fetch_json(url)
        if not data or data.get('status') != 200:
            return ""
        
        try:
            stream = data.get('data', {}).get('stream', {})
            flv = stream.get('flv', {})
            multi = flv.get('multiLine', [])
            if not multi:
                return ""
            
            raw_url = multi[0].get('url', '')
            if not raw_url:
                return ""
            
            # 签名转换
            return self._get_real_flv_url(raw_url)
        except Exception:
            return ""

    def homeContent(self, filter):
        result = {
            "class": [{"type_id": k, "type_name": k} for k in self._categories],
            "list": self._get_live_list("2168", 1)
        }
        filters = {}
        for cat_name in self._categories:
            filters[cat_name] = [{"key": "cateId", "name": "分类", "value": [{"n": "全部", "v": ""}]}]
        result["filters"] = filters
        return result

    def homeVideoContent(self):
        return {"list": self._get_live_list("2168", 1)}

    def categoryContent(self, tid, pg, filter, extend):
        cat_name = unquote(str(tid or '')).strip()
        if not cat_name or cat_name not in self._categories:
            return {'list': [], 'page': 1, 'pagecount': 0, 'limit': 20, 'total': 0}

        cate_id = CATEGORIES.get(cat_name, "2168")
        page = int(pg) if str(pg).isdigit() else 1
        return {
            "list": self._get_live_list(cate_id, page),
            "page": page,
            "pagecount": 99,
            "limit": 20,
            "total": 9999
        }

    def _get_live_list(self, cate_id, page):
        ck = f"list_{cate_id}_{page}"
        cached = self._cache_get(ck)
        if cached:
            return cached

        url = "https://www.huya.com/cache.php"
        params = {
            "m": "LiveList",
            "do": "getLiveListByPage",
            "gameId": cate_id,
            "tagAll": "0",
            "page": page
        }
        data = self._fetch_json(url, params)
        items = []
        if data and data.get("status") == 200:
            for room in data.get("data", {}).get("datas", []):
                items.append({
                    "vod_id": str(room.get("profileRoom", "")),
                    "vod_name": room.get("introduction", "未知标题"),
                    "vod_pic": room.get("screenshot", "") or room.get("avatar180", ""),
                    "vod_remarks": f"👁{room.get('totalCount', 0)} 🆙{room.get('nick', '未知主播')}"
                })
        self._cache_set(ck, items)
        return items

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if str(pg).isdigit() else 1
        url = "https://search.cdn.huya.com/"
        params = {
            "m": "Search",
            "do": "getSearchContent",
            "q": key,
            "uid": "0",
            "v": "4",
            "typ": "-5",
            "livestate": "0",
            "rows": "20",
            "start": str((page - 1) * 20)
        }
        data = self._fetch_json(url, params)
        items = []
        if data and data.get("status") == 200:
            docs = data.get("response", [{}])[3].get("docs", []) if len(data.get("response", [])) > 3 else []
            for room in docs:
                items.append({
                    "vod_id": str(room.get("room_id", "")),
                    "vod_name": room.get("game_roomName", "未知标题"),
                    "vod_pic": room.get("game_screenshot", ""),
                    "vod_remarks": f"👁{room.get('game_totalCount', 0)} 🆙{room.get('game_nick', '未知主播')}"
                })
        return {"list": items, "page": page}

    def detailContent(self, ids):
        room_id = ids[0] if isinstance(ids, list) else ids
        play_url = self._get_play_url(room_id)

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
        header["Referer"] = "https://m.huya.com/"
        return {"parse": 0, "playUrl": "", "url": url, "header": header}

    def isVideoFormat(self, url):
        return True

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None
