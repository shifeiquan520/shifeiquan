#!/usr/bin/env python3
# coding=utf-8
# !/usr/bin/python
"""
厂长资源 (4kcz.com) —— TVBox / 影视仓 Python 爬虫 (T4 py)
功能  : 首页推荐 / 分类浏览+翻页 / 搜索 / 详情选集 / 播放解析(m3u8)
依赖  : 无第三方强依赖(有 requests 用 requests, 否则回退 urllib)
用法  : 见文件末尾「部署说明」

站点结构说明:
  - 列表页   : {SITE}/{分类路径}          翻页 {SITE}/{分类路径}/page/{N}
  - 详情页   : {SITE}/movie/{id}.html
  - 搜索     : {SITE}/boss1O1?q={关键词}
  - 播放页   : {SITE}/v_play/{base64}.html   base64 解码 = mv_{影片id}-nm_{集数}
  - 真实地址 : 分两种情况
      一级) iframe 的 url= 参数直接是 m3u8
      二级) url= 是加密串, 需再请求播放器页, 真实地址在 mysvg 变量里
  - 空线路   : 少数影片当前线路是空壳, 页面用 var url 指向另一条线路, 需跟随

播放请求头的坑(超时主因): 
  站点把视频分片伪装成 .jpg 托管在第三方图床(超星/网易/腾讯等), 
  这些图床对 Referer 敏感 —— 带 Referer 一律 403, 播放器会一路重试到超时。
  因此回传给播放器的 header 只给 User-Agent, 不给 Referer。
"""

import base64
import json
import re
import sys
import time
import urllib.parse

sys.path.append('..')

# ---- TVBox 运行环境提供 base.spider; 本地调试时降级为空基类 ----
try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        pass

try:
    import requests
    HAS_REQUESTS = True
except Exception:
    HAS_REQUESTS = False

DEFAULT_SITE = 'https://www.4kcz.com'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# ============================================================
# 纯 Python AES-256-GCM 解密 —— 绕过雷池 SafeLine WAF 动态防护
# 站点把所有页面内容用 AES-GCM 加密后返回, 浏览器端用 forge 解密。
# 这里在 Python 里直接复现: 从挑战页提取 key/iv/tag/密文, 解密即得真实 HTML。
# 无第三方依赖, 可在 TVBox(Chaquopy) 环境运行。
# ============================================================
_SBOX = [
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
]
_INV_SBOX = [0] * 256
for _i, _v in enumerate(_SBOX):
    _INV_SBOX[_v] = _i


def _xtime(a):
    return ((a << 1) ^ 0x11b) & 0xff if a & 0x80 else (a << 1) & 0xff


def _aes_key_expand(key):
    nk = len(key) // 4
    nr = nk + 6
    w = [list(key[4*i:4*i+4]) for i in range(nk)]
    rcon = 1
    for i in range(nk, 4*(nr+1)):
        temp = list(w[i-1])
        if i % nk == 0:
            temp = temp[1:] + temp[:1]
            temp = [_SBOX[b] for b in temp]
            temp[0] ^= rcon
            rcon = _xtime(rcon)
        elif nk > 6 and i % nk == 4:
            temp = [_SBOX[b] for b in temp]
        w.append([w[i-nk][j] ^ temp[j] for j in range(4)])
    rk = []
    for rnd in range(nr+1):
        b = bytearray()
        for c in range(4):
            b += bytes(w[rnd*4+c])
        rk.append(bytes(b))
    return rk


def _aes_enc_block(key, block):
    rk = _aes_key_expand(key)
    nr = len(rk) - 1
    st = [[block[r + 4*c] for c in range(4)] for r in range(4)]
    for r in range(4):
        for c in range(4):
            st[r][c] ^= rk[0][r + 4*c]
    for rnd in range(1, nr):
        for r in range(4):
            for c in range(4):
                st[r][c] = _SBOX[st[r][c]]
        for r in range(1, 4):
            st[r] = st[r][r:] + st[r][:r]
        for c in range(4):
            a = [st[r][c] for r in range(4)]
            st[0][c] = _xtime(a[0]) ^ (_xtime(a[1]) ^ a[1]) ^ a[2] ^ a[3]
            st[1][c] = a[0] ^ _xtime(a[1]) ^ (_xtime(a[2]) ^ a[2]) ^ a[3]
            st[2][c] = a[0] ^ a[1] ^ _xtime(a[2]) ^ (_xtime(a[3]) ^ a[3])
            st[3][c] = (_xtime(a[0]) ^ a[0]) ^ a[1] ^ a[2] ^ _xtime(a[3])
        for r in range(4):
            for c in range(4):
                st[r][c] ^= rk[rnd][r + 4*c]
    for r in range(4):
        for c in range(4):
            st[r][c] = _SBOX[st[r][c]]
    for r in range(1, 4):
        st[r] = st[r][r:] + st[r][:r]
    for r in range(4):
        for c in range(4):
            st[r][c] ^= rk[nr][r + 4*c]
    out = bytearray(16)
    for r in range(4):
        for c in range(4):
            out[r + 4*c] = st[r][c]
    return bytes(out)


