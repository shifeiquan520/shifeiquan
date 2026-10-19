# coding=utf-8
# !/usr/bin/python
"""
红果短剧 TVBox / OK影视 / 影视仓 Python 源（聚合站浏览器版 2026）。

数据与播放全部来自聚合站 hongguoapp.cn（maccms / conch 模板）：
- 列表：/vodshow/51--------{page}---.html（第1页无页码）
- 字段模板：/vodshow/{tid}-{f1}-{order}-{genre}-{lang}-{letter}-{f6}-{f7}-{page}-{res}-{f10}-{year}.html
- 条目：<a href="/voddetail/{id}.html" title="{name}" data-original="{pic}"> + remarks span
- 详情：/voddetail/{id}.html -> 剧名 h2.hl-dc-title、简介 meta description、分集 /vodplay/{id}-{sid}-{n}.html
- 播放：/vodplay/{id}-{sid}-{n}.html 内 player_xxxx={...} 的 url = m3u8（多数不加密）
- 搜索：/vodsearch/-------------.html?wd=；兜底 /index.php/ajax/suggest?mid=1&wd=

说明：红果官方网页版视频是 CENC/DRM 加密（encv/tenc/senc），普通播放器无法解密，
故本源改为直接使用聚合站的可播片库。
"""

import json
import math
import re
import sys
import time
from urllib.parse import quote, urlencode

import requests

try:
    requests.packages.urllib3.disable_warnings()
except Exception:
    pass

sys.path.append("..")
sys.path.append("../../")
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        pass


HOST = "https://www.hongguoapp.cn"
TYPE_ID = "51"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

GENRES = ["古装", "战争", "青春偶像", "喜剧", "家庭", "犯罪", "动作", "奇幻",
          "剧情", "历史", "经典", "乡村", "情景", "商战", "网剧", "其他"]
YEARS = [str(y) for y in range(2026, 1999, -1)]
LANGS = ["国语", "英语"]
LETTERS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ["0-9"]
RESES = ["正片", "预告片", "花絮"]

CLASSES = [
    ("all", "全部推荐"),
    ("time", "最近更新"),
    ("hits", "最多播放"),
    ("score", "好评优先"),
]
SORTS = ("time", "hits", "score")


