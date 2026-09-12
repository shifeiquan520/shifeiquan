# -*- coding: utf-8 -*-
"""
综合采集 - 多源聚合影视源（重构版）
支持：热配置、源健康检测、缓存、线程池管理、分类别名、分页修复
"""

import json
import re
import time
import warnings
import concurrent.futures
from threading import Lock
from urllib.parse import unquote

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
        pass




# ========================= 可热更新配置 =========================
DEFAULT_CFG = {
    # 请求与并发
    "timeout": 8,
    "aux_timeout": 6,
    "max_workers": 16,
    "max_retries": 2,
    "search_result_limit": 100,
    "search_sources": 15,
    "line_batch": 8,
    "cache_ttl": 300,          # 秒

    # 协议/链接
    "allow_non_direct": True,   # True=兜底 parse=1
    "direct_exts": [".m3u8", ".mp4", ".flv", ".ts"],

    # 源管理
    "source_max_failures": 5,        # 连续失败几次标记为死源
    "auto_disable_dead": True,
    "max_latency_ms": 0,           # 延迟超过此值的源不参与请求（ms），0=不限制

# 分类别名映射（可在 extend 追加/覆盖）
    "category_aliases": {
        # 短剧
        "短剧": "短剧", "AI漫剧": "短剧",

        # 电影
        "动作片": "电影", "喜剧片": "电影", "爱情片": "电影",
        "科幻片": "电影", "恐怖片": "电影", "剧情片": "电影",
        "战争片": "电影", "犯罪片": "电影", "悬疑片": "电影",
        "奇幻片": "电影", "冒险片": "电影",

        # 国产剧
        "国产剧": "国产剧", "大陆剧": "国产剧", "海外剧": "国产剧",

        # 港台剧
        "港台剧": "港台剧", "香港剧": "港台剧", "台湾剧": "港台剧",

        # 动漫
        "国产动漫": "动漫", "日韩动漫": "动漫", "欧美动漫": "动漫",

        # 综艺
        "大陆综艺": "综艺", "港台综艺": "综艺",
        "日韩综艺": "综艺", "欧美综艺": "综艺",

        # 日韩剧
        "日韩剧": "日韩剧", "韩国剧": "日韩剧", "日本剧": "日韩剧",

        # 欧美剧
        "欧美剧": "欧美剧", "美剧": "欧美剧", "英剧": "欧美剧",

        # 伦理片（补充细分）
        "伦理片": "伦理片",
        "日韩伦理": "伦理片",
        "三级伦理": "伦理片",
        "三级片": "伦理片",
        "大陆伦理": "伦理片",
    },

    # 源列表（硬编码固定源）
    "sources": [
        {"key": "cj.lziapi.com", "name": "量子", "api": "https://cj.lziapi.com/api.php/provide/vod/"},
        {"key": "api.zuidapi.com", "name": "最大资源网", "api": "https://api.zuidapi.com/api.php/provide/vod/"},
        {"key": "wujin", "name": "无尽", "api": "https://api.wujinapi.cc/api.php/provide/vod/"},
        {"key": "api.guangsuapi.com", "name": "光速资源站", "api": "https://api.guangsuapi.com/api.php/provide/vod/"},
        {"key": "api.ffzyapi.com", "name": "非凡资源网", "api": "http://api.ffzyapi.com/api.php/provide/vod/"},
        {"key": "yhzy", "name": "樱花", "api": "https://m3u8.apiyhzy.com/api.php/provide/vod/"},
        {"key": "ffzy", "name": "非凡", "api": "https://ffzy5.tv/api.php/provide/vod/"},
        {"key": "www.huyaapi.com", "name": "虎牙资源", "api": "https://www.huyaapi.com/api.php/provide/vod/"},
        {"key": "caiji.xgzyapi.com", "name": "西瓜", "api": "https://caiji.xgzyapi.com/api.php/provide/vod/"},
        {"key": "api.wujinapi.me", "name": "无尽资源网", "api": "https://api.wujinapi.me/api.php/provide/vod/"},
        {"key": "api.okzyw.net", "name": "OK资源", "api": "http://api.okzyw.net/api.php/provide/vod/"},
        {"key": "xinlang", "name": "新浪", "api": "https://api.xinlangapi.com/xinlangapi.php/provide/vod/"},
        {"key": "api.apibdzy.com", "name": "百度", "api": "https://api.apibdzy.com/api.php/provide/vod/"},
        {"key": "api.ukuapi88.com", "name": "uku资源", "api": "https://api.ukuapi88.com/api.php/provide/vod/"},
    ],
}




