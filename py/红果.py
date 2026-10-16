# coding=utf-8
# !/usr/bin/python
"""
红果短剧 TVBox / OK影视 / 影视仓 Python 源（混合版 2026）。

数据层：官方 https://hongguoduanju.com
- /category 忽略 query，仅路径 /category/{type}[/{slug}] 生效；分页用 ?page=N。
- 内容类型：real-drama 真人剧、comic-drama 漫剧、ai-drama AI剧、comic 漫画。
- 首页 loaderData.page.homeSections 内为分组 video_list（字段 series_title）。
- 列表 /category 的 recommendList 字段是 series_name。
- 详情 /detail?series_id= 内 seriesDetail 含 vid_list / episode_cnt / accessible_episode_cnt。

播放层：官方免费集优先，超出免费集用聚合站补全集
- 官方受保护播放接口：POST /api/video/protected/play-info（免费集返回签名直链，超出即 403）。
- 聚合站（苹果CMS/conch，hongguoapp.cn）：按剧名解析出全集直连 m3u8（AES-128 HLS）。
- 全失败回退 parse=1，交给 OK影视/影视仓 通用解析。

搜索：官方 suggestion 优先 → 聚合站 → 本地池。
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


CATEGORIES = [
    ("real-drama", "真人剧", "/category/real-drama"),
    ("comic-drama", "漫剧", "/category/comic-drama"),
    ("ai-drama", "AI剧", "/category/ai-drama"),
    ("comic", "漫画", "/category/comic"),
]
CATEGORY_MAP = {tid: path for tid, _name, path in CATEGORIES}

STATIC_TOPICS = {
    "real-drama": [
        {"n": "爱情", "v": "romance"}, {"n": "年代", "v": "period"},
        {"n": "逆袭", "v": "comeback"}, {"n": "传奇", "v": "legend"},
        {"n": "成长", "v": "growth"}, {"n": "家庭", "v": "family"},
        {"n": "家族", "v": "clan"}, {"n": "萌宝", "v": "cute-kids"},
        {"n": "悬疑", "v": "suspense"}, {"n": "惊悚", "v": "thriller"},
        {"n": "恐怖", "v": "horror"}, {"n": "志怪", "v": "supernatural"},
        {"n": "古装", "v": "costume"}, {"n": "玄幻", "v": "fantasy"},
        {"n": "奇幻", "v": "wonder"}, {"n": "都市", "v": "urban"},
        {"n": "青春", "v": "youth"}, {"n": "喜剧", "v": "comedy"},
        {"n": "科幻", "v": "sci-fi"}, {"n": "灾难", "v": "disaster"},
        {"n": "动作冒险", "v": "action-adventure"}, {"n": "战争", "v": "war"},
        {"n": "综艺", "v": "variety"}, {"n": "剧情", "v": "drama"},
    ],
    "comic-drama": [
        {"n": "脑洞", "v": "creative"}, {"n": "玄幻", "v": "fantasy"},
        {"n": "剧情", "v": "drama"}, {"n": "末世", "v": "apocalypse"},
        {"n": "豪门", "v": "wealthy-family"}, {"n": "奇幻", "v": "wonder"},
        {"n": "科幻", "v": "sci-fi"}, {"n": "冒险", "v": "adventure"},
    ],
    "ai-drama": [
        {"n": "脑洞", "v": "creative"}, {"n": "玄幻", "v": "fantasy"},
        {"n": "剧情", "v": "drama"}, {"n": "末世", "v": "apocalypse"},
        {"n": "豪门", "v": "wealthy-family"}, {"n": "奇幻", "v": "wonder"},
        {"n": "科幻", "v": "sci-fi"}, {"n": "冒险", "v": "adventure"},
    ],
    "comic": [],
}

UA = ("Mozilla/5.0 (Linux; Android 12; TV) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# 聚合站（苹果CMS / conch 模板），按剧名解析全集 m3u8
AGG_HOST = "https://www.hongguoapp.cn"
AGG_SEARCH = "/vodsearch/-------------.html?wd=%s"


class Spider(Spider):
    def __init__(self):
        self.host = "https://hongguoduanju.com"
        self.agg_host = AGG_HOST
        self.headers = {
            "User-Agent": UA,
            "Referer": self.host + "/",
            "Origin": self.host,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self.json_headers = {
            "User-Agent": UA,
            "Referer": self.host + "/",
            "Origin": self.host,
            "X-Xs-From-Web": "1",
            "Accept": "application/json, text/plain, */*",
        }
        self.agg_headers = {
            "User-Agent": UA,
            "Referer": self.agg_host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self.timeout = 20
        self.page_size = 24
        self._cache = {}
        self._agg_cache = {}
        self.class_list = []
        self.search_pool = []

    def getName(self):
        return "红果短剧"

    def init(self, extend=""):
        return

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        return

    # ---------------------------------------------------------------- 首页/分类
    def homeContent(self, filter):
        classes = [
            {"type_id": tid, "type_name": name}
            for tid, name, _path in CATEGORIES
        ]
        self.class_list = classes
        result = {
            "class": classes,
            "list": self.homeVideoContent().get("list", []),
        }
        if filter:
            result["filters"] = self._build_filters()
        return result

    def homeVideoContent(self):
        try:
            data = self._router_data(self.host + "/") or {}
            page = self._pick_page(data, "page")
            videos = []
            for section in page.get("homeSections") or []:
                videos.extend(section.get("video_list") or [])
            if not videos:
                videos, _pages, _size = self._category_items("/category/real-drama", 1)
            return {"list": self._vod_list(videos[:self.page_size])}
        except Exception as exc:
            print("红果首页读取失败:", exc)
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        page_num = self._safe_int(pg, 1)
        try:
            path = self._category_path(tid, extend or {})
            videos, total_pages, page_size = self._category_items(path, page_num)

            # 落地页（无题材筛选）为空时兜底：先试 ?page=1，再退到该类型首个题材
            if not videos and page_num == 1 and not self._slug_of(tid, extend or {}):
                videos, total_pages, page_size = self._category_items(path, 1, force_page=True)
            if not videos and not self._slug_of(tid, extend or {}):
                topics = self._type_topics(str(tid))
                if topics and topics[0].get("v"):
                    videos, total_pages, page_size = self._category_items(
                        path + "/" + str(topics[0]["v"]), page_num)

            pagecount = total_pages if total_pages > 0 else 1
            return {
                "page": page_num,
                "pagecount": pagecount,
                "limit": page_size if page_size > 0 else self.page_size,
                "total": len(videos),
                "list": self._vod_list(videos),
            }
        except Exception as exc:
            print("红果分类读取失败:", exc)
            return {"list": [], "page": page_num, "pagecount": page_num}

    # ---------------------------------------------------------------- 详情
    def detailContent(self, ids):
        sid = ids[0] if isinstance(ids, list) else ids
        sid = str(sid or "")
        try:
            if sid.startswith("agg:"):
                return self._agg_detail_content(sid[4:])
            return self._official_detail_content(sid)
        except Exception as exc:
            print("红果详情读取失败:", exc)
            return {"list": []}

    def _official_detail_content(self, sid):
        data = self._router_data(self.host + "/detail?series_id=" + quote(str(sid))) or {}
        page = self._pick_page(data, "detail_page")
        detail = page.get("seriesDetail") or {}
        if not detail:
            return {"list": []}

        sid = str(detail.get("series_id") or sid)
        name = detail.get("series_name") or ""
        pic = detail.get("series_cover") or ""
        intro = detail.get("series_intro") or ""
        tags = detail.get("tags") or []

        actors = []
        for item in detail.get("celebrities") or []:
            actor = item.get("nickname") or ""
            role = item.get("sub_title") or ""
            if actor:
                actors.append(actor + ((" " + role) if role else ""))

        vids = [str(x) for x in (detail.get("vid_list") or []) if str(x)]
        total = self._safe_int(detail.get("episode_cnt") or len(vids), len(vids))
        accessible = self._safe_int(detail.get("accessible_episode_cnt") or 0, 0)
        if accessible <= 0 or accessible > len(vids):
            accessible = len(vids)

        # 聚合站补全集：按剧名解析出 vod_id / 播放源 / 集数
        agg = self._agg_resolve(name)
        play_urls = []
        if agg and agg[2]:
            agg_id, agg_src, agg_count = agg
            count = agg_count or total or len(vids)
            for i in range(1, count + 1):
                vid = vids[i - 1] if i <= len(vids) else ""
                pid = self._make_pid(sid, vid, agg_id, agg_src, i, name)
                play_urls.append("第%d集$%s" % (i, pid))
            remark = "全%d集" % count
        else:
            for i in range(1, accessible + 1):
                pid = self._make_pid(sid, vids[i - 1], "", "", i, name)
                play_urls.append("第%d集$%s" % (i, pid))
            remark = ("可播%d集/全%d集" % (accessible, total)) if total else ""

        tag_text = " / ".join([str(x) for x in tags[:4]]) if isinstance(tags, list) else str(tags)
        vod = {
            "vod_id": sid,
            "vod_name": name,
            "vod_pic": pic,
            "type_name": tag_text,
            "vod_year": "",
            "vod_area": "大陆",
            "vod_remarks": remark,
            "vod_actor": " / ".join(actors),
            "vod_director": "",
            "vod_content": intro,
            "vod_play_from": "红果短剧",
            "vod_play_url": "#".join(play_urls),
        }
        return {"list": [vod]}

    def _agg_detail_content(self, agg_id):
        info = self._agg_detail(agg_id)
        if not info:
            return {"list": []}
        name = info.get("name") or ("红果短剧%s" % agg_id)
        src = info.get("sid") or "1"
        count = self._safe_int(info.get("ep_count"), 0)
        play_urls = []
        for i in range(1, count + 1):
            pid = self._make_pid("", "", agg_id, src, i, name)
            play_urls.append("第%d集$%s" % (i, pid))
        vod = {
            "vod_id": "agg:" + str(agg_id),
            "vod_name": name,
            "vod_pic": info.get("cover") or "",
            "type_name": info.get("type_name") or "",
            "vod_year": "",
            "vod_area": "大陆",
            "vod_remarks": ("全%d集" % count) if count else "",
            "vod_actor": info.get("actor") or "",
            "vod_director": "",
            "vod_content": info.get("intro") or "",
            "vod_play_from": "红果短剧",
            "vod_play_url": "#".join(play_urls),
        }
        return {"list": [vod]}

    # ---------------------------------------------------------------- 搜索
    def searchContent(self, key, quick, pg="1"):
        page_num = self._safe_int(pg, 1)
        keyword = str(key or "").strip()
        if not keyword:
            return {"page": page_num, "pagecount": 1, "limit": self.page_size, "total": 0, "list": []}

        # 1) 官方 suggestion
        try:
            res = self._official_search(keyword, page_num)
            if res and res.get("list"):
                return res
        except Exception as exc:
            print("红果官方搜索失败，回退聚合:", exc)

        # 2) 聚合站
        try:
            res = self._agg_search_items(keyword, page_num)
            if res and res.get("list"):
                return res
        except Exception as exc:
            print("红果聚合搜索失败，回退本地池:", exc)

        # 3) 本地池
        return self._local_search(keyword, page_num)

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    def _official_search(self, keyword, page_num):
        url = self.host + "/incent_resource/suggestion?" + urlencode(
            {"web_id": "", "query": keyword, "count": 20})
        r = requests.get(url, headers=self.json_headers, timeout=self.timeout, verify=False)
        if r.status_code != 200:
            return None
        try:
            j = r.json()
        except Exception:
            return None
        lst = ((j or {}).get("data") or {}).get("suggest_list") or []
        items = []
        seen = set()
        for it in lst:
            sid = str(it.get("series_id") or it.get("book_id") or it.get("id") or "")
            if not sid or sid in seen:
                continue
            seen.add(sid)
            video = it.get("video_data") or {}
            items.append({
                "vod_id": sid,
                "vod_name": it.get("name") or it.get("series_name") or video.get("series_name") or "",
                "vod_pic": video.get("series_cover") or it.get("cover") or "",
                "vod_remarks": it.get("sub_title") or "",
                "vod_content": "",
            })
        return {
            "page": page_num,
            "pagecount": 1,
            "limit": self.page_size,
            "total": len(items),
            "list": items,
        }

    def _agg_search_items(self, keyword, page_num):
        found = self._agg_search(keyword)
        items = []
        for raw in found:
            if isinstance(raw, dict):
                vod_id = raw.get("vod_id")
                name = raw.get("vod_name") or ""
                pic = raw.get("vod_pic") or ""
            else:
                vod_id, name = raw[0], raw[1]
                pic = ""
            if not vod_id:
                continue
            items.append({
                "vod_id": "agg:%s" % vod_id,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": "",
                "vod_content": "",
            })
        cycle = self.page_size
        start = (page_num - 1) * cycle
        return {
            "page": page_num,
            "pagecount": 1,
            "limit": self.page_size,
            "total": len(items),
            "list": items[start:start + cycle],
        }

    def _local_search(self, keyword, page_num):
        pool = self._get_search_pool()
        matched = []
        exists = set()
        low = keyword.lower()
        for item in pool:
            sid = str(item.get("series_id") or "")
            if not sid or sid in exists:
                continue
            text = " ".join([
                str(item.get("series_name") or item.get("series_title") or ""),
                str(item.get("series_intro") or ""),
                " ".join([str(x) for x in (item.get("tags") or [])]),
            ]).lower()
            if low in text:
                matched.append(item)
                exists.add(sid)
        total = len(matched)
        start = (page_num - 1) * self.page_size
        end = start + self.page_size
        return {
            "page": page_num,
            "pagecount": max(1, int(math.ceil(total / float(self.page_size)))) if total else 1,
            "limit": self.page_size,
            "total": total,
            "list": self._vod_list(matched[start:end]),
        }

    # ---------------------------------------------------------------- 播放
    def playerContent(self, flag, pid, vipFlags):
        raw = str(pid or "")
        if '$' in raw:
            raw = raw.split('$', 1)[1]

        parts = raw.split("|", 5)
        if len(parts) >= 5 and parts[4].isdigit():
            sid = parts[0].strip()
            vid = parts[1].strip()
            agg_id = parts[2].strip()
            agg_src = parts[3].strip()
            idx = parts[4].strip()
            name = parts[5].strip() if len(parts) > 5 else ""
        else:
            sid, vid = self._split_play_id(raw)
            agg_id = ""
            agg_src = ""
            idx = "1"
            name = ""
            if "|" in raw or "@@@" in raw:
                # 检测是否为旧的 "第X集$series_id|vid" 形式
                pass

        # 1) 官方免费集：受保护播放接口返回签名直链
        if sid and vid:
            url = self._official_play_url(sid, vid)
            if url:
                return {
                    "parse": 0,
                    "playUrl": "",
                    "url": url,
                    "header": {"User-Agent": UA, "Referer": self.host + "/"},
                    "jx": 0,
                }

        # 2) 聚合站（详情页已解析出 agg_id）
        if agg_id:
            url = self._agg_episode_url(agg_id, agg_src, idx)
            if url:
                return self._agg_result(url)

        # 3) 聚合站（按剧名现解析，覆盖官方详情时未命中聚合的情况）
        if name:
            agg = self._agg_resolve(name)
            if agg and agg[2] and self._safe_int(idx, 1) <= agg[2]:
                url = self._agg_episode_url(agg[0], agg[1], idx)
                if url:
                    return self._agg_result(url)

        # 4) 回退通用解析
        page_url = self.host + "/player/" + quote(sid)
        if vid:
            page_url += "/" + quote(vid)
        return {
            "parse": 1,
            "playUrl": "",
            "url": page_url,
            "header": {"User-Agent": UA, "Referer": self.host + "/"},
        }

    def _agg_result(self, url):
        return {
            "parse": 0,
            "playUrl": "",
            "url": url,
            "header": {"User-Agent": UA, "Referer": self.agg_host + "/"},
            "jx": 0,
        }

    def _official_play_url(self, sid, vid):
        try:
            body = json.dumps({
                "series_id": str(sid),
                "item_id": str(vid),
                "definition": "720p",
            })
            url = self.host + "/api/video/protected/play-info?" + urlencode({"aid": 8662})
            headers = dict(self.json_headers)
            headers["Content-Type"] = "application/json"
            r = requests.post(url, data=body, headers=headers, timeout=self.timeout, verify=False)
            if r.status_code != 200:
                return ""
            j = r.json()
            info = j.get("play_info") or j.get("legacy_play_info") or {}
            main = info.get("main_url") or ""
            if isinstance(main, str) and main.startswith("http"):
                return main
        except Exception:
            pass
        return ""

    def _make_pid(self, sid, vid, agg_id, agg_src, idx, name):
        safe_name = str(name or "").replace("|", "").replace("\n", "").replace("\t", "").strip()
        return "|".join([str(sid or ""), str(vid or ""), str(agg_id or ""),
                         str(agg_src or ""), str(idx), safe_name])

    # ---------------------------------------------------------------- 聚合站
    def _agg_get(self, path):
        url = path if path.startswith("http") else self.agg_host + path
        cached = self._cache.get(url)
        if cached and time.time() - cached[0] < 300:
            return cached[1]
        r = requests.get(url, headers=self.agg_headers, timeout=self.timeout, verify=False)
        text = r.text if r.status_code == 200 else ""
        self._cache[url] = (time.time(), text)
        return text

    def _agg_search(self, name):
        name = str(name or "").strip()
        if not name:
            return []
        html = self._agg_get(AGG_SEARCH % quote(name))
        if not html:
            return []
        found = []
        seen = set()
        for m in re.finditer(r'href="/voddetail/(\d+)\.html"[^>]*title="([^"]*)"', html):
            vod_id, title = m.group(1), m.group(2).strip()
            if vod_id not in seen:
                seen.add(vod_id)
                found.append({"vod_id": vod_id, "vod_name": title, "vod_pic": ""})
        if not found:
            for m in re.finditer(r'href="/voddetail/(\d+)\.html"[^>]*>([^<]+)</a>', html):
                vod_id, title = m.group(1), m.group(2).strip()
                if vod_id not in seen:
                    seen.add(vod_id)
                    found.append({"vod_id": vod_id, "vod_name": title, "vod_pic": ""})
        return found

    def _agg_best(self, name, found):
        if not found:
            return None
        target = self._norm_name(name)
        for item in found:
            if self._norm_name(item["vod_name"]) == target:
                return item
        for item in found:
            vn = self._norm_name(item["vod_name"])
            if target and (target in vn or vn in target):
                return item
        return found[0]

    def _agg_detail(self, agg_id):
        html = self._agg_get("/voddetail/%s.html" % agg_id)
        if not html:
            return None
        srcs = re.findall(r'/vodplay/%s-(\d+)-(\d+)\.html' % re.escape(str(agg_id)), html)
        if not srcs:
            return None
        sid = srcs[0][0]
        max_ep = 0
        for row in srcs:
            if row[0] == sid:
                max_ep = max(max_ep, self._safe_int(row[1], 0))

        name = ""
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        if m:
            name = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if not name:
            m = re.search(r'<title>(.*?)</title>', html, re.S)
            if m:
                name = re.split(r'[－\-_|]', m.group(1).strip())[0].strip()
        name = self._clean_agg_name(name)

        cover = ""
        m = re.search(r'(?:data-original|data-src|src)="([^"]+\.(?:jpg|jpeg|png|webp))"', html)
        if m:
            cover = m.group(1)
            if cover.startswith("/"):
                cover = self.agg_host + cover

        intro = ""
        m = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]*)"', html)
        if m:
            intro = m.group(1).strip()

        return {
            "name": name,
            "cover": cover,
            "intro": intro,
            "sid": sid,
            "ep_count": max_ep,
        }

    def _agg_resolve(self, name):
        name = str(name or "").strip()
        if not name:
            return None
        if name in self._agg_cache:
            return self._agg_cache[name]
        res = None
        try:
            found = self._agg_search(name)
            best = self._agg_best(name, found)
            if best:
                info = self._agg_detail(best["vod_id"])
                if info and info.get("ep_count"):
                    res = (best["vod_id"], info.get("sid") or "1", info.get("ep_count"))
        except Exception as exc:
            print("红果聚合解析失败:", exc)
        self._agg_cache[name] = res
        return res

    def _agg_episode_url(self, agg_id, sid, idx):
        sid = str(sid or "1")
        idx = str(self._safe_int(idx, 1))
        html = self._agg_get("/vodplay/%s-%s-%s.html" % (agg_id, sid, idx))
        return self._extract_m3u8(html)

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

    def _clean_agg_name(self, name):
        name = str(name or "").strip()
        name = re.sub(r'(短剧)?高清完整版(在线观看|免费观看|下载)?$', '', name).strip()
        name = re.sub(r'(在线观看|免费观看|全集)$', '', name).strip()
        name = name.strip("《》").strip()
        return name

    def _norm_name(self, name):
        return re.sub(r'[\s，,。.、！!？?：:·\-—_/\\()（）\[\]【】"\'’“”]+', '', str(name or ""))

    # ---------------------------------------------------------------- 通用
    def localProxy(self, params):
        return [404, "text/plain", "not found"]

    def _router_data(self, url):
        cached = self._cache.get(url)
        if cached and time.time() - cached[0] < 300:
            return cached[1]

        response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=False)
        response.raise_for_status()
        response.encoding = "utf-8"

        text = response.text
        m = re.search(r"_ROUTER_DATA\s*=\s*", text)
        if not m:
            return {}
        start = m.end()
        brace_count = 0
        in_string = False
        escape = False
        end = start
        for i, ch in enumerate(text[start:], start):
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"' and not escape:
                in_string = not in_string
                continue
            if not in_string:
                if ch == "{":
                    brace_count += 1
                elif ch == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
        json_str = text[start:end]
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return {}
        self._cache[url] = (time.time(), data)
        return data

    def _pick_page(self, router_data, preferred):
        loader = (router_data or {}).get("loaderData") or {}
        if isinstance(loader.get(preferred), dict):
            return loader.get(preferred) or {}

        content_keys = ("recommendList", "selectorList", "videoList", "seriesDetail", "homeSections")
        for value in loader.values():
            if isinstance(value, dict) and any(k in value for k in content_keys):
                return value

        for key, value in loader.items():
            if isinstance(value, dict) and key.endswith("/page"):
                return value
        for value in loader.values():
            if isinstance(value, dict):
                return value
        return {}

    def _build_filters(self):
        filters = {}
        for tid, _name, _path in CATEGORIES:
            topics = self._type_topics(tid)
            if topics:
                filters[tid] = [{
                    "key": "topic",
                    "name": "分类",
                    "value": [{"n": "全部", "v": ""}] + topics,
                }]
            else:
                filters[tid] = []
        return filters

    def _type_topics(self, tid):
        try:
            data = self._router_data(self.host + "/category/" + str(tid)) or {}
            page = self._pick_page(data, "category_page")
            topics = []
            for row in page.get("selectorList") or []:
                for item in row.get("items") or []:
                    n = item.get("show_name")
                    v = item.get("selector_item_id")
                    if n and v is not None:
                        topics.append({"n": str(n), "v": str(v)})
            if topics:
                return topics
        except Exception:
            pass
        return STATIC_TOPICS.get(str(tid), [])

    def _slug_of(self, tid, extend):
        tid = str(tid or "")
        data = extend if isinstance(extend, dict) else {}
        slug = ""
        for key in ("topic", "background", "category"):
            value = data.get(key)
            if value is not None and str(value) != "":
                slug = str(value).strip()
                break

        if not slug and tid not in CATEGORY_MAP and tid not in ("", "all"):
            slug = tid

        if slug.startswith("cate_"):
            slug = slug[len("cate_"):]
        if slug and not re.match(r"^[A-Za-z0-9_-]+$", slug):
            slug = ""
        return slug

    def _category_path(self, tid, extend):
        tid = str(tid or "")
        base = CATEGORY_MAP.get(tid, CATEGORY_MAP["real-drama"])
        slug = self._slug_of(tid, extend)
        return base + (("/" + slug) if slug else "")

    def _category_items(self, path, page=1, force_page=False):
        url = self.host + (path or "/category/real-drama")
        page = self._safe_int(page, 1)
        if page > 1 or force_page:
            url += "?" + urlencode({"page": page})

        data = self._router_data(url) or {}
        page_data = self._pick_page(data, "category_page")
        items = page_data.get("recommendList") or []
        if not items:
            category_data = page_data.get("categoryData") or {}
            if isinstance(category_data, dict):
                items = category_data.get("recommendList") or []

        pagination = page_data.get("pagination") or {}
        total_pages = self._safe_int(pagination.get("totalPages"), 0)
        page_size = self._safe_int(pagination.get("pageSize"), 0)

        seen = set()
        result = []
        for item in items:
            sid = str(item.get("series_id") or "")
            if sid and sid not in seen:
                seen.add(sid)
                result.append(item)
        return result, total_pages, page_size

    def _vod_list(self, videos):
        result = []
        for item in videos or []:
            sid = str(item.get("series_id") or "")
            if not sid:
                continue

            tags = item.get("tags") or []
            tag_text = " / ".join([str(x) for x in tags[:2]]) if isinstance(tags, list) else str(tags)
            remark = item.get("episode_right_text") or ""
            if not remark:
                count = item.get("episode_cnt") or len(item.get("vid_list") or [])
                remark = ("全%s集" % count) if count else tag_text
            elif tag_text:
                remark = remark + " · " + tag_text

            result.append({
                "vod_id": sid,
                "vod_name": item.get("series_name") or item.get("series_title") or "",
                "vod_pic": (
                    item.get("series_cover")
                    or item.get("background_cover")
                    or item.get("background_cover_mobile")
                    or ""
                ),
                "vod_remarks": remark,
                "vod_content": item.get("series_intro") or "",
            })
        return result

    def _get_search_pool(self):
        if self.search_pool:
            return self.search_pool

        pool = []
        seen = set()

        def add(items):
            for item in items or []:
                sid = str(item.get("series_id") or "")
                if sid and sid not in seen:
                    seen.add(sid)
                    pool.append(item)

        try:
            data = self._router_data(self.host + "/") or {}
            page = self._pick_page(data, "page")
            for section in page.get("homeSections") or []:
                add(section.get("video_list") or [])
        except Exception:
            pass

        for _tid, _name, path in CATEGORIES:
            for page_no in (1, 2, 3):
                url = self.host + path + (("?page=" + str(page_no)) if page_no > 1 else "")
                try:
                    data = self._router_data(url) or {}
                    page_data = self._pick_page(data, "category_page")
                    add(page_data.get("recommendList") or [])
                except Exception:
                    pass

        self.search_pool = pool
        return pool

    def _split_play_id(self, play_id):
        raw = str(play_id or "")
        if "@@@" in raw:
            sid, vid = raw.split("@@@", 1)
            return sid.strip(), vid.strip()
        parts = raw.strip("/").split("/")
        if len(parts) >= 2 and parts[-2].isdigit():
            return parts[-2], parts[-1]
        if parts and parts[-1].isdigit():
            return parts[-1], ""
        return raw, ""

    def _safe_int(self, value, default=0):
        try:
            return int(value)
        except Exception:
            return default
