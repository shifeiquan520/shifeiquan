# -*- coding: utf-8 -*-
"""
采集之王 - 多源聚合影视源（重构版）
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
    "home_sources": 3,
    "category_sources": 10,
    "search_result_limit": 100,
    "line_batch": 8,
    "cache_ttl": 30,           # 秒

    # 协议/链接
    "allow_non_direct": True,   # True=兜底 parse=1
    "direct_exts": [".m3u8", ".mp4", ".flv", ".ts"],

    # 源管理
    "source_check_interval": 3600,   # 秒，健康检查间隔
    "source_max_failures": 3,        # 连续失败几次标记为死源
    "auto_disable_dead": True,

    # 分类别名映射（可在 extend 追加/覆盖）
    "category_aliases": {
        "记录片": "纪录片", "纪录片": "记录片",
        "动漫": "动漫片", "动漫片": "动漫片", "番剧": "动漫片",
        "国产剧": "国产剧", "大陆剧": "国产剧",
        "港台剧": "港台剧", "香港剧": "港台剧", "台湾剧": "港台剧",
        "日韩剧": "日韩剧", "韩国剧": "日韩剧", "日本剧": "日韩剧",
        "欧美剧": "欧美剧", "美剧": "欧美剧", "英剧": "欧美剧",
        "海外剧": "海外剧", "泰国剧": "海外剧",
        "短剧": "短剧",
    },

    # 源列表（可在 extend 里用 enabled_keys 覆盖/裁剪）
    "sources": [
        {"key": "lzi", "name": "量子", "api": "https://cj.lziapi.com/api.php/provide/vod"},
        {"key": "dyttzy", "name": "天堂", "api": "https://caiji.dyttzyapi.com/api.php/provide/vod"},
        {"key": "ruyi", "name": "如意", "api": "https://cj.rycjapi.com/api.php/provide/vod"},
        {"key": "bfzy", "name": "暴风", "api": "https://bfzyapi.com/api.php/provide/vod"},
        {"key": "ffzy", "name": "非凡", "api": "https://ffzy5.tv/api.php/provide/vod"},
        {"key": "zy360", "name": "360", "api": "https://360zy.com/api.php/provide/vod"},
        {"key": "jisu", "name": "极速", "api": "https://jszyapi.com/api.php/provide/vod"},
        {"key": "zuid", "name": "最大", "api": "https://api.zuidapi.com/api.php/provide/vod"},
        {"key": "ty", "name": "天涯", "api": "https://tyyszyapi.com/api.php/provide/vod"},
        {"key": "hhzy", "name": "火狐", "api": "https://hhzyapi.com/api.php/provide/vod"},
        {"key": "hwzy", "name": "华为", "api": "https://cjhwba.com/api.php/provide/vod"},
        {"key": "mtzy", "name": "茅台", "api": "https://caiji.maotaizy.cc/api.php/provide/vod"},
        {"key": "myzy", "name": "猫眼", "api": "https://api.maoyanapi.top/api.php/provide/vod"},
        {"key": "wsyzy", "name": "无水印", "api": "https://api.wsyzy.net/api.php/provide/vod"},
        {"key": "1080zy", "name": "1080", "api": "https://api.1080zyku.com/inc/api_mac10.php"},
        {"key": "155zy", "name": "155", "api": "https://155api.com/api.php/provide/vod"},
        {"key": "sdzy", "name": "闪电", "api": "https://sdzyapi.com/api.php/provide/vod"},
        {"key": "suoni", "name": "索尼", "api": "https://suoniapi.com/api.php/provide/vod"},
        {"key": "hnzy", "name": "红牛", "api": "https://www.hongniuzy2.com/api.php/provide/vod"},
        {"key": "hyzy", "name": "虎牙", "api": "https://www.huyaapi.com/api.php/provide/vod"},
        {"key": "dbzy", "name": "豆瓣", "api": "https://caiji.dbzy.tv/api.php/provide/vod"},
        {"key": "uku", "name": "优酷", "api": "https://api.ukuapi.com/api.php/provide/vod"},
        {"key": "ikun", "name": "爱坤", "api": "https://ikunzyapi.com/api.php/provide/vod"},
        {"key": "wujin", "name": "无尽", "api": "https://api.wujinapi.cc/api.php/provide/vod"},
        {"key": "guangsu", "name": "光速", "api": "https://api.guangsuapi.com/api.php/provide/vod"},
        {"key": "wolong", "name": "卧龙", "api": "https://collect.wolongzyw.com/api.php/provide/vod"},
        {"key": "xinlang", "name": "新浪", "api": "https://api.xinlangapi.com/xinlangapi.php/provide/vod"},
        {"key": "wwzy", "name": "旺旺", "api": "https://api.wwzy.tv/api.php/provide/vod"},
        {"key": "yhzy", "name": "樱花", "api": "https://m3u8.apiyhzy.com/api.php/provide/vod"},
        {"key": "nnzy", "name": "牛牛", "api": "https://api.niuniuzy.me/api.php/provide/vod"},
        {"key": "baiduyun", "name": "百度", "api": "https://api.apibdzy.com/api.php/provide/vod"},
        {"key": "subo", "name": "速播", "api": "https://subocaiji.com/api.php/provide/vod"},
        {"key": "jinying", "name": "金鹰", "api": "https://jinyingzy.com/api.php/provide/vod"},
        {"key": "piaoling", "name": "飘零", "api": "https://p2100.net/api.php/provide/vod"},
        {"key": "mozhua", "name": "魔爪", "api": "https://mozhuazy.com/api.php/provide/vod"},
        {"key": "modu", "name": "魔都", "api": "https://www.mdzyapi.com/api.php/provide/vod"},
        {"key": "xgzy", "name": "西瓜", "api": "https://caiji.xgzyapi.com/api.php/provide/vod"},
        {"key": "98zy", "name": "98", "api": "https://98zy.vip/api.php/provide/vod"},
        {"key": "dzzy", "name": "大众", "api": "https://cdn.dzzyapi.com/api.php/provide/vod"},
    ],
}


# ========================= 工具函数 =========================
_TAG_RE = re.compile(r'<[^>]+>')

def _clean(text):
    if not text:
        return ''
    text = _TAG_RE.sub('', str(text))
    text = text.replace('&nbsp;', ' ').replace('&', '&')
    text = text.replace('"', '"').replace('<', '<').replace('>', '>')
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
        r'采访$', r'制作特辑$', r'拍摄花絮$'
    ]
    return any(re.search(p, n) for p in block)

# 全局常用分类（可通过 cfg 覆盖）
CATEGORIES = [
    '短剧', 'AI漫剧', '国产剧', '香港剧', '韩国剧', '欧美剧', '日本剧',
    '台湾剧', '泰国剧', '海外剧', '动作片', '喜剧片', '爱情片', '科幻片',
    '恐怖片', '剧情片', '战争片', '动画片', '纪录片', '电影解说',
    '大陆综艺', '港台综艺', '日韩综艺', '欧美综艺',
    '国产动漫', '日韩动漫', '欧美动漫', '伦理片'
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
        return '采集之王'

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
        if isinstance(enabled, list) and enabled:
            enabled_set = set(enabled)
            self.sources = [s for s in self.cfg['sources'] if s['key'] in enabled_set]
        else:
            self.sources = list(self.cfg['sources'])

        # 运行时状态
        self.timeout = self.cfg['timeout']
        self.aux_timeout = self.cfg['aux_timeout']
        self.max_workers = self.cfg['max_workers']
        self.max_retries = self.cfg['max_retries']
        self.home_sources = self.cfg['home_sources']
        self.category_sources = self.cfg['category_sources']
        self.search_limit = self.cfg['search_result_limit']
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
        self._last_health_check = 0

        # 缓存
        self.cache = SimpleCache(self.cfg['cache_ttl'])

        # 线程池
        self._executor = None
        self._executor_lock = Lock()

        # 分类列表（给首页/筛选用）
        self._categories = list(CATEGORIES)

        # 远程配置缓存
        self._jumps_cache = ("", "")
        self._jumps_expire = 0

    # ---------- 生命周期 ----------
    def destroy(self):
        try:
            if self._executor:
                self._executor.shutdown(wait=False)
        except Exception:
            pass
        self._executor = None
        try:
            self.session.close()
        except Exception:
            pass

    def _get_executor(self):
        with self._executor_lock:
            if self._executor is None:
                self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.cfg['max_workers'])
        return self._executor

    # ---------- 源健康检查 ----------
    def _maybe_health_check(self):
        now = time.time()
        interval = self.cfg['source_check_interval']
        if now - self._last_health_check < interval:
            return
        self._last_health_check = now

        # 简单探活：随机抽 3 个源做 HEAD/GET
        import random
        candidates = [s for s in self.sources if not self.health[s['key']].disabled]
        if not candidates:
            return
        sample = random.sample(candidates, min(3, len(candidates)))

        def probe(src):
            key = src['key']
            try:
                t0 = time.time()
                r = self.session.get(src['api'].split('?', 1)[0],
                                     params={'ac': 'list', 'pg': 1},
                                     timeout=self.cfg['timeout'], verify=False)
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

        for src in sample:
            try:
                probe(src)
            except Exception:
                pass

        # 标记死源
        if self.cfg['auto_disable_dead']:
            with self._health_lock:
                for h in self.health.values():
                    if h.failures >= self.cfg['source_max_failures']:
                        h.disabled = True

    def _get_alive_sources(self, limit=None):
        self._maybe_health_check()
        alive = [s for s in self.sources if not self.health[s['key']].disabled]
        # 按延迟排序（低优先）
        alive.sort(key=lambda s: self.health[s['key']].latency_ms or 9999)
        if limit:
            return alive[:limit]
        return alive

    # ---------- 线程池 ----------
    def _get_executor(self):
        if self._executor is None:
            self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.cfg['max_workers'])
        return self._executor

    # ---------- 缓存键 ----------
    def _ck(self, *parts):
        return ':'.join(str(p) for p in parts)

    # ---------- 请求封装 ----------
    def _fetch(self, source, retry=True, timeout=None, **params):
        attempts = self.max_retries if retry else 1
        api = source['api'].split('?', 1)[0]

        for attempt in range(attempts):
            try:
                r = self.session.get(api, params=params,
                                     timeout=timeout or self.timeout, verify=False)
                if r.status_code == 200:
                    j = r.json()
                    if isinstance(j, dict):
                        with self._health_lock:
                            self.health[source['key']].record_ok(0)
                        return j
            except Exception:
                pass
            if attempt < (self.max_retries if retry else 1) - 1:
                time.sleep(0.2 * (attempt + 1))

        with self._health_lock:
            self.health[source['key']].record_fail()
        return None

    # ---------- 并行 ----------
    def _parallel(self, jobs):
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
        sources = self._get_alive_sources(self.home_sources)
        if not sources:
            return []

        jobs = [(s['key'], lambda s=s: self._fetch(s, retry=False, timeout=self.aux_timeout,
                                                    ac='detail', pg=1)) for s in sources]
        data = self._parallel(jobs)

        items = []
        seen = set()
        for s in sources:
            j = data.get(s['key'])
            if not j or not j.get('list'):
                continue
            for v in j['list'][:30]:
                item = self._item(v, s['key'], is_search=False)
                if item['vod_id'] in seen:
                    continue
                seen.add(item['vod_id'])
                items.append(item)
        return items[:30]

    # ---------- 分类 ----------
    def categoryContent(self, tid, pg, filter, extend):
        try:
            cat_name = unquote(str(tid or '')).strip()
            if not cat_name or ':' in cat_name or cat_name not in self._categories:
                return {'list': [], 'page': 1, 'pagecount': 0, 'limit': 20, 'total': 0}

            page = int(pg) if str(pg).isdigit() else 1
            sources = self._get_alive_sources(self.category_sources)
            if not sources:
                return {'list': [], 'page': page, 'pagecount': 0, 'limit': 20, 'total': 0}

            # 并行拿分类数据（单次请求，利用缓存）
            jobs = []
            for s in sources:
                ck = self._ck('cat', s['key'], cat_name, pg)
                def fn(s=s, ck=ck):
                    return self._cached_fetch(ck, lambda: self._category_fetch(s, cat_name, pg))
                jobs.append((s['key'], fn))

            data = self._parallel(jobs)

            items = []
            seen = set()
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
                    unique = f"{s['key']}:{vod.get('vod_id', '')}"
                    if unique in seen:
                        continue
                    seen.add(unique)
                    items.append(self._item(vod, s['key'], is_search=False))

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
        # 先拿该源的分类列表，找到对应 type_id
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
        # 拿详情列表
        return self._fetch(source, retry=False, timeout=self.aux_timeout,
                           ac='detail', t=src_tid, pg=pg)

    # ---------- 搜索 ----------
    def searchContent(self, key, quick, pg='1'):
        try:
            page = int(pg) if str(pg).isdigit() else 1
            if page > 1:
                return {'list': [], 'page': page}

            sources = self._get_alive_sources()
            if not sources:
                return {'list': [], 'page': page}

            jobs = [(s['key'], lambda s=s: self._fetch(s, retry=False, timeout=5, ac='list', wd=key))
                    for s in sources]
            data = self._parallel(jobs)

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
                    gk = (name, year, type_name)
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
                for src_key, v in entries:
                    item = self._item(v, src_key, is_search=True)
                    src_name = next((s['name'] for s in self.sources if s['key'] == src_key), src_key)
                    item['vod_remarks'] = f"{src_name} {_clean(v.get('vod_remarks', ''))}".strip()
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

            main_src = next(s for s in self.sources if s['key'] == key)
            j = self._fetch(main_src, ac='detail', ids=real_id)
            if not j or not j.get('list'):
                return {'list': []}

            vod = j['list'][0]
            name = _clean(vod.get('vod_name', ''))

            play_froms, play_urls = [], []
            self._collect_lines(key, vod, play_froms, play_urls)

            if is_search:
                play_froms, play_urls = self._deduplicate_playlists(play_froms, play_urls)
                return {'list': [self._build_detail_dict(vid, vod, play_froms, play_urls)]}

            # 其它源补线
            others = [s for s in self.sources if s['key'] != key][:8]
            if others:
                executor = self._get_executor()
                futures = {executor.submit(self._fetch, s, retry=False, timeout=self.aux_timeout,
                                           ac='detail', wd=name): s for s in others}

                for fut in concurrent.futures.as_completed(futures):
                    if len(play_froms) >= self.cfg['line_batch']:
                        break
                    s = futures[fut]
                    try:
                        j2 = fut.result(timeout=self.aux_timeout + 1)
                        if not j2 or not j2.get('list'):
                            continue
                        for v2 in j2['list']:
                            n2 = _clean(v2.get('vod_name', ''))
                            if not _same_name(n2, name):
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

        from_raw = str(vod.get('vod_play_from', '') or '').replace('$$$', ',').replace('，', ',')
        froms = [x.strip() for x in from_raw.split(',') if x.strip()]
        urls = [x.strip() for x in str(vod.get('vod_play_url', '') or '').split('$$$') if x.strip()]

        episodes = []
        seen_ep = set()
        for url_group in urls:
            if not url_group:
                continue
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
            play_froms.append(_clean(src.get('name', src_key)) or src_key)
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
        pass

    def manualVideoCheck(self):
        return False

    def destroy(self):
        try:
            if self._executor:
                self._executor.shutdown(wait=False)
        except Exception:
            pass
        self._executor = None
        try:
            self.session.close()
        except Exception:
            pass

    def localProxy(self, param):
        return None


# 兼容旧版导入
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')