# ========================= 工具函数 =========================
_TAG_RE = re.compile(r'<[^>]+>')

def _clean(text):
    if not text:
        return ''
    text = _TAG_RE.sub('', str(text))
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    text = text.replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>')
    return re.sub(r'\s+', ' ', text).strip()

def _is_direct(url, allowed_exts):
    if not url:
        return False
    u = str(url).split('?')[0].lower()
    return any(u.endswith(ext) for ext in allowed_exts)

def _norm_name(s):
    s = re.sub(r'[\s·•：:，,。！？!?（）()【】\[\]]', '', _clean(s)).lower()
    return re.sub(r'(国语版|高清版|完整版|全集|正片)$', '', s)

def _same_name(a, b):
    x, y = _norm_name(a), _norm_name(b)
    return bool(x and y and (x == y or x in y or y in x))

def _category_match(a, b, aliases):
    x = _clean(a)
    y = _clean(b)
    return x == y or aliases.get(x) == y

def _is_blocked(name):
    if not name:
        return False
    n = name.lower()
    block = [
        r'番外篇?$', r'预告片?$', r'花絮$', r'幕后$',
        r'特辑$', r'先导$', r'宣传片$', r'片段$',
        r'采访$', r'制作特辑$', r'拍摄花絮$',
        r'解[说析]', r'解说版$', r'解说全集$',
        r'一口气看完', r'分钟看完', r'速看', r'详解',
    ]
    return any(re.search(p, n) for p in block)

# 全局常用分类（可通过 cfg 覆盖）
CATEGORIES = [
    '短剧', '电影', '国产剧', '港台剧', '动漫',
    '综艺', '日韩剧', '欧美剧', '伦理片'

]


# ========================= 源健康状态管理 =========================
class SourceHealth:
    __slots__ = ('key', 'failures', 'last_ok', 'disabled', 'latency_ms')

    def __init__(self, key):
        self.key = key
        self.failures = 0
        self.last_ok = 0
        self.disabled = False
        self.latency_ms = 0

    def record_ok(self, latency):
        self.failures = 0
        self.last_ok = time.time()
        self.latency_ms = latency
        self.disabled = False

    def record_fail(self):
        self.failures += 1
        self.latency_ms = 0


# ========================= 简易内存缓存 =========================
class SimpleCache:
    def __init__(self, ttl):
        self.ttl = ttl
        self._data = {}
        self._lock = Lock()

    def get(self, key):
        with self._lock:
            entry = self._data.get(key)
            if entry and time.time() - entry[0] < self.ttl:
                return entry[1]
            if entry:
                del self._data[key]
        return None

    def set(self, key, value):
        with self._lock:
            self._data[key] = (time.time(), value)

    def clear_expired(self):
        now = time.time()
        with self._lock:
            keys = [k for k, (ts, _) in self._data.items() if now - ts >= self.ttl]
            for k in keys:
                del self._data[k]