def _gf_mult(x, y):
    x = bytearray(x)
    r = bytearray(16)
    for i in range(128):
        if (y[i >> 3] >> (7 - (i & 7))) & 1:
            for j in range(16):
                r[j] ^= x[j]
        carry = x[15] & 1
        for j in range(15, 0, -1):
            x[j] = ((x[j] >> 1) | (x[j-1] << 7)) & 0xff
        x[0] = (x[0] >> 1) & 0xff
        if carry:
            x[0] ^= 0xe1
    return bytes(r)


def _ghash(h, data):
    y = bytearray(16)
    for i in range(0, len(data), 16):
        blk = data[i:i+16]
        for j in range(16):
            y[j] ^= blk[j]
        y = bytearray(_gf_mult(bytes(y), h))
    return bytes(y)


def _ctr_crypt(key, counter, data):
    out = bytearray()
    ctr = bytearray(counter)
    for i in range(0, len(data), 16):
        ks = _aes_enc_block(key, bytes(ctr))
        chunk = data[i:i+16]
        for j in range(len(chunk)):
            out.append(chunk[j] ^ ks[j])
        for j in range(15, -1, -1):
            ctr[j] = (ctr[j] + 1) & 0xff
            if ctr[j] != 0:
                break
    return bytes(out)


def _inc32(counter):
    c = bytearray(counter)
    for j in range(15, 11, -1):
        c[j] = (c[j] + 1) & 0xff
        if c[j] != 0:
            break
    return bytes(c)


def _aes_gcm_decrypt(key, iv, ciphertext, tag, aad=b''):
    """AES-GCM 解密, 认证失败返回 None"""
    h = _aes_enc_block(key, bytes(16))
    if len(iv) == 12:
        j0 = iv + b'\x00\x00\x00\x01'
    else:
        j0 = _ghash(h, iv + b'\x00' * ((16 - len(iv) % 16) % 16) +
                    (len(iv)*8).to_bytes(8, 'big') + (0).to_bytes(8, 'big'))
    plain = _ctr_crypt(key, _inc32(j0), ciphertext)
    aad_pad = aad + b'\x00' * ((16 - len(aad) % 16) % 16)
    c_pad = ciphertext + b'\x00' * ((16 - len(ciphertext) % 16) % 16)
    data = aad_pad + c_pad + (len(aad)*8).to_bytes(8, 'big') + (len(ciphertext)*8).to_bytes(8, 'big')
    s = _ghash(h, data)
    mask = _aes_enc_block(key, j0)
    s = bytes(x ^ y for x, y in zip(s, mask))
    if s != tag:
        return None
    return plain


def _waf_decrypt(html):
    """若页面是雷池 SafeLine 动态防护挑战页, 解密返回真实 HTML; 否则原样返回"""
    if not html or 'raw_key' not in html or 'AES-GCM' not in html:
        return html
    try:
        def _arr(name):
            m = re.search(r'var\s+%s\s*=\s*(?:new\s+Uint8Array\()?\[([\d,\s]+)\]' % name, html)
            if not m:
                return None
            return bytes(int(x) for x in m.group(1).split(',') if x.strip())
        key = _arr('raw_key')
        enc = _arr('encrypted')
        tag = _arr('tag')
        iv = _arr('iv')
        if not (key and enc and tag and iv):
            return html
        plain = _aes_gcm_decrypt(key, iv, enc, tag)
        if plain:
            return plain.decode('utf-8', 'ignore')
    except Exception:
        pass
    return html


