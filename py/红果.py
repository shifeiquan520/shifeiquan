# coding=utf-8
# !/usr/bin/python
"""
红果短剧 TVBox / OK影视 / 影视仓 Python 源（方案 1：ORZ 官方元数据 + 多聚合站播放 2026）。

架构：
- 元数据（分类/筛选/详情/搜索）：ORZ 免费官方 API（https://orz.icicic.icu/api/api.php）
  - 真人短剧：type=days_7_to_date&action=today_new
  - AI短剧：type=days_7_to_date&action=aiju_today_new
  - 详情：type=bookid&book_id=...
  - 搜索：name=关键词&tab_type=11|19
  - 筛选题材来自官方 type 标签
- 播放：多聚合站聚合（按剧名匹配），按优先级尝试，去重
  - https://www.hongguostudio.com (源站，非 CF)
  - https://www.hongguoapp.cn (CF 备用)
- 顶级分类：真人短剧 / AI短剧（无漫剧）
- ORZ 挂了时：自动降级用聚合站搜索/分类，题材用本地缓存
"""

import json
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
    class Spider(object):
        pass


ORZ = "https://orz.icicic.icu/api/api.php"
AGG_HOSTS = [
    "https://www.hongguostudio.com",   # 源站，nginx，非 CF
    "https://www.hongguoapp.cn",       # CF 备用
]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

CLASSES = [("real", "真人短剧"), ("ai", "AI短剧")]

# 官方题材（来自 ORZ type 标签首段）——本地兜底
REAL_GENRES = ["古装", "战争", "青春偶像", "喜剧", "家庭", "犯罪", "动作", "奇幻", "剧情",
               "历史", "经典", "乡村", "情景", "商战", "网剧"]
AI_GENRES = ["剧情", "恋爱", "脑洞", "宫廷", "种田", "末世", "总裁",
             "武侠", "玄幻", "悬疑", "萌宝", "科幻", "家族", "日常"]

AI_KEYWORDS = ["真人AI", "AI版", "AI真人"]
SEED_AI = ["风水天师", "万妖图录传", "斩仙台下震惊诸神", "我家井里有条龙"]

# AI 题材 -> 聚合站搜索关键词映射（ORZ 挂了时兜底用）
AI_GENRE_KEYWORDS = {
    "剧情": ["剧情AI", "剧情真人AI", "AI剧情"],
    "恋爱": ["恋爱AI", "甜宠AI", "言情AI"],
    "脑洞": ["脑洞AI", "悬疑AI", "反转AI"],
    "宫廷": ["宫廷AI", "古装AI", "宫斗AI"],
    "种田": ["种田AI", "经营AI", "发家致富AI"],
    "末世": ["末世AI", "废土AI", "生存AI"],
    "总裁": ["总裁AI", "霸总AI", "豪门AI"],
    "武侠": ["武侠AI", "仙侠AI", "江湖AI"],
    "玄幻": ["玄幻AI", "奇幻AI", "魔幻AI"],
    "悬疑": ["悬疑AI", "推理AI", "破案AI"],
    "萌宝": ["萌宝AI", "带球跑AI", "宝宝AI"],
    "科幻": ["科幻AI", "未来AI", "机甲AI"],
    "家族": ["家族AI", "豪门恩怨AI", "传承AI"],
    "日常": ["日常AI", "生活AI", "治愈AI"],
}

PAGE_SIZE = 20
ORZ_PAGE_SIZE = 18
SCAN_GUARD = 10  # 分类扫描最多翻多少页 ORZ
TID = "51"

# ORZ 健康检查缓存
_orz_healthy_cache = {"time": 0, "ok": True}