# ========================= 主 Spider =========================
class Spider(Spider):
    def getName(self):
        return '综合采集'

    def init(self, extend=''):
        # 合并配置
        self.cfg = dict(DEFAULT_CFG)
        if isinstance(extend, dict):
            self.cfg.update(extend)
        elif isinstance(extend, str) and extend:
            try:
                self.cfg.update(json.loads(extend))
            except Exception:
                pass

        # 允许通过 enabled_keys 裁剪源
        enabled = self.cfg.get('enabled_keys')
        max_ms = self.cfg.get('max_latency_ms', 0)
        if isinstance(enabled, list) and enabled:
            enabled_set = set(enabled)
            self.sources = [s for s in self.cfg['sources'] if s['key'] in enabled_set]
        else:
            self.sources = list(self.cfg['sources'])

        # 按延迟阈值过滤慢源
        if max_ms > 0:
            self.sources = [s for s in self.sources if s.get('latency_ms', 0) <= max_ms]

        # 运行时状态
        self.timeout = self.cfg['timeout']
        self.aux_timeout = self.cfg['aux_timeout']
        self.max_workers = self.cfg['max_workers']
        self.max_retries = self.cfg['max_retries']
        self.search_limit = self.cfg['search_result_limit']
        self.search_sources = self.cfg.get('search_sources', 15)
        self.allowed_exts = tuple(self.cfg['direct_exts'])
        self.allow_non_direct = self.cfg['allow_non_direct']
        self.aliases = self.cfg['category_aliases']

        # 会话（全局 verify=False）
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': UA})
        self.session.verify = False

        # 源健康
        self.health = {s['key']: SourceHealth(s['key']) for s in self.sources}
        self._health_lock = Lock()

        # 缓存
        self.cache = SimpleCache(self.cfg['cache_ttl'])

        # 线程池
        self._executor = None
        self._executor_lock = Lock()

        # 分类列表（给首页/筛选用）
        self._categories = list(CATEGORIES)

        # 分类元数据缓存（type_id 映射，TTL 3600秒）
        self._cat_meta_cache = {}
        self._cat_meta_ts = {}

        # 启动时探测所有源
        self._probe_all_sources()

    # ---------- 生命周期 ----------
    def destroy(self):
        try:
            if self._executor:
                self._executor.shutdown(wait=True, cancel_futures=True)
        except Exception:
            pass
        self._executor = None
        try:
            self.session.close()
        except Exception:
            pass

    def __del__(self):
        self.destroy()

    def _get_executor(self):
        with self._executor_lock:
            if self._executor is None:
                self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.cfg['max_workers'])
        return self._executor

    # ---------- 启动探测所有源 ----------
    def _probe_all_sources(self):
        """启动时同步探测所有源，标记不可用源"""
        def probe(src):
            key = src['key']
            try:
                t0 = time.time()
                r = self.session.get(
                    src['api'].split('?', 1)[0],
                    params={'ac': 'list', 'pg': 1},
                    timeout=self.cfg['timeout'], verify=False
                )
                latency = int((time.time() - t0) * 1000)
                if r.status_code == 200:
                    with self._health_lock:
                        self.health[key].record_ok(latency)
                else:
                    with self._health_lock:
                        self.health[key].record_fail()
            except Exception:
                with self._health_lock:
                    self.health[key].record_fail()

        executor = self._get_executor()
        futures = {executor.submit(probe, s): s for s in self.sources}
        for fut in concurrent.futures.as_completed(futures):
            try:
                fut.result(timeout=self.cfg['timeout'] + 2)
            except Exception:
                pass

        if self.cfg['auto_disable_dead']:
            with self._health_lock:
                for h in self.health.values():
                    if h.failures >= self.cfg['source_max_failures']:
                        h.disabled = True

    def _get_alive_sources(self, limit=None):
        alive = [s for s in self.sources if not self.health[s['key']].disabled]
        # 按延迟排序（低优先）
        alive.sort(key=lambda s: self.health[s['key']].latency_ms or 9999)
        if limit:
            return alive[:limit]
        return alive

    # ---------- 缓存键 ----------
    def _ck(self, *parts):
        return ':'.join(str(p) for p in parts)

    # ---------- 请求封装 ----------
    def _fetch(self, source, retry=True, timeout=None, **params):
        attempts = self.max_retries if retry else 1
        api = source['api'].split('?', 1)[0]

        for attempt in range(attempts):
            try:
                t0 = time.time()
                r = self.session.get(api, params=params,
                                     timeout=timeout or self.timeout, verify=False)
                if r.status_code == 200:
                    j = r.json()
                    if isinstance(j, dict):
                        latency = int((time.time() - t0) * 1000)
                        with self._health_lock:
                            self.health[source['key']].record_ok(latency)
                        return j
            except Exception:
                pass

        with self._health_lock:
            self.health[source['key']].record_fail()
        return None

    # ---------- 并行 ----------
    def _parallel(self, jobs, early_return=0):
        if not jobs:
            return {}
        results = {}
        executor = self._get_executor()
        futures = {}
        for k, fn in jobs:
            futures[executor.submit(fn)] = k
        for fut in concurrent.futures.as_completed(futures):
            k = futures[fut]
            try:
                results[k] = fut.result(timeout=self.timeout + 2)
            except Exception:
                results[k] = None
            if early_return and len([v for v in results.values() if v and v.get('list')]) >= early_return:
                break
        return results

    # ---------- 缓存包装 ----------
    def _cached_fetch(self, cache_key, fetch_fn):
        val = self.cache.get(cache_key)
        if val is not None:
            return val
        val = fetch_fn()
        if val is not None:
            self.cache.set(cache_key, val)
        return val

    # ---------- 条目构建 ----------
    def _item(self, vod, src_key, is_search=False):
        prefix = 'search_' if is_search else ''
        return {
            'vod_id': f"{prefix}{src_key}:{vod.get('vod_id', '')}",
            'vod_name': _clean(vod.get('vod_name', '')) or '未知影片',
            'vod_pic': vod.get('vod_pic', '') or '',
            'vod_remarks': _clean(vod.get('vod_remarks', '')) or '',
        }