class Spider(Spider):
    def __init__(self):
        self.host = HOST
        self.headers = {
            "User-Agent": UA,
            "Referer": self.host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self.ajax_headers = {
            "User-Agent": UA,
            "Referer": self.host + "/",
            "X-Requested-With": "XMLHttpRequest",
        }
        self.timeout = 20
        self.page_size = 36
        self._cache = {}

    def getName(self):
        return "红果短剧"

    def init(self, extend=""):
        return

    def isVideoFormat(self, url):
        return any(str(url).lower().endswith(x) for x in (".m3u8", ".mp4", ".ts", ".flv", ".mkv"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        return

    def localProxy(self, params):
        return None

    # ---------------------------------------------------------------- 首页
    def homeContent(self, filter):
        result = {"class": [{"type_id": t, "type_name": n} for t, n in CLASSES]}
        if filter:
            result["filters"] = self._build_filters()
        result["list"] = self.homeVideoContent().get("list", [])
        return result

    def homeVideoContent(self):
        try:
            html = self._get("/")
            items = self._parse_items(html)
            return {"list": self._to_vods(items)[:self.page_size]}
        except Exception as exc:
            print("红果首页读取失败:", exc)
            return {"list": []}

    # ---------------------------------------------------------------- 分类
    def categoryContent(self, tid, pg, filter, extend):
        page_num = self._safe_int(pg, 1)
        ext = extend if isinstance(extend, dict) else {}
        order = tid if tid in SORTS else ""
        try:
            url = self._show_url(
                order,
                ext.get("genre", ""),
                ext.get("lang", ""),
                ext.get("letter", ""),
                page_num,
                ext.get("res", ""),
                ext.get("year", ""),
            )
            html = self._get(url)
            items = self._parse_items(html)
            pagecount = self._page_count(html, page_num)
            return {
                "page": page_num,
                "pagecount": pagecount,
                "limit": self.page_size,
                "total": len(items),
                "list": self._to_vods(items),
            }
        except Exception as exc:
            print("红果分类读取失败:", exc)
            return {"list": [], "page": page_num, "pagecount": page_num}

    def _show_url(self, order="", genre="", lang="", letter="", page="", res="", year=""):
        fields = [""] * 12
        fields[0] = TYPE_ID
        fields[2] = order
        fields[3] = genre
        fields[4] = lang
        fields[5] = letter
        fields[8] = "" if str(page) in ("", "1") else str(page)
        fields[9] = res
        fields[11] = year
        return "/vodshow/" + "-".join([quote(str(x), safe="") for x in fields]) + ".html"

    def _page_count(self, html, fallback):
        pages = [self._safe_int(x, 0) for x in
                 re.findall(r'/vodshow/%s[0-9A-Za-z%%\-]*-(\d+)---\.html' % TYPE_ID, html)]
        pages = [p for p in pages if p > 0]
        return max(pages) if pages else max(fallback, 1)

    # ---------------------------------------------------------------- 详情
    def detailContent(self, ids):
        vid = str(ids[0] if isinstance(ids, list) else ids or "")
        try:
            html = self._get("/voddetail/%s.html" % vid)
            if not html:
                return {"list": []}

            name = ""
            m = re.search(r'<h2[^>]*class="[^"]*hl-dc-title[^"]*"[^>]*>(.*?)</h2>', html, re.S)
            if m:
                name = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            if not name:
                m = re.search(r'<title>(.*?)</title>', html, re.S)
                if m:
                    name = re.split(r'[-_|]', m.group(1).strip())[0].strip()

            pic = ""
            m = re.search(r'(?:data-original|src)="([^"]+\.(?:jpg|jpeg|png|webp))"', html)
            if m:
                pic = m.group(1)
                if pic.startswith("/"):
                    pic = self.host + pic

            intro = ""
            m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html)
            if m:
                intro = m.group(1).strip()

            sid, count = self._episodes(html, vid)
            play_urls = []
            for i in range(1, count + 1):
                play_urls.append("第%d集$%s" % (i, self._make_pid(vid, sid, i)))

            vod = {
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "type_name": "",
                "vod_year": "",
                "vod_area": "大陆",
                "vod_remarks": ("全%d集" % count) if count else "",
                "vod_actor": "",
                "vod_director": "",
                "vod_content": intro,
                "vod_play_from": "红果短剧",
                "vod_play_url": "#".join(play_urls),
            }
            return {"list": [vod]}
        except Exception as exc:
            print("红果详情读取失败:", exc)
            return {"list": []}

    def _episodes(self, html, vid):
        rows = re.findall(r'/vodplay/%s-(\d+)-(\d+)\.html' % re.escape(str(vid)), html)
        if not rows:
            return "1", 0
        sid = rows[0][0]
        count = 0
        for s, n in rows:
            if s == sid:
                count = max(count, self._safe_int(n, 0))
        return sid, count

    # ---------------------------------------------------------------- 搜索
    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg):
        page_num = self._safe_int(pg, 1)
        keyword = str(key or "").strip()
        if not keyword:
            return {"page": page_num, "pagecount": 1, "limit": self.page_size, "total": 0, "list": []}

        items = []
        try:
            items = self._search_web(keyword)
        except Exception as exc:
            print("红果搜索(页面)失败:", exc)
        if not items:
            try:
                items = self._search_suggest(keyword)
            except Exception as exc:
                print("红果搜索(联想)失败:", exc)

        start = (page_num - 1) * self.page_size
        return {
            "page": page_num,
            "pagecount": max(1, int(math.ceil(len(items) / float(self.page_size)))) if items else 1,
            "limit": self.page_size,
            "total": len(items),
            "list": self._to_vods(items[start:start + self.page_size]),
        }

    def _search_web(self, keyword):
        html = self._get("/vodsearch/-------------.html?" + urlencode({"wd": keyword}))
        return self._parse_items(html)

    def _search_suggest(self, keyword):
        text = self._get("/index.php/ajax/suggest?" + urlencode({"mid": 1, "wd": keyword}), ajax=True)
        if not text:
            return []
        try:
            data = json.loads(text)
        except Exception:
            return []
        items = []
        for it in (data or {}).get("list") or []:
            vid = str(it.get("id") or "").strip()
            if not vid:
                continue
            pic = it.get("pic") or ""
            if isinstance(pic, str) and pic.startswith("/"):
                pic = self.host + pic
            items.append({"vod_id": vid, "vod_name": it.get("name") or "", "vod_pic": pic, "vod_remarks": ""})
        return items

    # ---------------------------------------------------------------- 播放
    def playerContent(self, flag, pid, vipFlags):
        raw = str(pid or "")
        if "$" in raw:
            raw = raw.split("$", 1)[1]
        parts = raw.split("|", 2)
        if len(parts) >= 3:
            vid, sid, n = parts[0].strip(), (parts[1].strip() or "1"), parts[2].strip()
        else:
            vid, sid, n = raw.strip(), "1", "1"

        page_url = "%s/vodplay/%s-%s-%s.html" % (self.host, vid, sid, n)
        url = ""
        try:
            url = self._extract_m3u8(self._get("/vodplay/%s-%s-%s.html" % (vid, sid, n)))
        except Exception as exc:
            print("红果播放解析失败:", exc)

        if url:
            return {
                "parse": 0,
                "playUrl": "",
                "url": quote(url, safe=":/?&=%#"),
                "header": {"User-Agent": UA, "Referer": self.host + "/"},
                "jx": 0,
            }
        return {
            "parse": 1,
            "playUrl": "",
            "url": page_url,
            "header": {"User-Agent": UA, "Referer": self.host + "/"},
        }

    def _extract_m3u8(self, html):
        if not html:
            return ""
        for m in re.finditer(r'player_[0-9a-z]+\s*=\s*(\{.*?\})\s*(?:;|</script>)', html, re.S):
            try:
                obj = json.loads(m.group(1))
            except Exception:
                continue
            url = obj.get("url") or ""
            if ";" in url:
                url = url.split(";")[0]
            if isinstance(url, str) and re.search(r'https?://\S+\.m3u8', url):
                return url
        return ""

    # ---------------------------------------------------------------- 通用
    def _get(self, path, ajax=False):
        url = path if path.startswith("http") else self.host + path
        cached = self._cache.get(url)
        if cached and time.time() - cached[0] < 300:
            return cached[1]
        headers = dict(self.ajax_headers if ajax else self.headers)
        r = requests.get(url, headers=headers, timeout=self.timeout, verify=False)
        r.encoding = "utf-8"
        text = r.text if r.status_code == 200 else ""
        self._cache[url] = (time.time(), text)
        return text

    def _parse_items(self, html):
        if not html:
            return []
        result = []
        seen = set()
        for m in re.finditer(r'<a([^>]*)>', html):
            attrs = m.group(1) or ""
            hm = re.search(r'href="/voddetail/(\d+)\.html"', attrs)
            if not hm:
                continue
            vid = hm.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            tm = re.search(r'title="([^"]*)"', attrs)
            pm = re.search(r'data-original="([^"]*)"', attrs)
            if not pm:
                pm = re.search(r'src="(https?://[^"]+\.(?:jpg|jpeg|png|webp))"', attrs)
            window = html[m.end():m.end() + 500]
            rm = re.search(r'remarks[^>]*>([^<]*)<', window)
            if not rm:
                rm = re.search(r'remarks[^>]*>([^<]*)<', html[max(0, m.start() - 500):m.start()])
            result.append({
                "vod_id": vid,
                "vod_name": (tm.group(1) if tm else "").strip(),
                "vod_pic": pm.group(1) if pm else "",
                "vod_remarks": (rm.group(1) if rm else "").strip(),
            })
        return result

    def _to_vods(self, items):
        result = []
        for it in items or []:
            vid = str(it.get("vod_id") or "")
            if not vid:
                continue
            result.append({
                "vod_id": vid,
                "vod_name": it.get("vod_name") or "",
                "vod_pic": it.get("vod_pic") or "",
                "vod_remarks": it.get("vod_remarks") or "",
                "vod_content": "",
            })
        return result

    def _build_filters(self):
        def group(key, name, values):
            return {"key": key, "name": name, "value": [{"n": "全部", "v": ""}] + values}

        groups = [
            group("genre", "类型", [{"n": g, "v": g} for g in GENRES]),
            group("year", "年份", [{"n": y, "v": y} for y in YEARS]),
            group("lang", "语言", [{"n": l, "v": l} for l in LANGS]),
            group("letter", "字母", [{"n": c, "v": c} for c in LETTERS]),
            group("res", "资源", [{"n": r, "v": r} for r in RESES]),
        ]
        return {tid: groups for tid, _name in CLASSES}

    def _make_pid(self, vid, sid, n):
        return "%s|%s|%s" % (vid, sid or "1", n)

    def _safe_int(self, value, default=0):
        try:
            return int(value)
        except Exception:
            return default