def _is_waf_block(html):
    """判断是否为雷池 WAF 拦截页(访问过快/恶意请求), 是则需退避重试"""
    if not html or len(html) < 500:
        return False
    # 拦截页特征: slg-box / slg-warning 元素 + 拦截文案
    if ('slg-box' in html or 'slg-warning' in html) and \
       ('请求频率过高' in html or '访问已被拦截' in html or '访问频繁' in html):
        return True
    return False


class Spider(BaseSpider):
    # ==================== 生命周期 ====================
    def init(self, extend=""):
        """extend 可传入新域名, 站点换域名时无需改代码"""
        self.site = DEFAULT_SITE
        try:
            if extend:
                ext = extend.strip()
                if ext.startswith('{'):
                    ext = json.loads(ext).get('site', '')
                if ext.startswith('http'):
                    self.site = ext.rstrip('/')
        except Exception:
            pass
        return self

    def getName(self):
        return '厂长资源'

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(m3u8|mp4|mkv|flv|avi|ts)(\?|$)', str(url), re.I))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        return ''

    def localProxy(self, param):
        return [200, "video/MP2T", {}, None]

    # ==================== 网络 ====================
    def _site(self):
        return getattr(self, 'site', DEFAULT_SITE)

    def _headers(self, ref=None):
        return {
            'User-Agent': UA,
            'Referer': ref or (self._site() + '/'),
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

    def _session(self):
        """复用连接省去重复 TLS 握手(站点首字节约 2.8s, 复用可省 0.3~0.8s)"""
        if not HAS_REQUESTS:
            return None
        se = getattr(self, '_se', None)
        if se is None:
            try:
                se = requests.Session()
                ad = requests.adapters.HTTPAdapter(
                    pool_connections=4, pool_maxsize=8, max_retries=0)
                se.mount('https://', ad)
                se.mount('http://', ad)
            except Exception:
                se = requests
            self._se = se
        return se

    # 修改点：增大超时，增加重试次数；识别 WAF 拦截页并退避重试
    def _get(self, url, ref=None, timeout=None, retry=4):
        """
        取网页源码; 失败退避重试, 最终失败返回空串。
        超时用 (连接, 读取) 二元组: 连接超时短(死链快速失败), 读取超时放宽。
        若返回的是雷池 WAF 动态防护挑战页, 自动解密得到真实 HTML;
        若返回的是 WAF 拦截页(访问过快), 等待更久后重试。
        """
        ct, rt = timeout or (8, 25)   # 原为 (6,15)，增大读取超时
        for i in range(max(1, retry)):
            try:
                if HAS_REQUESTS:
                    r = self._session().get(url, headers=self._headers(ref),
                                            timeout=(ct, rt), allow_redirects=True)
                    if r.status_code >= 500:
                        raise IOError('http %d' % r.status_code)
                    html = r.content.decode('utf-8', 'ignore')
                else:
                    import urllib.request
                    req = urllib.request.Request(url, headers=self._headers(ref))
                    html = urllib.request.urlopen(req, timeout=rt).read().decode('utf-8', 'ignore')
                # 雷池 WAF 动态防护: 页面内容是 AES-GCM 加密的, 需解密
                # 注意: _waf_decrypt 对非加密页原样返回(同一对象), 只有真正解密成功才采用
                dec = _waf_decrypt(html)
                if dec and dec is not html and len(dec) > 100:
                    return dec
                # 雷池 WAF 拦截页(访问过快): 等待更久再重试, 避免分类/播放大面积空白
                if _is_waf_block(html):
                    if i + 1 < max(1, retry):
                        time.sleep(2.5 * (i + 1))
                        continue
                    return ''
                return html
            except Exception:
                if i + 1 < max(1, retry):
                    time.sleep(0.8 * (i + 1))  # 退避重试
        return ''

    # ==================== 工具 ====================
    @staticmethod
    def _text(html):
        """去标签取纯文本"""
        t = re.sub(r'<[^>]+>', '', html or '')
        t = t.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&quot;', '"')
        t = t.replace('\u200b', '')  # 站点标题里混有零宽字符
        return re.sub(r'\s+', ' ', t).strip()

    def _parse_list(self, html):
        """
        列表解析。先锁定结果容器 div.bt_img 内的 ul, 避免把侧栏推荐
        当成结果(搜索页尤其明显: 实际12条却会误抓到20条)。
        容器找不到时回退为全页扫描。
        """
        if not html:
            return []

        block = ''
        m = re.search(r'<div[^>]*class="?[^">]*bt_img[^">]*"?[^>]*>', html)
        if m:
            u = re.search(r'<ul[^>]*>([\s\S]*?)</ul>', html[m.end():])
            if u:
                block = u.group(1)

        items = re.findall(r'<li[^>]*>([\s\S]*?)</li>', block) if block else []
        if not items:  # 回退: 全页粗扫
            items = [html[max(0, x.start() - 320): x.end() + 560]
                     for x in re.finditer(r'/movie/(\d+)\.html', html)]

        out, seen = [], set()
        for it in items:
            im = re.search(r'/movie/(\d+)\.html', it)
            if not im:
                continue
            vid = im.group(1)
            if vid in seen:
                continue

            # 站点属性可能带引号也可能不带引号(class=dytit / class="dytit")
            nm = re.search(r'class="?dytit"?[^>]*>\s*<a[^>]*>([^<]+)</a>', it) \
                 or re.search(r'alt="?([^"\s>]+)"?', it)
            name = self._text(nm.group(1)) if nm else ''
            if not name:
                continue

            pm = re.search(r'data-original="?([^"\s>]+)"?', it) \
                 or re.search(r'<img[^>]*src="?([^"\s>]+)"?', it)
            pic = pm.group(1) if pm else ''

            # 角标: 优先集数/清晰度标签; 站点列表项通常只有主演, 需截断避免卡片溢出
            remark = ''
            rm = re.search(r'class="?(?:jidi|dysc|hdtag|note)"?[^>]*>([^<]*)<', it)
            if rm:
                remark = self._text(rm.group(1))
            else:
                rm = re.search(r'class="?inzhuy"?[^>]*>([^<]*)<', it)
                if rm:
                    actors = self._text(rm.group(1)).replace('主演：', '').strip()
                    if actors:
                        parts = [p for p in re.split(r'[,，、\s]+', actors) if p][:2]
                        remark = ' '.join(parts) + ('…' if len(parts) < len(
                            [p for p in re.split(r'[,，、\s]+', actors) if p]) else '')
            remark = remark.rstrip('：:')

            seen.add(vid)
            out.append({'vod_id': vid, 'vod_name': name,
                        'vod_pic': pic, 'vod_remarks': remark})
        return out

    # ==================== 筛选数据 ====================
    # 站点三套 taxonomy(取自 sitemap-taxonomy-*.xml, 为官方全集)。
    # 注意: 该站不支持多维度组合筛选(类型+年份+排序均无效),
    #       每个 taxonomy 项都是一条独立列表路径, 故筛选=切换路径。
    TAGS = [
        ('剧情', 'juqing'), ('动作', 'dozuo'), ('喜剧', 'xiju'), ('爱情', 'aiqing'),
        ('科幻', 'kh'), ('悬疑', 'xuanyi'), ('惊悚', 'kingsong'), ('恐怖', 'kubu'),
        ('犯罪', 'fanzui'), ('冒险', 'maoxian'), ('奇幻', 'qihuan'), ('动画', 'dhh'),
        ('动漫', 'doman'), ('战争', 'zhanzheng'), ('历史', 'lishi'), ('古装', 'guzhuang'),
        ('武侠', 'wuxia'), ('家庭', 'jiating'), ('传记', 'chuanji'), ('灾难', 'zainan'),
        ('运动', 'yd'), ('音乐', 'yy'), ('歌舞', 'gw'), ('西部', 'xb'),
        ('儿童', 'etet'), ('同性', 'tongxing'), ('情色', 'qingse'), ('真人秀', 'zrx'),
        ('纪录片', 'jlpp'), ('短片', 'dp'),
    ]
    VIEW_CATS = [
        ('4K', '4k'), ('1080P', '1080p'), ('720P', '720p'), ('HD', 'hd'),
        ('IMAX', 'imax'), ('豆瓣Top250', 'douban250'), ('漫威宇宙', 'manweidianyingyuzhou'),
        ('星球大战', 'xingqiudazhanxilie'), ('周星驰', 'zhouxingchi'), ('番剧', 'fjj'),
        ('剧场版', 'jcb'), ('国漫', 'gmm'), ('真人版', 'zrbb'), ('PV预告', 'pvyugao'),
        ('国产剧', 'guochanju'), ('欧美剧', 'omm'), ('英美剧', 'ymm'), ('韩剧', 'hjj'),
        ('日剧', 'rjj'), ('港台剧', 'gangtaiju'), ('泰剧', 'taiju-2'), ('德剧', 'deju'),
        ('海外剧', 'hww'), ('综艺', '%e7%bb%bc%e8%89%ba'), ('纪录片', 'jlpp'),
        ('短片', '%e7%9f%ad%e7%89%87'), ('网盘分享', '%e7%bd%91%e7%9b%98%e5%88%86%e4%ba%ab'),
        ('TS', 'ts'), ('TC', 'tc'),
    ]
    SERIES = [
        ('电影', 'dyy'), ('电视剧', 'dianshiju'), ('华语电影', 'huayudianying'),
        ('欧美电影', 'meiguodianying'), ('日本电影', 'ribendianying'),
        ('韩国电影', 'hanguodianying'), ('印度电影', 'yindudianying'),
        ('加拿大电影', 'jianadadianying'), ('俄罗斯电影', 'eluosidianying'),
        ('国产剧', 'guochanju'), ('美剧', 'mj'), ('韩剧', 'hj'), ('日剧', 'rj'),
        ('海外剧', 'hwj'), ('动画', 'dohua'),
    ]

    # 聚合片库: type_id -> (筛选key, 选项列表)
    LIBS = {
        'movie_bt_tags': ('tag', TAGS),
        'movie_bt_view_cat': ('cat', VIEW_CATS),
        'movie_bt_series': ('ser', SERIES),
    }

    # ==================== 首页 ====================
    def homeContent(self, filter):
        cats = [
            {'type_id': 'movie_bt', 'type_name': '最近更新'},
            # 带筛选的聚合片库
            {'type_id': 'movie_bt_tags', 'type_name': '类型片库'},
            {'type_id': 'movie_bt_series', 'type_name': '剧集片库'},
            {'type_id': 'movie_bt_view_cat', 'type_name': '专题片库'},
            # 常用快捷入口
            {'type_id': 'movie_bt_series/dyy', 'type_name': '电影'},
            {'type_id': 'movie_bt_series/guochanju', 'type_name': '国产剧'},
            {'type_id': 'movie_bt_series/mj', 'type_name': '美剧'},
            {'type_id': 'movie_bt_series/hj', 'type_name': '韩剧'},
            {'type_id': 'movie_bt_series/rj', 'type_name': '日剧'},
            {'type_id': 'movie_bt_view_cat/fjj', 'type_name': '动漫'},
            {'type_id': 'movie_bt_view_cat/douban250', 'type_name': '豆瓣Top250'},
            {'type_id': 'movie_bt_view_cat/4k', 'type_name': '4K专区'},
        ]

        filters = {}
        for tid, (key, opts) in self.LIBS.items():
            name = {'tag': '类型', 'cat': '专题', 'ser': '分类'}[key]
            filters[tid] = [{
                'key': key,
                'name': name,
                'value': [{'n': n, 'v': v} for n, v in opts],
            }]

        return {'class': cats, 'filters': filters}

    def homeVideoContent(self):
        return {'list': self.categoryContent('movie_bt', 1, {}, {}).get('list', [])}

    # ==================== 分类列表 ====================
    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1

        tid = str(tid).strip('/')

        # 聚合片库: 由筛选器决定具体走哪条 taxonomy 路径
        if tid in self.LIBS:
            key, opts = self.LIBS[tid]
            slug = ''
            if isinstance(extend, dict):
                slug = str(extend.get(key, '') or '').strip()
            if not slug:  # 未选择时用第一项兜底
                slug = opts[0][1]
            tid = '%s/%s' % (tid, slug)

        base = '%s/%s' % (self._site(), tid)
        url = base if pg == 1 else '%s/page/%d' % (base, pg)

        vod_list = self._parse_list(self._get(url))
        # 空页说明已到末尾, 让 TVBox 停止继续翻页
        pagecount = pg if not vod_list else 9999
        return {
            'list': vod_list,
            'page': pg,
            'pagecount': pagecount,
            'limit': 90,
            'total': 999999,
        }

    # ==================== 详情 / 选集 ====================
    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, (list, tuple)) else ids
        vid = str(vid).strip()
        html = self._get('%s/movie/%s.html' % (self._site(), vid))
        if not html:
            return {'list': []}

        # --- 标题 ---
        m = re.search(r'<div class="?moviedteail_tt"?[^>]*>[\s\S]*?<h1[^>]*>([^<]+)</h1>', html) \
            or re.search(r'<meta\s+property="?og:title"?\s+content="?([^"\s>]+)"?', html) \
            or re.search(r'<title>《([^》]+)》', html) \
            or re.search(r'<title>([^<|_]+)', html)
        name = self._text(m.group(1)) if m else ''

        # --- 封面 ---
        m = re.search(r'(?:property|name)="og:image"\s+content="([^"]+)"', html) \
            or re.search(r'data-original="?([^"\s>]+)"?', html)
        pic = m.group(1) if m else ''

        # --- 简介 ---
        m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html)
        content = m.group(1).strip() if m else ''

        # --- 元信息 (类型/地区/年份/导演/主演/语言) ---
        info = {}
        mb = re.search(r'<ul class="?moviedteail_list"?[^>]*>([\s\S]*?)</ul>', html)
        if mb:
            for li in re.findall(r'<li[^>]*>([\s\S]*?)</li>', mb.group(1)):
                t = self._text(li)
                if '：' in t:
                    k, v = t.split('：', 1)
                    info[k.strip()] = v.strip()

        # --- 选集: v_play 加密链接, 仅存 base64 短码, 换域名自动适配 ---
        episodes = []
        seen = set()
        pairs = re.findall(
            r'<a[^>]*href="?[^">]*?/v_play/([A-Za-z0-9+/=_-]+)\.html"?[^>]*>([\s\S]*?)</a>', html)
        used = {}
        for code, txt in pairs:
            if code in seen:
                continue
            seen.add(code)
            label = self._text(txt)
            if not label or '立即播放' in label or '播放' == label:
                label = self._ep_label(code, len(episodes))
            label = label.replace('#', '').replace('$', '')
            # 部分影片是"多线路"而非多集, 标签会完全重名(如两个"线路1080P"),
            # 在 TVBox 里表现为两个无法区分的按钮 —— 重名时补序号
            used[label] = used.get(label, 0) + 1
            if used[label] > 1:
                label = '%s%d' % (label, used[label])
            episodes.append('%s$%s' % (label, code))

        if not episodes:
            for code in re.findall(r'/v_play/([A-Za-z0-9+/=_-]+)\.html', html):
                if code in seen:
                    continue
                seen.add(code)
                episodes.append('%s$%s' % (self._ep_label(code, len(episodes)), code))

        # 无效页面(404 / 已下架): 返回空列表, 避免 TVBox 里出现垃圾条目
        if not episodes and (not name or name in ('404', '页面未找到') or '404' in name):
            return {'list': []}

        # --- 豆瓣评分: <li>豆瓣：<a class="dbpingfen" href="douban...">7.2</a></li> ---
        score = info.get('豆瓣', '')
        m = re.search(r'class="?dbpingfen"?[^>]*>\s*([\d.]+)\s*<', html)
        if m:
            score = m.group(1)
        score = score.strip() if score else ''
        if not re.match(r'^\d+(\.\d+)?$', score or ''):
            score = ''

        # --- 年份: 站点部分老片写成 "1900~2000年代", 回退到上映日期取精确年份 ---
        year = info.get('年份', '').strip()
        if not re.match(r'^\d{4}$', year):
            ym = re.search(r'(19\d{2}|20\d{2})', info.get('上映', '') or year)
            year = ym.group(1) if ym else year

        # 角标优先级: 豆瓣评分 > 集数 > 上映日期
        # 注意: 多条目未必是多集, 也可能是同一部片的多条线路, 别误报"共N集"
        is_multi_ep = len(episodes) > 1 and any(
            re.search(r'第?\s*\d+\s*集|^\s*\d+\s*$|EP\s*\d+', e.split('$')[0], re.I)
            for e in episodes)
        if score:
            remarks = '豆瓣 %s' % score
        elif is_multi_ep:
            remarks = '共%d集' % len(episodes)
        else:
            remarks = info.get('上映', '')

        # 简介前置关键信息, 方便在详情页一眼看到
        extra = []
        if score:
            extra.append('豆瓣评分 %s' % score)
        if info.get('时长'):
            extra.append('片长 %s' % info['时长'])
        if info.get('又名'):
            extra.append('又名: %s' % info['又名'])
        if extra:
            content = '【%s】%s' % (' / '.join(extra), content)

        vod = {
            'vod_id': vid,
            'vod_name': name,
            'vod_pic': pic,
            'vod_year': year,
            'vod_area': info.get('地区', ''),
            'vod_lang': info.get('语言', ''),
            'vod_score': score,
            'vod_douban_score': score,
            'vod_remarks': remarks,
            'vod_duration': info.get('时长', ''),
            'type_name': info.get('类型', ''),
            'vod_actor': info.get('主演', ''),
            'vod_director': info.get('导演', ''),
            'vod_writer': info.get('编剧', ''),
            'vod_content': content,
            'vod_play_from': '厂长资源',
            'vod_play_url': '#'.join(episodes),
        }
        return {'list': [vod]}

    @staticmethod
    def _ep_label(code, idx):
        """从 base64 码 mv_{id}-nm_{集数} 还原集数标签"""
        try:
            pad = code + '=' * (-len(code) % 4)
            raw = base64.b64decode(pad).decode('utf-8', 'ignore')
            m = re.search(r'nm_(\d+)', raw)
            if m:
                return '第%s集' % m.group(1)
        except Exception:
            pass
        return '第%d集' % (idx + 1)

    # ==================== 搜索 ====================
    def searchContent(self, key, quick, pg="1"):
        """站点搜索为分词模糊匹配且不支持翻页, 这里按相关度重排, 精确匹配置顶"""
        key = str(key).strip()
        if not key:
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 90, 'total': 0}
        # 站点搜索路径已多次变更: 依次尝试 WordPress 格式 / 表单 action
        q = urllib.parse.quote(key)
        urls = [
            '%s/search/%s-------------.html' % (self._site(), q),
            '%s/nimasile?q=%s' % (self._site(), q),
        ]
        vod_list = []
        for u in urls:
            vod_list = self._parse_list(self._get(u))
            if vod_list:
                break

        def score(v):
            n = v.get('vod_name', '')
            if n == key:
                return 0
            if key and key in n:
                return 1
            if n and n in key:
                return 2
            return 3

        vod_list.sort(key=score)
        return {'list': vod_list, 'page': 1, 'pagecount': 1,
                'limit': 90, 'total': len(vod_list)}

    # ==================== 播放解析 ====================
    def _play_header(self, url):
        """
        按视频分片所在 CDN 决定回传给播放器的请求头。
        实测: 站点把视频分片伪装成 .jpg 托管在第三方图床/网盘,
        这些图床对 Referer 敏感 —— 带 Referer 直接 403,
        只带 User-Agent 才能正常拉流。
        """
        h = {'User-Agent': UA}
        try:
            host = urllib.parse.urlparse(url).hostname or ''
        except Exception:
            host = ''
        # 白名单: 确实校验来源、需要 Referer 的站内直连线路
        if any(k in host for k in ('4kcz.com',)):
            h['Referer'] = self._site() + '/'
        # 对其他域名(图床)不加 Referer
        return h

    def _pick_m3u8(self, page, base=''):
        """从播放器页面里挖真实播放地址(二级解析)，增加更多模式"""
        if not page:
            return ''

        # 常见变量名：mysvg, url, playurl, player_aaaa, video, source 等
        patterns = [
            r"mysvg\s*=\s*['\"]([^'\"]+)['\"]",
            r"var\s+(?:url|urls|vurl|videoUrl|playurl|player_aaaa)\s*=\s*['\"]([^'\"]+)['\"]",
            r"(?:source|src|url)\s*[:=]\s*['\"](https?://[^'\"]+?\.(?:m3u8|mp4)[^'\"]*)['\"]",
            r"['\"]?(?:m3u8|mp4)['\"]?\s*[:=]\s*['\"]([^'\"]+?\.(?:m3u8|mp4))['\"]",
        ]
        for pat in patterns:
            m = re.search(pat, page, re.I)
            if m:
                raw = m.group(1)
                # 处理可能的相对路径
                if not raw.startswith('http'):
                    if raw.startswith('//'):
                        raw = 'https:' + raw
                    elif base:
                        raw = urllib.parse.urljoin(base, raw)
                if self.isVideoFormat(raw):
                    return raw

        # 兜底: 裸露的 m3u8 / mp4
        m = re.search(r'(https?://[^\s"\'<>\\]+?\.(?:m3u8|mp4)[^\s"\'<>\\]*)', page, re.I)
        if m:
            return m.group(1)

        # 相对路径 m3u8
        m = re.search(r'["\'](/[^\s"\'<>]+?\.m3u8[^\s"\'<>]*)["\']', page)
        if m and base:
            return urllib.parse.urljoin(base, m.group(1))

        return ''

    def playerContent(self, flag, id, vipFlags):
        pid = str(id).strip()
        # 兼容: 传入完整 URL 或 base64 短码
        play_url = pid if pid.startswith('http') else \
            '%s/v_play/%s.html' % (self._site(), pid)

        result = {'parse': 0, 'playUrl': '', 'url': '',
                  'header': {'User-Agent': UA}}

        # 第一次请求播放页（超时已加大）
        html = self._get(play_url, ref=self._site() + '/')
        if not html:
            # 如果第一次请求失败，可尝试直接让TVBox嗅探该页（保底）
            result['parse'] = 1
            result['url'] = play_url
            result['header'] = {'User-Agent': UA}
            return result

        # 查找 iframe (属性可能带引号也可能不带)
        m = re.search(r'<iframe[^>]*\bsrc="?([^"\s>]+)"?', html)

        # 部分影片当前线路是空壳, 页面用 var url 指向另一条线路; 跟随一次
        if not m:
            jump = re.search(r'var\s+url\s*=\s*["\']?(https?://[^"\'\s]*?/v_play/[^"\'\s]+)', html)
            if jump and jump.group(1) != play_url:
                html2 = self._get(jump.group(1), ref=play_url)
                if html2:
                    m2 = re.search(r'<iframe[^>]*\bsrc="?([^"\s>]+)"?', html2)
                    if m2:
                        html, play_url, m = html2, jump.group(1), m2

        # 如果没有 iframe，尝试直接从当前页面解析
        if not m:
            real = self._pick_m3u8(html, play_url)
            if real:
                result['url'] = self._safe_url(real)
                result['header'] = self._play_header(real)
                return result
            # 还是不行，交给嗅探
            result['parse'] = 1
            result['url'] = play_url
            result['header'] = {'User-Agent': UA}
            return result

        src = m.group(1)
        if not src.startswith('http'):
            src = urllib.parse.urljoin(play_url, src)

        # 一级: iframe 的 url= 参数直接就是 m3u8
        mm = re.search(r'[?&]url=([^&"\']+)', src)
        if mm:
            real = urllib.parse.unquote(mm.group(1))
            if self.isVideoFormat(real):
                result['url'] = self._safe_url(real)
                result['header'] = self._play_header(real)
                return result

        # 二级: url= 是加密串, 真实地址藏在播放器页面里, 需再请求一层
        page = self._get(src, ref=play_url)
        real = self._pick_m3u8(page, src)
        if real:
            result['url'] = self._safe_url(real)
            result['header'] = self._play_header(real)
            return result

        # 实在解不出 → 把播放器页交给 TVBox 嗅探(保底, 不留空白)
        result['parse'] = 1
        result['url'] = src
        result['header'] = {'User-Agent': UA, 'Referer': play_url}
        return result

    @staticmethod
    def _safe_url(u):
        """对中文等非 ASCII 字符做百分号编码, 保留 URL 结构符号"""
        try:
            return urllib.parse.quote(u, safe=':/?&=.#%+-_~@!$,;*()[]')
        except Exception:
            return u


# ============================================================
# 本地自测:  python3 csp_4kcz.py
# ============================================================
if __name__ == '__main__':
    s = Spider().init('')
    print('== 分类 ==')
    cs = s.homeContent(False)['class']
    print(len(cs), [c['type_name'] for c in cs])

    print('\n== 列表(电影 第1页) ==')
    lst = s.categoryContent('movie_bt_series/dyy', 1, {}, {})['list']
    print('共%d条, 首条: %s' % (len(lst), lst[0] if lst else '空'))

    print('\n== 详情(电视剧) ==')
    d = s.detailContent(['23645'])['list'][0]
    print('%s | %s | %s | %s' % (d['vod_name'], d['vod_year'],
                                  d['vod_area'], d['type_name']))
    print('导演:', d['vod_director'])
    print('选集:', d['vod_play_url'][:120], '...')

    print('\n== 播放解析 ==')
    first = d['vod_play_url'].split('#')[0].split('$')[1]
    print('m3u8:', s.playerContent('厂长资源', first, '')['url'])

    print('\n== 搜索 ==')
    r = s.searchContent('消失的人', True)['list']
    print('共%d条:' % len(r), [x['vod_name'] for x in r[:5]])