# ---------- 首页 ----------
    def homeContent(self, filter):
        result = {
            'class': [{'type_id': n, 'type_name': n} for n in self._categories],
            'list': self._home_list()
        }
        if filter:
            result['filters'] = {}
        return result

    def homeVideoContent(self):
        return {'list': self._home_list()}

    def _home_list(self):
        ck = self._ck('home')
        cached = self.cache.get(ck)
        if cached is not None:
            return cached

        # 获取所有可用源（按延迟排序）
        alive = self._get_alive_sources()
        if not alive:
            return []

        # 量子源固定 + 其他最快2个
        qz_src = next((s for s in alive if s['key'] == 'cj.lziapi.com'), None)
        others = [s for s in alive if s['key'] != 'cj.lziapi.com']
        sources = [qz_src] + others[:2] if qz_src else others[:3]

        jobs = [(s['key'], lambda s=s: self._fetch(s, retry=False, timeout=self.aux_timeout,
                                                     ac='list', pg=1)) for s in sources]
        data = self._parallel(jobs)

        all_vods = []
        for s in sources:
            j = data.get(s['key'])
            if not j or not j.get('list'):
                continue
            for v in j['list'][:30]:
                all_vods.append((s['key'], v))

        all_vods.sort(key=lambda x: x[1].get('vod_time', '') or '', reverse=True)

        items = []
        seen = set()
        for src_key, v in all_vods:
            name_key = _norm_name(v.get('vod_name', ''))
            if not name_key or name_key in seen:
                continue
            seen.add(name_key)
            item = self._item(v, src_key, is_search=False)
            items.append(item)
        result = items[:30]
        self.cache.set(ck, result)
        return result

    # ---------- 分类 ----------
    def categoryContent(self, tid, pg, filter, extend):
        try:
            cat_name = unquote(str(tid or '')).strip()
            if not cat_name or ':' in cat_name or cat_name not in self._categories:
                return {'list': [], 'page': 1, 'pagecount': 0, 'limit': 20, 'total': 0}

            page = int(pg) if str(pg).isdigit() else 1
            # 获取所有可用源（按延迟排序）
            alive = self._get_alive_sources()
            if not alive:
                return {'list': [], 'page': page, 'pagecount': 0, 'limit': 20, 'total': 0}

            # 量子源固定 + 其他最快9个
            qz_src = next((s for s in alive if s['key'] == 'cj.lziapi.com'), None)
            others = [s for s in alive if s['key'] != 'cj.lziapi.com']
            sources = [qz_src] + others[:9] if qz_src else others[:10]

            # 并行拿分类数据（单次请求，利用缓存）
            jobs = []
            for s in sources:
                ck = self._ck('cat', s['key'], cat_name, pg)
                def fn(s=s, ck=ck):
                    return self._cached_fetch(ck, lambda: self._category_fetch(s, cat_name, pg))
                jobs.append((s['key'], fn))

            data = self._parallel(jobs)

            all_vods = []
            pagecount = 0
            for s in sources:
                j = data.get(s['key'])
                if not j or not j.get('list'):
                    continue
                try:
                    pagecount = max(pagecount, int(j.get('pagecount', 0) or 0))
                except Exception:
                    pass
                for vod in j['list']:
                    all_vods.append((s['key'], vod))

            all_vods.sort(key=lambda x: x[1].get('vod_time', '') or '', reverse=True)

            items = []
            seen = set()
            for src_key, vod in all_vods:
                name_key = _norm_name(vod.get('vod_name', ''))
                if not name_key or name_key in seen:
                    continue
                seen.add(name_key)
                items.append(self._item(vod, src_key, is_search=False))

            total = len(seen)
            limit = 20
            pagecount = max(pagecount, (total + limit - 1) // limit)

            return {
                'list': items,
                'page': pg,
                'pagecount': pagecount,
                'limit': limit,
                'total': total,
            }
        except Exception:
            return {'list': [], 'page': 1, 'pagecount': 0, 'limit': 20, 'total': 0}

    def _category_fetch(self, source, cat_name, pg):
        key = source['key']
        now = time.time()
        # 检查元数据缓存（TTL 3600秒）
        meta_cache = self._cat_meta_cache.get(key, {})
        meta_ts = self._cat_meta_ts.get(key, 0)
        if cat_name in meta_cache and now - meta_ts < 3600:
            src_tid = meta_cache[cat_name]
        else:
            meta = self._fetch(source, retry=False, timeout=self.aux_timeout, ac='list', pg=1)
            if not meta:
                return None
            src_tid = ''
            for item in (meta or {}).get('class', []):
                if _category_match(item.get('type_name', ''), cat_name, self.aliases):
                    src_tid = str(item.get('type_id', '')).strip()
                    break
            if not src_tid:
                return None
            # 更新缓存
            if key not in self._cat_meta_cache:
                self._cat_meta_cache[key] = {}
            self._cat_meta_cache[key][cat_name] = src_tid
            self._cat_meta_ts[key] = now
        return self._fetch(source, retry=False, timeout=self.aux_timeout,
                           ac='list', t=src_tid, pg=pg)

    # ---------- 搜索 ----------
    def searchContent(self, key, quick, pg='1'):
        try:
            page = int(pg) if str(pg).isdigit() else 1

            sources = self._get_alive_sources(self.search_sources)
            if not sources:
                return {'list': [], 'page': page}

            jobs = [(s['key'], lambda s=s: self._fetch(s, retry=False, timeout=3, ac='list', wd=key, pg=page))
                    for s in sources]
            data = self._parallel(jobs, early_return=self.search_limit)

            groups = {}
            order = []
            for s in sources:
                j = data.get(s['key'])
                if not j or not j.get('list'):
                    continue
                for v in j['list'][:3]:
                    name = _clean(v.get('vod_name', ''))
                    if not name or _is_blocked(name):
                        continue
                    type_name = _clean(v.get('type_name', ''))
                    year = str(v.get('vod_year', '') or '')
                    gk = _norm_name(name)
                    if gk not in groups:
                        groups[gk] = []
                        order.append(gk)
                    groups[gk].append((s['key'], v))

            def rank(entry):
                src_key, v = entry
                try:
                    score = float(v.get('vod_score', 0) or 0)
                except Exception:
                    score = 0.0
                remarks = _clean(v.get('vod_remarks', ''))
                bonus = 1 if any(w in remarks for w in ('完结', 'HD', '正片')) else 0
                return (bonus, score)

            result_list = []
            for gk in order:
                entries = groups[gk]
                entries.sort(key=rank, reverse=True)
                src_key, v = entries[0]
                item = self._item(v, src_key, is_search=True)
                src_name = next((s['name'] for s in self.sources if s['key'] == src_key), src_key)
                remarks = _clean(v.get('vod_remarks', ''))
                src_count = len(entries)
                if src_count > 1:
                    item['vod_remarks'] = f"{src_name} [{src_count}源] {remarks}".strip()
                else:
                    item['vod_remarks'] = f"{src_name} {remarks}".strip()
                result_list.append(item)

            if len(result_list) > self.search_limit:
                result_list = result_list[:self.search_limit]

            src_order = {s['key']: i for i, s in enumerate(self.sources)}
            result_list.sort(key=lambda x: src_order.get(x['vod_id'].split(':')[0].replace('search_', ''), 999))

            return {'list': result_list, 'page': page}
        except Exception:
            return {'list': [], 'page': 1}

    # ---------- 详情 ----------
    def detailContent(self, ids):
        try:
            vid = ids[0] if isinstance(ids, list) else ids
            vid = str(vid)

            is_search = vid.startswith('search_')
            raw = vid.replace('search_', '')
            key, _, real_id = raw.partition(':')
            if not real_id or key not in {s['key'] for s in self.sources}:
                return {'list': []}

            # 先获取主源影片名（用于搜索其他源）
            main_src = next((s for s in self.sources if s['key'] == key), None)
            if not main_src:
                return {'list': []}
            j = self._fetch(main_src, ac='detail', ids=real_id)

            # 主源失败时，用名称搜索其他源兜底
            if not j or not j.get('list'):
                for s in self.sources:
                    if s['key'] == key:
                        continue
                    j = self._fetch(s, retry=False, timeout=self.aux_timeout,
                                    ac='list', wd=real_id)
                    if j and j.get('list'):
                        # 找到同名影片
                        for v in j['list']:
                            if _same_name(_clean(v.get('vod_name', '')), real_id):
                                j = {'list': [v]}
                                key = s['key']
                                break
                        if j.get('list'):
                            break
                if not j or not j.get('list'):
                    return {'list': []}

            vod = j['list'][0]
            name = _clean(vod.get('vod_name', ''))

            # 所有源并行请求（按 sources 顺序）
            all_srcs = self.sources[:self.cfg['line_batch']]
            executor = self._get_executor()
            futures = {}
            for s in all_srcs:
                if s['key'] == key:
                    futures[executor.submit(lambda _j=j: _j)] = s
                else:
                    futures[executor.submit(self._fetch, s, retry=False,
                                           timeout=self.aux_timeout,
                                           ac='detail', wd=name)] = s

            # 按 self.sources 顺序收集线路
            play_froms, play_urls = [], []
            for s in all_srcs:
                if len(play_froms) >= self.cfg['line_batch']:
                    break
                fut = next((f for f, src in futures.items() if src['key'] == s['key']), None)
                if not fut:
                    continue
                try:
                    j2 = fut.result(timeout=self.aux_timeout + 1)
                    if not j2 or not j2.get('list'):
                        continue
                    for v2 in j2['list']:
                        n2 = _clean(v2.get('vod_name', ''))
                        if not _same_name(n2, name):
                            # 放宽匹配：前10字前缀匹配兜底
                            n2_short = _norm_name(n2)[:10]
                            name_short = _norm_name(name)[:10]
                            if not (n2_short and name_short and
                                    (n2_short == name_short or
                                     n2_short.startswith(name_short) or
                                     name_short.startswith(n2_short))):
                                continue
                        f2, u2 = [], []
                        self._collect_lines(s['key'], v2, f2, u2)
                        if u2 and len(play_froms) < self.cfg['line_batch']:
                            play_froms.extend(f2)
                            play_urls.extend(u2)
                        break
                except Exception:
                    continue

            play_froms, play_urls = self._deduplicate_playlists(play_froms, play_urls)
            return {'list': [self._build_detail_dict(vid, vod, play_froms, play_urls)]}

        except Exception:
            return {'list': []}

    def _collect_lines(self, src_key, vod, play_froms, play_urls):
        src = next((s for s in self.sources if s['key'] == src_key), {})
        src_name = _clean(src.get('name', src_key)) or src_key
        if src_name in play_froms:
            return

        # 按 $$$ 分割线路名和播放地址
        from_names = str(vod.get('vod_play_from', '') or '').replace('，', ',').split('$$$')
        url_groups = str(vod.get('vod_play_url', '') or '').split('$$$')

        for i, (from_name, url_group) in enumerate(zip(from_names, url_groups)):
            if not url_group:
                continue
            from_name = _clean(from_name) or f'{src_name}{i+1}'

            episodes = []
            seen_ep = set()
            for ep in url_group.split('#'):
                parts = ep.split('$')
                if len(parts) < 2:
                    continue
                ep_name = _clean(parts[0]) or f"第{len(episodes)+1}集"
                ep_url = parts[-1].strip()
                if not self.allow_non_direct and not _is_direct(ep_url, self.allowed_exts):
                    continue
                mark = ep_name.lower()
                if mark in seen_ep:
                    continue
                seen_ep.add(mark)
                episodes.append(f"{ep_name}${ep_url}")

            if episodes:
                if len(from_names) > 1:
                    play_froms.append(f'{src_name}线路{i+1}')
                else:
                    play_froms.append(f'{src_name}线路')
                play_urls.append('#'.join(episodes))

    def _deduplicate_playlists(self, play_froms, play_urls):
        uniq_froms, uniq_urls = [], []
        seen_names, seen_groups = set(), set()
        for pf, pu in zip(play_froms, play_urls):
            n = _clean(pf).lower()
            u = _clean(pu).lower()
            if not n or not u or n in seen_names or u in seen_groups:
                continue
            seen_names.add(n)
            seen_groups.add(u)
            uniq_froms.append(_clean(pf))
            uniq_urls.append(pu)
        return uniq_froms, uniq_urls

    def _build_detail_dict(self, vid, vod, play_froms, play_urls):
        name = _clean(vod.get('vod_name', ''))
        try:
            score = str(float(vod.get('vod_score', 0) or 0))
            if score.endswith('.0'):
                score = score[:-2]
        except Exception:
            score = ''
        d = {
            'vod_id': vid,
            'vod_name': name,
            'vod_pic': vod.get('vod_pic', '') or '',
            'type_name': _clean(vod.get('type_name', '')),
            'vod_year': str(vod.get('vod_year', '') or ''),
            'vod_area': _clean(vod.get('vod_area', '')),
            'vod_actor': _clean(vod.get('vod_actor', '')),
            'vod_director': _clean(vod.get('vod_director', '')),
            'vod_content': _clean(vod.get('vod_content', '')),
            'vod_remarks': _clean(vod.get('vod_remarks', '')),
            'vod_play_from': '$$$'.join(play_froms),
            'vod_play_url': '$$$'.join(play_urls),
        }
        if score and score != '0':
            d['vod_score'] = score
        return d

    # ---------- 播放 ----------
    def playerContent(self, flag, pid, vipFlags):
        try:
            url = str(pid or '').strip()
            if url.startswith('//'):
                url = 'https:' + url
            header = {'User-Agent': UA}
            if _is_direct(url, self.allowed_exts):
                return {'parse': 0, 'playUrl': '', 'url': url, 'header': header}
            return {'parse': 1, 'playUrl': '', 'url': url, 'header': header}
        except Exception:
            return {'parse': 0, 'playUrl': '', 'url': pid, 'header': {'User-Agent': UA}}

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None


# 兼容旧版导入
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
