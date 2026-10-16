# coding=utf-8
# !/usr/bin/python
"""
红果短剧 TVBox / OK影视 / 影视仓 Python 源。

站点说明（2026 实测）：
- /category 会忽略所有 query 参数，只有路径 /category/{type}[/{slug}] 才生效。
- 内容类型：real-drama 真人剧、comic-drama 漫剧、ai-drama AI剧、comic 漫画。
- 分页参数为 ?page=N（pg 无效）。
- 首页 loaderData.page.homeSections 内为多组 video_list（字段是 series_title）。
- 列表 /category 的 recommendList 字段是 series_name。
- 播放页为受保护播放（protectedPlayback），SSR 无 main_url，只能回退 parse=1 走通用解析。

合并优化点：
1. 4 个内容类型作为一级分类，题材筛选动态读取官网 selectorList。
2. 分类一律使用路径式 URL，分页用 page 参数，避免各分类显示同一份数据。
3. 播放直链失败时回退 parse=1，交给 OK影视/影视仓 通用解析。
4. 只展示官网网页端当前可访问的集数，避免未开放集数点开 404 黑屏。
"""

import json
import math
import re
import sys
import time
from urllib.parse import quote, urlencode

import requests

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


class Spider(Spider):
    def __init__(self):
        self.host = "https://hongguoduanju.com"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 12; TV) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            ),
            "Referer": self.host + "/",
            "Origin": self.host,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self.timeout = 20
        self.page_size = 24
        self._cache = {}
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

    def detailContent(self, ids):
        sid = ids[0] if isinstance(ids, list) else ids
        try:
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
            accessible_count = self._safe_int(detail.get("accessible_episode_cnt") or 0, 0)
            if accessible_count <= 0 or accessible_count > len(vids):
                accessible_count = len(vids)

            playable_vids = vids[:accessible_count]
            play_urls = [
                "第%s集$%s|%s" % (index, sid, vid)
                for index, vid in enumerate(playable_vids, 1)
            ]

            tag_text = " / ".join([str(x) for x in tags[:4]]) if isinstance(tags, list) else str(tags)
            remark = "可播%s集/全%s集" % (len(playable_vids), total) if total else ""

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
                "vod_play_from": "红果直连",
                "vod_play_url": "#".join(play_urls),
            }
            return {"list": [vod]}
        except Exception as exc:
            print("红果详情读取失败:", exc)
            return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        page_num = self._safe_int(pg, 1)
        keyword = str(key or "").strip().lower()
        if not keyword:
            return {"list": [], "page": page_num}

        try:
            pool = self._get_search_pool()
            matched = []
            exists = set()
            for item in pool:
                sid = str(item.get("series_id") or "")
                if not sid or sid in exists:
                    continue
                text = " ".join([
                    str(item.get("series_name") or item.get("series_title") or ""),
                    str(item.get("series_intro") or ""),
                    " ".join([str(x) for x in (item.get("tags") or [])]),
                ]).lower()
                if keyword in text:
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
        except Exception as exc:
            print("红果搜索失败:", exc)
            return {"list": [], "page": page_num}

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    def playerContent(self, flag, pid, vipFlags):
        # 处理 "第X集$series_id|vid" 格式
        play_id = str(pid or "")
        if '$' in play_id:
            play_id = play_id.split('$', 1)[1]

        sid, vid = self._split_play_id(play_id)
        if not sid:
            return {"parse": 1, "playUrl": "", "url": str(pid or "")}

        page_url = self.host + "/player/" + quote(sid)
        if vid:
            page_url += "/" + quote(vid)

        try:
            data = self._router_data(page_url) or {}
            info = self._first_value_by_key(data.get("loaderData") or {}, "video_player_info") or {}
            play_url = str(info.get("main_url") or info.get("backup_url") or "")
            poster = str(info.get("poster_url") or "")

            if play_url:
                return {
                    "parse": 0,
                    "playUrl": "",
                    "url": play_url,
                    "header": {
                        "User-Agent": self.headers["User-Agent"],
                        "Referer": page_url,
                        "Origin": self.host,
                    },
                    "jx": 0,
                    "pic": poster,
                }
        except Exception as exc:
            print("红果直链解析失败，尝试通用解析:", exc)

        # 站点已改为受保护播放（protectedPlayback），SSR 不再提供直链，回退通用解析
        return {
            "parse": 1,
            "playUrl": "",
            "url": page_url,
            "header": {
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.host + "/",
            },
        }

    def localProxy(self, params):
        return [404, "text/plain", "not found"]

    def _router_data(self, url):
        cached = self._cache.get(url)
        if cached and time.time() - cached[0] < 300:
            return cached[1]

        response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=False)
        response.raise_for_status()
        response.encoding = "utf-8"

        # 站点用 _ROUTER_DATA = {...}; 需匹配平衡的大括号，避免贪婪/非贪婪截断
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
            data = self._router_data(self.host + "/category/" + tid) or {}
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
        return STATIC_TOPICS.get(tid, [])

    def _category_path(self, tid, extend):
        tid = str(tid or "")
        if tid in CATEGORY_MAP:
            base = CATEGORY_MAP[tid]
        elif re.match(r"^[A-Za-z0-9_-]+$", tid) and tid not in ("", "home", "all"):
            base = CATEGORY_MAP["real-drama"]
        else:
            base = CATEGORY_MAP["real-drama"]

        data = extend if isinstance(extend, dict) else {}
        slug = ""
        for key in ("topic", "background", "category"):
            value = data.get(key)
            if value is not None and str(value) != "":
                slug = str(value).strip()
                break

        if not slug and tid not in CATEGORY_MAP and re.match(r"^[A-Za-z0-9_-]+$", tid):
            slug = tid

        if slug.startswith("cate_"):
            slug = slug[len("cate_"):]
        if slug and not re.match(r"^[A-Za-z0-9_-]+$", slug):
            slug = ""

        return base + (("/" + slug) if slug else "")

    def _category_items(self, path, page=1):
        url = self.host + (path or "/category/real-drama")
        page = self._safe_int(page, 1)
        if page > 1:
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
        if "|" in raw:
            sid, vid = raw.split("|", 1)
            return sid.strip(), vid.strip()
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

    def _first_value_by_key(self, obj, target_key):
        if isinstance(obj, dict):
            if target_key in obj:
                return obj.get(target_key)
            for value in obj.values():
                found = self._first_value_by_key(value, target_key)
                if found is not None:
                    return found
        elif isinstance(obj, list):
            for value in obj:
                found = self._first_value_by_key(value, target_key)
                if found is not None:
                    return found
        return None