class Spider(Spider):
    def __init__(self):
        self.agg_hosts = AGG_HOSTS
        self._agg_host = AGG_HOSTS[0]
        self.timeout = 12
        self._cache = {}
        self._scan_state = {}  # 分类扫描状态
        self._meta_cache = {}  # ORZ 书籍元数据缓存
        self._ai_cache = None  # AI 列表缓存

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
        return {
            "class": [{"type_id": t, "type_name": n} for t, n in CLASSES],
            "filters": self._build_filters(),
            "list": self.homeVideoContent().get("list", []),
        }

    def homeVideoContent(self):
        # 优先 ORZ 取最新推荐
        try:
            data = self._orz_get(type="days_7_to_date", action="today_new", all_time="true", page="1")
            items = [self._orz_to_vod(it) for it in (data.get("data") or [])]
            if items:
                return {"list": items[:PAGE_SIZE]}
        except Exception as exc:
            print("红果首页读取失败:", exc)
        # 回退聚合站首页
        try:
            return {"list": self._parse_items(self._agg_get("/"))[:PAGE_SIZE]}
        except Exception as exc:
            print("聚合站首页读取失败:", exc)
            return {"list": []}

    # ---------------------------------------------------------------- 分类
    def categoryContent(self, tid, pg, filter, extend):
        page = self._safe_int(pg, 1)
        ext = extend if isinstance(extend, dict) else {}
        genre = str(ext.get("genre") or "").strip()

        # 真人短剧：优先 ORZ，失败回退聚合站 /vodshow
        if tid == "real":
            return self._real_category(page, genre)
        # AI短剧：支持题材筛选（ORZ 恢复后走官方，挂了走关键词映射）
        return self._ai_category(page, genre)

    def _real_category(self, page, genre):
        # 先尝试 ORZ 官方分类（含题材筛选）
        try:
            res = self._real_category_orz(page, genre)
            if res["list"]:
                return res
        except Exception:
            pass
        # ORZ 挂了/无数据 -> 直接走聚合站分页（不缓存，透传分页）
        return self._real_category_agg(page, genre)

    def _real_category_orz(self, page, genre):
        key = "real|%s" % genre
        if page <= 1 or key not in self._scan_state:
            self._scan_state[key] = {"items": [], "next_page": 1, "done": False}
        state = self._scan_state[key]

        target = page * PAGE_SIZE
        guard = 0
        while len(state["items"]) < target and not state["done"] and guard < SCAN_GUARD:
            guard += 1
            data = self._orz_get(type="days_7_to_date", action="today_new",
                                 all_time="true", page=str(state["next_page"]))
            rows = data.get("data") or []
            if not rows:
                raise ValueError("ORZ no data")
            state["next_page"] += 1
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

    def _real_category_agg(self, page, genre):
        """聚合站 /vodshow 兜底：真人短剧"""
        url = self._show_url(genre=genre, page=page)
        html = self._agg_get(url)
        vods = self._parse_items(html)
        # 给聚合站 vid 加 "h:" 前缀，区分 ORZ book_id
        for v in vods:
            if v.get("vod_id") and not v["vod_id"].startswith("h:"):
                v["vod_id"] = "h:" + v["vod_id"]
        pagecount = self._page_count(html, page) if vods else page
        return {
            "page": page,
            "pagecount": pagecount,
            "limit": PAGE_SIZE,
            "total": len(vods),
            "list": vods[:PAGE_SIZE] if len(vods) > PAGE_SIZE else vods,
        }

    def _ai_category(self, page, genre=""):
        items = self._ai_list()
        # ORZ 挂了时聚合站无 AI 题材元数据，忽略 genre，返回全部 AI 剧
        if genre:
            print("AI题材筛选需要 ORZ 官方接口，当前已降级，显示全部 AI 剧")
        start = (page - 1) * PAGE_SIZE
        chunk = items[start:start + PAGE_SIZE]
        pagecount = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
        return {
            "page": page,
            "pagecount": pagecount,
            "limit": PAGE_SIZE,
            "total": len(items),
            "list": chunk,
        }

    def _ai_list(self):
        now = time.time()
        if self._ai_cache and now - self._ai_cache[0] < 1800:
            return self._ai_cache[1]

        items = []
        seen = set()

        def add(vod):
            if vod["vod_id"] not in seen:
                seen.add(vod["vod_id"])
                items.append(vod)

        for kw in AI_KEYWORDS:
            for vod in self._agg_search_list(kw):
                add(vod)
        for seed in SEED_AI:
            core = self._norm(seed)[:4]
            for vod in self._agg_search_list(seed):
                if core and core in self._norm(vod.get("vod_name") or ""):
                    add(vod)
                    break

        self._ai_cache = (now, items)
        return items

    # ---------------------------------------------------------------- 详情
    def detailContent(self, ids):
        raw = str(ids[0] if isinstance(ids, list) else ids or "").strip()
        if not raw:
            return {"list": []}
        try:
            return self._detail(raw)
        except Exception as exc:
            print("红果详情读取失败:", exc)
            return {"list": []}

    def _detail(self, raw_id):
        raw_id = str(raw_id).strip()
        # 聚合站 vid 带 "h:" 前缀
        if raw_id.startswith("h:"):
            return self._detail_agg(raw_id[2:])
        # ORZ 官方 book_id
        return self._detail_orz(raw_id)

    def _detail_orz(self, book_id):
        # 先试 ORZ 官方详情
        data = self._orz_get(type="bookid", book_id=book_id)
        if not data or self._safe_int(data.get("code"), 0) != 200:
            # ORZ 挂了，回退聚合站搜索
            return self._detail_fallback(book_id)

        meta = self._meta_cache.get(book_id, {})
        name = data.get("book_name") or meta.get("name") or ""
        eps = data.get("data") or []

        vod = {
            "vod_id": book_id,
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

        agg_vid = self._agg_search_vid(name) if name else None
        sid, count = ("1", 0)
        if agg_vid:
            sid, count = self._agg_episodes(agg_vid)

        if agg_vid and count:
            urls = ["第%d集$%s|%s|%d" % (i, agg_vid, sid, i) for i in range(1, count + 1)]
            vod["vod_play_url"] = "#".join(urls)
            vod["vod_remarks"] = "可播·共%d集" % count
        else:
            vod["vod_play_url"] = "暂不可播$o|%s|1" % book_id
            vod["vod_remarks"] = "聚合站未收录"
            if not vod["vod_content"]:
                vod["vod_content"] = "本剧来自红果官方库，聚合站暂未收录，无法播放。"

        return {"list": [vod]}

    def _detail_agg(self, vid):
        """聚合站详情：直接用 vid 取聚合站详情页"""
        html = self._agg_get("/voddetail/%s.html" % vid)
        if not html:
            return {"list": [{"vod_id": "h:" + vid, "vod_name": "未知", "vod_remarks": "获取失败"}]}

        name = ""
        m = re.search(r'<h2[^>]*class="[^"]*hl-dc-title[^"]*"[^>]*>(.*?)</h2>', html, re.S)
        if m:
            name = self._strip(m.group(1))
        if not name:
            m = re.search(r'<meta\s+property="og:title"\s+content="([^"]*)"', html)
            if m:
                name = m.group(1).strip()
        if not name:
            m = re.search(r'<title>(.*?)</title>', html, re.S)
            if m:
                name = re.split(r'[-_|]', self._strip(m.group(1)))[0].strip()

        pic = ""
        m = re.search(r'class="[^"]*hl-item-thumb[^"]*"[^>]*data-original="([^"]+)"', html)
        if not m:
            m = re.search(r'(?:data-original|data-src)="([^"]+\.(?:jpg|jpeg|png|webp))"', html)
        if m:
            pic = m.group(1).strip()
            if pic.startswith("//"):
                pic = "https:" + pic
            elif pic.startswith("/"):
                pic = self._agg_base() + pic

        intro = ""
        m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html)
        if m:
            intro = m.group(1).strip()

        remark = ""
        m = re.search(r'class="[^"]*hl-dc-remarks[^"]*"[^>]*>([^<]*)<', html)
        if not m:
            m = re.search(r'class="[^"]*remarks[^"]*"[^>]*>([^<]*)<', html)
        if m:
            remark = m.group(1).strip()

        sid, count = self._agg_episodes(vid)
        if count <= 1:
            urls = ["全集$%s|%s|1" % (vid, sid)]
        else:
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
            "vod_remarks": remark or (("全%d集" % count) if count else ""),
            "vod_play_from": "红果短剧",
            "vod_play_url": "#".join(urls),
        }]}

    def _detail_fallback(self, book_id):
        """ORZ 挂了时：用聚合站搜索兜底"""
        # 从缓存里找元数据
        meta = self._meta_cache.get(book_id, {})
        name = meta.get("name") or ""
        if not name:
            # 实在没有名字，直接返回不可播
            return {"list": [{
                "vod_id": book_id,
                "vod_name": "未知剧集",
                "vod_pic": "",
                "type_name": "",
                "vod_year": "",
                "vod_area": "大陆",
                "vod_actor": "",
                "vod_director": "",
                "vod_content": "ORZ 官方源暂不可用，且无法匹配聚合站数据。",
                "vod_play_from": "红果短剧",
                "vod_play_url": "暂不可播$o|%s|1" % book_id,
                "vod_remarks": "数据源异常",
            }]}

        agg_vid = self._agg_search_vid(name) if name else None
        sid, count = ("1", 0)
        if agg_vid:
            sid, count = self._agg_episodes(agg_vid)

        if agg_vid and count:
            urls = ["第%d集$%s|%s|%d" % (i, agg_vid, sid, i) for i in range(1, count + 1)]
            remarks = "可播·共%d集" % count
            play_url = "#".join(urls)
        else:
            urls = "暂不可播$o|%s|1" % book_id
            remarks = "聚合站未收录"
            play_url = urls

        return {"list": [{
            "vod_id": book_id,
            "vod_name": name,
            "vod_pic": meta.get("cover") or "",
            "type_name": meta.get("tag") or "",
            "vod_year": "",
            "vod_area": "大陆",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": meta.get("intro") or "",
            "vod_play_from": "红果短剧",
            "vod_play_url": play_url,
            "vod_remarks": remarks,
        }]}

    # ---------------------------------------------------------------- 搜索
    def searchContent(self, key, quick, pg="1"):
        page = self._safe_int(pg, 1)
        kw = str(key or "").strip()
        if not kw:
            return {"page": page, "pagecount": 1, "limit": PAGE_SIZE, "total": 0, "list": []}

        items = []
        # 1. 官方搜索
        try:
            for tab in ("11", "19"):  # 真人/AI
                data = self._orz_get(name=kw, tab_type=tab, page=str(page))
                for it in (data.get("data") or []):
                    items.append(self._orz_to_vod(it))
        except Exception as exc:
            print("红果官方搜索失败:", exc)

        # 2. 聚合站搜索兜底
        if page == 1:
            try:
                for it in self._agg_search_list(kw):
                    items.append(it)
            except Exception as exc:
                print("聚合站搜索失败:", exc)

        # 去重
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
        if raw.startswith("o|"):  # 官方源无直接播放
            return {"parse": 0, "playUrl": "", "url": "", "header": {"User-Agent": UA, "Referer": self._agg_base() + "/"}}

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
                "header": {"User-Agent": UA, "Referer": self._agg_base() + "/"},
                "jx": 0,
            }
        return {
            "parse": 1,
            "playUrl": "",
            "url": "%s/vodplay/%s-%s-%s.html" % (self._agg_base(), vid, sid, n),
            "header": {"User-Agent": UA, "Referer": self._agg_base() + "/"},
        }

    # ---------------------------------------------------------------- ORZ 官方源
    def _orz_get(self, **params):
        global _orz_healthy_cache
        q = urlencode(params)
        url = ORZ + "?" + q
        cached = self._cache.get(url)
        if cached and time.time() - cached[0] < 300:
            return cached[1]
        data = {}
        try:
            r = requests.get(ORZ, params=params,
                             headers={"User-Agent": UA, "Accept": "application/json"},
                             timeout=self.timeout, verify=False)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/json"):
                data = r.json()
            else:
                # 非 JSON（如 CF 521 页面），标记不健康
                _orz_healthy_cache = {"time": time.time(), "ok": False}
                data = {}
        except Exception as exc:
            print("红果官方源请求失败:", exc)
            _orz_healthy_cache = {"time": time.time(), "ok": False}
            data = {}
        self._cache[url] = (time.time(), data)
        return data

    def _orz_to_vod(self, it):
        book = str(it.get("book_id") or "")
        name = (it.get("title") or it.get("book_name") or "").strip()
        cover = it.get("cover") or it.get("cover_url") or ""
        tag = self._main_tag(it.get("type"))
        self._meta_cache[book] = {"name": name, "cover": cover, "tag": tag,
                                  "intro": it.get("intro") or ""}
        return {
            "vod_id": book,
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

    # ---------------------------------------------------------------- 聚合站（播放源）
    def _agg_base(self):
        return getattr(self, "_agg_host", AGG_HOSTS[0]) or AGG_HOSTS[0]

    def _agg_host_order(self):
        cur = self._agg_base()
        return [cur] + [h for h in AGG_HOSTS if h != cur]

    def _agg_get(self, path, ajax=False):
        path = str(path or "")
        if path.startswith("http"):
            return self._agg_fetch(path, ajax)[1]
        cached = self._cache.get(path)
        if cached and time.time() - cached[0] < 300:
            return cached[1]
        text = ""
        for _round in range(2):
            for base in self._agg_host_order():
                status, body = self._agg_fetch(base + path, ajax)
                if status == 200 and body and not self._is_blocked(status, body):
                    self._agg_host = base
                    text = body
                    break
            if text:
                break
            time.sleep(0.25)
        self._cache[path] = (time.time(), text)
        return text

    def _agg_fetch(self, url, ajax=False):
        base = "/".join(url.split("/", 3)[:3]) or self._agg_base()
        headers = {
            "User-Agent": UA,
            "Referer": base + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        if ajax:
            headers["X-Requested-With"] = "XMLHttpRequest"
        try:
            r = requests.get(url, headers=headers, timeout=self.timeout, verify=False)
            r.encoding = "utf-8"
            return r.status_code, (r.text if r.status_code == 200 else "")
        except Exception as exc:
            print("聚合站请求失败:", url, exc)
            return 0, ""

    def _is_blocked(self, status, text):
        if status in (403, 429, 503):
            return True
        low = (text or "")[:2000].lower()
        for marker in ("just a moment", "cf-browser-verification", "challenge-platform",
                       "attention required", "cf_chl_opt", "cf-chl"):
            if marker in low:
                return True
        return False

    def _agg_search_vid(self, name):
        """在聚合站按剧名搜索，返回最匹配的 vid"""
        for it in self._agg_search_list(name):
            if (it.get("vod_name") or "").strip() == name.strip():
                return it.get("vod_id", "")[2:] if it.get("vod_id", "").startswith("h:") else it.get("vod_id")
        lst = self._agg_search_list(name)
        return lst[0].get("vod_id", "")[2:] if lst else None

    def _agg_search_list(self, name):
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
        out = []
        for it in (data.get("list") or []):
            vid = str(it.get("id") or "").strip()
            if not vid:
                continue
            pic = it.get("pic") or ""
            if isinstance(pic, str):
                if pic.startswith("//"):
                    pic = "https:" + pic
                elif pic.startswith("/"):
                    pic = self._agg_base() + pic
            out.append({
                "vod_id": "h:" + vid,
                "vod_name": it.get("name") or "",
                "vod_pic": pic,
                "vod_remarks": "",
                "vod_content": "",
            })
        return out

    def _parse_items(self, html):
        if not html:
            return []
        out = []
        seen = set()
        pattern = re.compile(r'<a\b([^>]*href="[^"]*?/voddetail/(\d+)\.html"[^>]*)>(.*?)</a>', re.S)
        for m in pattern.finditer(html):
            vid = m.group(2)
            if vid in seen:
                continue
            attrs = m.group(1)
            inner = m.group(3)

            name = ""
            tm = re.search(r'title="([^"]*)"', attrs)
            if tm:
                name = tm.group(1).strip()
            if not name:
                name = self._strip(inner)

            pic = ""
            pm = (re.search(r'data-original="([^"]+)"', attrs)
                  or re.search(r'data-src="([^"]+)"', attrs)
                  or re.search(r'src="([^"]+\.(?:jpg|jpeg|png|webp))"', attrs))
            if pm:
                pic = pm.group(1).strip()
                if pic.startswith("//"):
                    pic = "https:" + pic
                elif pic.startswith("/"):
                    pic = self._agg_base() + pic

            rem = ""
            rm = re.search(r'remarks[^>]*>([^<]*)<', inner)
            if not rm:
                window = html[m.end():m.end() + 500]
                rm = re.search(r'remarks[^>]*>([^<]*)<', window)
            if rm:
                rem = rm.group(1).strip()

            seen.add(vid)
            out.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": rem,
                "vod_content": "",
            })
        return out

    def _agg_episodes(self, vid):
        html = self._agg_get("/voddetail/%s.html" % vid)
        if not html:
            return "1", 0
        counts = {}
        for sid, n in re.findall(r'/vodplay/%s-(\d+)-(\d+)\.html' % re.escape(str(vid)), html):
            counts[sid] = max(counts.get(sid, 0), self._safe_int(n, 0))
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

    # ---------------------------------------------------------------- 工具
    def _show_url(self, genre="", year="", lang="", res="", page=1):
        fields = [""] * 12
        fields[0] = TID
        fields[3] = genre
        fields[4] = lang
        fields[8] = str(page) if page and page > 1 else ""
        fields[9] = res
        fields[11] = year
        enc = [quote(v, safe="") if v else "" for v in fields]
        return "/vodshow/" + "-".join(enc) + ".html"

    def _page_count(self, html, cur):
        if html:
            idx = html.find("hl-page-tips")
            seg = html[idx:idx + 200] if idx >= 0 else ""
            m = re.search(r'(\d+)\s*[^0-9]*\s*(\d+)', seg)
            if m:
                return max(cur, self._safe_int(m.group(2), cur))
        return cur + 1

    def _norm(self, s):
        s = re.sub(r'[(\uff08\u3010\[].*?[)\uff09\u3011\]]', '', str(s or ''))
        s = re.sub(r'\u7b2c[0-9\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e]+[\u5b63\u90e8\u96c6]', '', s)
        s = re.sub(r'[0-9]+$', '', s)
        return re.sub(r'[\s\-_:\uff1a\u00b7,\uff0c\u3002\uff01\uff1f\.!\?"\u201c\u201d\']', '', s)

    def _strip(self, html):
        return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', str(html or ''))).strip()

    def _safe_int(self, value, default=0):
        try:
            return int(str(value).strip())
        except Exception:
            return default
