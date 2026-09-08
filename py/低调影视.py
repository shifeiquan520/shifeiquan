# -*- coding: utf-8 -*-
import json
import re
import requests
from base.spider import Spider


class Spider(Spider):

    def init(self, extend=""):
        self.host = "https://ddys.io"
        self.api = f"{self.host}/api/v1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": f"{self.host}/",
        }

    def getName(self):
        return "低端影视"

    def isVideoFormat(self, url):
        return ".m3u8" in url or ".mp4" in url

    def manualVideoCheck(self):
        return False

    def action(self, action):
        pass

    def destroy(self):
        pass

    def _get(self, path, params=None):
        try:
            url = f"{self.api}{path}"
            r = requests.get(url, headers=self.headers, params=params, timeout=10, verify=False)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print(f"[低端影视] _get error: {path} - {e}")
        return None

    def homeContent(self, filter):
        result = {"class": [], "filters": {}, "list": []}

        # 获取分类
        data = self._get("/types")
        if data and data.get("success"):
            for t in data.get("data", []):
                result["class"].append({
                    "type_id": t["code"],
                    "type_name": t["name"],
                })

        # 获取地区字典
        regions = []
        reg_data = self._get("/regions")
        if reg_data and reg_data.get("success"):
            regions = reg_data.get("data", [])

        # 获取题材字典
        genres = []
        gen_data = self._get("/genres")
        if gen_data and gen_data.get("success"):
            genres = gen_data.get("data", [])

        # 构造筛选条件
        for cls in result["class"]:
            tid = cls["type_id"]
            filters = [
                {
                    "key": "region",
                    "name": "地区",
                    "value": [{"n": "全部", "v": ""}] + [{"n": r["name"], "v": r["code"]} for r in regions],
                },
                {
                    "key": "genre",
                    "name": "题材",
                    "value": [{"n": "全部", "v": ""}] + [{"n": g["name"], "v": g["code"]} for g in genres],
                },
                {
                    "key": "sort",
                    "name": "排序",
                    "value": [
                        {"n": "最新", "v": "latest"},
                        {"n": "评分", "v": "rating"},
                        {"n": "最热", "v": "popular"},
                    ],
                },
            ]
            result["filters"][tid] = filters

        # 首页推荐
        home_data = self._get("/movies", {"type": "movie", "sort": "latest", "page": 1, "per_page": 24})
        if home_data and home_data.get("success"):
            result["list"] = self._parse_list(home_data.get("data", []))

        return result

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        params = {
            "type": tid,
            "page": pg,
            "per_page": 24,
        }
        if extend:
            if extend.get("region"):
                params["region"] = extend["region"]
            if extend.get("genre"):
                params["genre"] = extend["genre"]
            if extend.get("sort"):
                params["sort"] = extend["sort"]

        data = self._get("/movies", params)
        videos = []
        total_pages = 999
        if data and data.get("success"):
            videos = self._parse_list(data.get("data", []))
            meta = data.get("meta", {})
            total_pages = meta.get("total_pages", 999)

        return {
            "list": videos,
            "page": int(pg),
            "pagecount": total_pages,
            "limit": 24,
            "total": 99999,
        }

    def detailContent(self, ids):
        slug = ids[0] if ids else ""
        if not slug:
            return {"list": []}

        # 获取详情
        detail = self._get(f"/movies/{slug}")
        if not detail or not detail.get("success"):
            return {"list": []}

        m = detail["data"]
        director = m.get("director", "")
        if isinstance(director, list):
            director = ", ".join(director)
        actors = m.get("actors", "")
        if isinstance(actors, list):
            actors = ", ".join(actors)
        intro = m.get("intro", "")
        intro = re.sub(r'<[^>]+>', '', intro)
        vod = {
            "vod_id": m.get("slug", slug),
            "vod_name": m.get("title", ""),
            "vod_pic": m.get("poster", ""),
            "vod_year": str(m.get("year", "")),
            "vod_area": m.get("region", ""),
            "vod_director": director,
            "vod_actor": actors,
            "vod_content": intro,
            "vod_remarks": str(m.get("rating", "")),
        }

        # 获取播放资源
        sources = self._get(f"/movies/{slug}/sources")
        sdata = {}
        play_from = []
        play_url = []
        if sources and sources.get("success"):
            sdata = sources["data"]
            online = sdata.get("online", [])
            for src in online:
                name = src.get("source_name", src.get("name", "默认"))
                url = src.get("url", "")
                if url:
                    play_from.append(name)
                    play_url.append(url)

        if not play_url:
            download = sdata.get("download", [])
            for src in download:
                name = src.get("source_name", src.get("name", "下载"))
                url = src.get("url", "")
                if url:
                    play_from.append(name)
                    play_url.append(url)

        vod["vod_play_from"] = "$$$".join(play_from) if play_from else "默认"
        vod["vod_play_url"] = "$$$".join([f"{play_from[i]}${play_url[i]}" for i in range(len(play_url))]) if play_url else ""

        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        params = {
            "q": key,
            "type": "movie",
            "page": pg,
            "per_page": 20,
        }
        data = self._get("/search", params)
        videos = []
        if data and data.get("success"):
            videos = self._parse_list(data.get("data", []))
        return {"list": videos, "page": int(pg)}

    def playerContent(self, flag, id, vipFlags):
        result = {
            "parse": 0,
            "url": id,
            "header": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Referer": f"{self.host}/",
            },
        }
        return result

    def localProxy(self, param):
        pass

    def _parse_list(self, items):
        videos = []
        for m in items:
            videos.append({
                "vod_id": m.get("slug", ""),
                "vod_name": m.get("title", ""),
                "vod_pic": m.get("poster", ""),
                "vod_remarks": m.get("rating", "") or m.get("year", ""),
            })
        return videos
