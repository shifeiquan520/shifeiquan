# coding=utf-8
# !/usr/bin/python
"""
红果短剧 TVBox / OK影视 / 影视仓 Python 源（方案 C：纯聚合站 2026）。

数据源：聚合站 https://www.hongguoapp.cn （苹果CMS/conch 模板，片源为「暴风资源」m3u8）。
- 真人短剧：聚合站分类 tid=51，/vodshow 12 字段拼接（题材/年份/语言/资源 + 翻页），可播。
- AI短剧  ：聚合站未单列分类，本源用关键词（真人AI / AI版 / AI真人）+ 少量种子剧名
            在聚合站内搜索，AI 判定以命中的聚合站条目为准，只收录聚合站能解析出 m3u8 的条目。
- 播放    ：/vodplay/{vid}-{sid}-{n}.html -> player_aaaa.url（m3u8）。
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


HOSTS = ["https://www.hongguostudio.com", "https://www.hongguoapp.cn"]
AGG = HOSTS[0]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

CLASSES = [("real", "真人短剧"), ("ai", "AI短剧")]

GENRES = ["古装", "战争", "青春偶像", "喜剧", "家庭", "犯罪", "动作", "奇幻", "剧情",
          "历史", "经典", "乡村", "情景", "商战", "网剧"]
YEARS = [str(y) for y in range(2026, 2010, -1)]
LANGS = ["国语", "英语"]
RESES = ["正片", "预告片", "花絮"]

AI_KEYWORDS = ["真人AI", "AI版", "AI真人"]
SEED_AI = ["风水天师", "万妖图录传", "斩仙台下震惊诸神", "我家井里有条龙"]

PAGE_SIZE = 20
TID = "51"


class Spider(Spider):
    def __init__(self):
        self.host = AGG
        self.timeout = 12
        self._host = HOSTS[0]
        self._cache = {}
        self._ai_cache = None

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
        try:
            return {"list": self._parse_items(self._get("/"))[:PAGE_SIZE]}
        except Exception as exc:
            print("红果首页读取失败:", exc)
            return {"list": []}

    # ---------------------------------------------------------------- 分类
    def categoryContent(self, tid, pg, filter, extend):
        page = self._safe_int(pg, 1)
        if tid == "ai":
            return self._ai_category(page)
        return self._real_category(page, extend if isinstance(extend, dict) else {})

    def _real_category(self, page, extend):
        url = self._show_url(
            genre=str(extend.get("genre") or "").strip(),
            year=str(extend.get("year") or "").strip(),
            lang=str(extend.get("lang") or "").strip(),
            res=str(extend.get("res") or "").strip(),
            page=page,
        )
        html = self._get(url)
        vods = self._parse_items(html)
        return {
            "page": page,
            "pagecount": self._page_count(html, page) if vods else page,
            "limit": PAGE_SIZE,
            "total": len(vods),
            "list": vods[:PAGE_SIZE] if len(vods) > PAGE_SIZE else vods,
        }

    def _ai_category(self, page):
        items = self._ai_list()
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

    # ---------------------------------------------------------------- 详情
    def detailContent(self, ids):
        vid = str(ids[0] if isinstance(ids, list) else ids or "").strip()
        if not vid:
            return {"list": []}
        try:
            return self._detail(vid)
        except Exception as exc:
            print("红果详情读取失败:", exc)
            return {"list": []}

    def _detail(self, vid):
        html = self._get("/voddetail/%s.html" % vid)
        if not html:
            return {"list": []}

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
                pic = self._base() + pic

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

        sid, count = self._episodes(vid, html)
        if count <= 1:
            urls = ["全集$%s|%s|1" % (vid, sid)]
        else:
            urls = ["第%d集$%s|%s|%d" % (i, vid, sid, i) for i in range(1, count + 1)]

        return {"list": [{
            "vod_id": vid,
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

    # ---------------------------------------------------------------- 搜索
    def searchContent(self, key, quick, pg="1"):
        page = self._safe_int(pg, 1)
        kw = str(key or "").strip()
        if not kw or page > 1:
            return {"page": page, "pagecount": page, "limit": PAGE_SIZE, "total": 0, "list": []}
        try:
            items = self._suggest_list(kw)
        except Exception as exc:
            print("红果搜索失败:", exc)
            items = []
        return {"page": page, "pagecount": page, "limit": PAGE_SIZE, "total": len(items), "list": items}

    # ---------------------------------------------------------------- 播放
    def playerContent(self, flag, pid, vipFlags):
        raw = str(pid or "")
        if "$" in raw:
            raw = raw.split("$", 1)[1]
        parts = raw.split("|")
        if len(parts) >= 3:
            vid, sid, n = parts[0].strip(), (parts[1].strip() or "1"), parts[2].strip()
        else:
            vid, sid, n = raw.strip(), "1", "1"

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
                "header": {"User-Agent": UA, "Referer": self._base() + "/"},
                "jx": 0,
            }
        return {
            "parse": 1,
            "playUrl": "",
            "url": "%s/vodplay/%s-%s-%s.html" % (self._base(), vid, sid, n),
            "header": {"User-Agent": UA, "Referer": self._base() + "/"},
        }

    # ---------------------------------------------------------------- AI 列表
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
            for vod in self._suggest_list(kw):
                add(vod)
        for seed in SEED_AI:
            core = self._norm(seed)[:4]
            for vod in self._suggest_list(seed):
                if core and core in self._norm(vod.get("vod_name") or ""):
                    add(vod)
                    break

        self._ai_cache = (now, items)
        return items

    # ---------------------------------------------------------------- 聚合站
    def _base(self):
        return getattr(self, "_host", HOSTS[0]) or HOSTS[0]

    def _host_order(self):
        cur = self._base()
        return [cur] + [h for h in HOSTS if h != cur]

    def _get(self, path, ajax=False):
        path = str(path or "")
        if path.startswith("http"):
            return self._fetch(path, ajax)[1]
        cached = self._cache.get(path)
        if cached and time.time() - cached[0] < 300:
            return cached[1]
        text = ""
        for _round in range(2):
            for base in self._host_order():
                status, body = self._fetch(base + path, ajax)
                if status == 200 and body and not self._is_blocked(status, body):
                    self._host = base
                    text = body
                    break
            if text:
                break
            time.sleep(0.25)
        self._cache[path] = (time.time(), text)
        return text

    def _fetch(self, url, ajax=False):
        base = "/".join(url.split("/", 3)[:3]) or self._base()
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
            print("红果请求失败:", url, exc)
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

    def _suggest_list(self, wd):
        wd = str(wd or "").strip()
        if not wd:
            return []
        text = self._get("/index.php/ajax/suggest?" + urlencode({"mid": 1, "wd": wd}), ajax=True)
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
                    pic = self._base() + pic
            out.append({
                "vod_id": vid,
                "vod_name": (it.get("name") or "").strip(),
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
                    pic = self._base() + pic

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

    def _episodes(self, vid, html):
        if not html:
            html = self._get("/voddetail/%s.html" % vid)
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
            if isinstance(url, str) and ";" in url:
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

    def _build_filters(self):
        def group(key, name, values):
            return {"key": key, "name": name,
                    "value": [{"n": "全部", "v": ""}] + [{"n": v, "v": v} for v in values]}
        real = [
            group("genre", "题材", GENRES),
            group("year", "年份", YEARS),
            group("lang", "语言", LANGS),
            group("res", "资源", RESES),
        ]
        return {"real": real, "ai": []}

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
