# coding=utf-8
# !/usr/bin/python
"""
红果短剧 TVBox / OK影视 / 影视仓 Python 源（方案 A：红果官方分类 + 聚合站播放 2026）。

分类结构完全照红果：
- 顶级只有两类：真人短剧(real) / AI短剧(ai)
- 类内再按题材筛选：爱情/都市/家庭/古装/年代/逆袭/玄幻 ... （真人）或 剧情/恋爱/脑洞/宫廷 ... （AI）

数据分工：
- 分类 / 题材 / 剧集清单：红果官方数据源（公开免费）
    https://orz.icicic.icu/api/api.php
    ?type=days_7_to_date&action=today_new&all_time=true&page=N    真人短剧
    ?type=days_7_to_date&action=aiju_today_new&all_time=true&page=N  AI短剧
    ?type=bookid&book_id=...                                       详情/分集
    ?name=关键词&tab_type=11|19                                    搜索
- 播放：聚合站 hongguoapp.cn（按剧名搜索 -> /voddetail -> /vodplay -> m3u8）

已知代价（免费路线固有）：聚合站按批次收录红果内容，真人短剧仅部分可播，
AI短剧聚合站基本未收录 —— 不可播的剧会在详情标注 "聚合站未收录·暂不可播"。
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


ORZ = "https://orz.icicic.icu/api/api.php"
AGG = "https://www.hongguoapp.cn"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

CLASSES = [
    ("real", "真人短剧"),
    ("ai", "AI短剧"),
]
REAL_GENRES = ["爱情", "都市", "家庭", "成长", "逆袭", "剧情", "悬疑",
               "古装", "年代", "奇幻", "青春", "玄幻", "喜剧", "家族"]
AI_GENRES = ["剧情", "恋爱", "脑洞", "宫廷", "种田", "末世", "总裁",
             "武侠", "玄幻", "悬疑", "萌宝", "科幻", "家族", "日常"]

PAGE_SIZE = 20
SCAN_GUARD = 10


class Spider(Spider):
    def __init__(self):
        self.host = AGG
        self.headers = {
            "User-Agent": UA,
            "Referer": AGG + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self.agg_ajax_headers = {
            "User-Agent": UA,
            "Referer": AGG + "/",
            "X-Requested-With": "XMLHttpRequest",
        }
        self.orz_headers = {"User-Agent": UA, "Accept": "application/json"}
        self.timeout = 20
        self._cache = {}
        self._scan = {}
        self._meta = {}

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
        result = {
            "class": [{"type_id": t, "type_name": n} for t, n in CLASSES],
            "filters": self._build_filters(),
        }
        result["list"] = self.homeVideoContent().get("list", [])
        return result

    def homeVideoContent(self):
        try:
            data = self._orz_get(type="days_7_to_date", action="today_new")
            items = [self._orz_to_vod(it) for it in (data.get("data") or [])]
            return {"list": items[:PAGE_SIZE]}
        except Exception as exc:
            print("红果首页读取失败:", exc)
            return {"list": []}

    # ---------------------------------------------------------------- 分类
    def categoryContent(self, tid, pg, filter, extend):
        page = self._safe_int(pg, 1)
        ext = extend if isinstance(extend, dict) else {}
        genre = str(ext.get("genre") or "").strip()
        action = "aiju_today_new" if tid == "ai" else "today_new"
        key = "%s|%s" % (tid, genre)

        if page <= 1 or key not in self._scan:
            self._scan[key] = {"items": [], "next": 1, "done": False}
        state = self._scan[key]

        target = page * PAGE_SIZE
        guard = 0
        while len(state["items"]) < target and not state["done"] and guard < SCAN_GUARD:
            guard += 1
            data = self._orz_get(type="days_7_to_date", action=action,
                                 all_time="true", page=str(state["next"]))
            rows = data.get("data") or []
            if not rows:
                state["done"] = True
                break
            state["next"] += 1
            for it in rows:
                if genre and self._main_tag(it.get("type")) != genre:
                    continue
                state["items"].append(it)

        start = (page - 1) * PAGE_SIZE
        chunk = state["items"][start:start + PAGE_SIZE]
        vods = [self._orz_to_vod(it) for it in chunk]
        pagecount = page if state["done"] else page + 1
        return {
            "page": page,
            "pagecount": pagecount,
            "limit": PAGE_SIZE,
            "total": len(state["items"]),
            "list": vods,
        }

    # ---------------------------------------------------------------- 详情
    def detailContent(self, ids):
        raw = str(ids[0] if isinstance(ids, list) else ids or "")
        try:
            if raw.startswith("h:"):
                return self._agg_detail_content(raw[2:])
            book = raw[2:] if raw.startswith("o:") else raw
            return self._orz_detail_content(book, raw)
        except Exception as exc:
            print("红果详情读取失败:", exc)
            return {"list": []}

    def _orz_detail_content(self, book, raw_id):
        data = self._orz_get(type="bookid", book_id=book)
        if not data or self._safe_int(data.get("code"), 0) != 200:
            return {"list": []}
        meta = self._meta.get(book, {})
        name = data.get("book_name") or meta.get("name") or ""
        eps = data.get("data") or []

        vod = {
            "vod_id": raw_id or ("o:" + book),
            "vod_name": name,
            "vod_pic": meta.get("cover") or "",
            "type_name": meta.get("tag") or "",
            "vod_year": "",
            "vod_area": "大陆",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": meta.get("intro") or "",
            "vod_play_from": "红果短剧",
        }

        hgid = self._agg_suggest(name) if name else None
        sid, count = ("1", 0)
        if hgid:
            sid, count = self._agg_episodes(hgid)

        if hgid and count:
            urls = ["第%d集$%s|%s|%d" % (i, hgid, sid, i) for i in range(1, count + 1)]
            vod["vod_play_url"] = "#".join(urls)
            vod["vod_remarks"] = "可播·共%d集" % count
        else:
            vod["vod_play_url"] = "暂不可播$o|%s|1" % book
            vod["vod_remarks"] = "聚合站未收录·暂不可播"
            if not vod["vod_content"]:
                vod["vod_content"] = "本剧来自红果官方库，聚合站暂未收录，无法播放。"
        return {"list": [vod]}

    def _agg_detail_content(self, vid):
        html = self._agg_get("/voddetail/%s.html" % vid)
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
                pic = AGG + pic
        intro = ""
        m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html)
        if m:
            intro = m.group(1).strip()
        sid, count = self._agg_episodes(vid)
        urls = ["第%d集$%s|%s|%d" % (i, vid, sid, i) for i in range(1, count + 1)]
        return {"list": [{
            "vod_id": "h:" + vid,
            "vod_name": name,
            "vod_pic": pic,
            "type_name": "",
            "vod_year": "",
            "vod_area": "大陆",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": intro,
            "vod_remarks": ("全%d集" % count) if count else "",
            "vod_play_from": "红果短剧",
            "vod_play_url": "#".join(urls),
        }]}

    # ---------------------------------------------------------------- 搜索
    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg):
        page = self._safe_int(pg, 1)
        kw = str(key or "").strip()
        if not kw:
            return {"page": page, "pagecount": 1, "limit": PAGE_SIZE, "total": 0, "list": []}

        items = []
        try:
            for tab in ("11", "19"):
                data = self._orz_get(name=kw, tab_type=tab, page=str(page))
                for it in (data.get("data") or []):
                    items.append(self._orz_to_vod(it))
        except Exception as exc:
            print("红果官方搜索失败:", exc)

        if page == 1:
            try:
                for it in self._agg_suggest_list(kw):
                    items.append(it)
            except Exception as exc:
                print("聚合站搜索失败:", exc)

        seen = set()
        uniq = []
        for it in items:
            vid = it.get("vod_id")
            if vid and vid not in seen:
                seen.add(vid)
                uniq.append(it)
        return {
            "page": page,
            "pagecount": page + 1 if len(uniq) >= PAGE_SIZE else page,
            "limit": PAGE_SIZE,
            "total": len(uniq),
            "list": uniq,
        }

    # ---------------------------------------------------------------- 播放
    def playerContent(self, flag, pid, vipFlags):
        raw = str(pid or "")
        if "$" in raw:
            raw = raw.split("$", 1)[1]
        if raw.startswith("o|"):
            return {
                "parse": 0, "playUrl": "", "url": "",
                "header": {"User-Agent": UA, "Referer": AGG + "/"},
            }
        parts = raw.split("|")
        if len(parts) >= 3:
            vid, sid, n = parts[0].strip(), (parts[1].strip() or "1"), parts[2].strip()
        else:
            vid, sid, n = raw.strip(), "1", "1"

        url = ""
        try:
            url = self._extract_m3u8(self._agg_get("/vodplay/%s-%s-%s.html" % (vid, sid, n)))
        except Exception as exc:
            print("红果播放解析失败:", exc)

        if url:
            return {
                "parse": 0,
                "playUrl": "",
                "url": quote(url, safe=":/?&=%#"),
                "header": {"User-Agent": UA, "Referer": AGG + "/"},
                "jx": 0,
            }
        return {
            "parse": 1,
            "playUrl": "",
            "url": "%s/vodplay/%s-%s-%s.html" % (AGG, vid, sid, n),
            "header": {"User-Agent": UA, "Referer": AGG + "/"},
        }

    # ---------------------------------------------------------------- 红果官方源
    def _orz_get(self, **params):
        q = urlencode(params)
        url = ORZ + "?" + q
        cached = self._cache.get(url)
        if cached and time.time() - cached[0] < 300:
            return cached[1]
        data = {}
        try:
            r = requests.get(ORZ, params=params, headers=self.orz_headers,
                             timeout=self.timeout, verify=False)
            data = r.json()
        except Exception as exc:
            print("红果官方源请求失败:", exc)
            data = {}
        self._cache[url] = (time.time(), data)
        return data

    def _orz_to_vod(self, it):
        book = str(it.get("book_id") or "")
        name = (it.get("title") or it.get("book_name") or "").strip()
        cover = it.get("cover") or it.get("cover_url") or ""
        tag = self._main_tag(it.get("type"))
        self._meta[book] = {"name": name, "cover": cover, "tag": tag,
                            "intro": it.get("intro") or ""}
        return {
            "vod_id": "o:" + book,
            "vod_name": name,
            "vod_pic": cover,
            "vod_remarks": tag,
            "vod_content": it.get("intro") or "",
        }

    def _main_tag(self, type_str):
        if not type_str:
            return ""
        return str(type_str).split(",")[0].split("?")[0].strip()

    def _build_filters(self):
        def group(genres):
            return [{"key": "genre", "name": "题材",
                     "value": [{"n": "全部", "v": ""}] + [{"n": g, "v": g} for g in genres]}]
        return {"real": group(REAL_GENRES), "ai": group(AI_GENRES)}

    # ---------------------------------------------------------------- 聚合站
    def _agg_get(self, path, ajax=False):
        url = path if path.startswith("http") else AGG + path
        cached = self._cache.get(url)
        if cached and time.time() - cached[0] < 300:
            return cached[1]
        headers = dict(self.agg_ajax_headers if ajax else self.headers)
        text = ""
        try:
            r = requests.get(url, headers=headers, timeout=self.timeout, verify=False)
            r.encoding = "utf-8"
            text = r.text if r.status_code == 200 else ""
        except Exception as exc:
            print("聚合站请求失败:", exc)
        self._cache[url] = (time.time(), text)
        return text

    def _agg_suggest(self, name):
        for it in self._agg_suggest_list(name):
            if (it.get("vod_name") or "").strip() == str(name).strip():
                return it.get("vod_id", "")[2:]
        lst = self._agg_suggest_list(name)
        return lst[0].get("vod_id", "")[2:] if lst else None

    def _agg_suggest_list(self, name):
        name = str(name or "").strip()
        if not name:
            return []
        text = self._agg_get("/index.php/ajax/suggest?" + urlencode({"mid": 1, "wd": name}), ajax=True)
        if not text:
            return []
        try:
            data = json.loads(text)
        except Exception:
            return []
        result = []
        for it in (data.get("list") or []):
            vid = str(it.get("id") or "").strip()
            if not vid:
                continue
            pic = it.get("pic") or ""
            if isinstance(pic, str) and pic.startswith("/"):
                pic = AGG + pic
            result.append({
                "vod_id": "h:" + vid,
                "vod_name": it.get("name") or "",
                "vod_pic": pic,
                "vod_remarks": "",
                "vod_content": "",
            })
        return result

    def _agg_episodes(self, vid):
        html = self._agg_get("/voddetail/%s.html" % vid)
        if not html:
            return "1", 0
        counts = {}
        for s, n in re.findall(r'/vodplay/%s-(\d+)-(\d+)\.html' % re.escape(str(vid)), html):
            counts[s] = max(counts.get(s, 0), self._safe_int(n, 0))
        if not counts:
            return "1", 0
        sid = max(counts, key=lambda k: counts[k])
        return sid, counts[sid]

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

    def _safe_int(self, value, default=0):
        try:
            return int(value)
        except Exception:
            return default
