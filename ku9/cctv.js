/**
 * 央视频直播/回看解析 - 酷9 JS版（修复AES cKey）
 * 用法：?id=频道ID (如 cctv5)
 *       ?id=频道ID&playseek=20260517120000-20260517130000 (回看)
 */
function main(item) {
    // ======================== 常量 ========================
    var XOR_KEY = [0x84,0x2E,0xED,0x08,0xF0,0x66,0xE6,0xEA,0x48,0xB4,0xCA,0xA9,0x91,0xED,0x6F,0xF3];
    var AES_KEY_HEX = '4E2918885FD98109869D14E0231A0BF4';
    var AES_IV_HEX  = '16B17E519DDD0CE5B79D7A63A4DD801C';
    var SR = 'mg3c3b04ba';
    var NN = 'https://m.yangshipin.cn/';
    var UA_SUFFIX = '|mozilla/5.0 (iphone; cpu||Mozilla|Netscape|Win32|';

    // 频道列表（保持原有）
    var CHANNELS = {
        'cctv1':['2024078201','600001859','fhd'],'cctv2':['2024075401','600001800','fhd'],
        'cctv3':['2024068501','600001801','fhd'],'cctv4':['2029797101','600001814','fhd'],
        'cctv5':['2024078401','600001818','fhd'],'cctv5p':['2024078001','600001817','fhd'],
        'cctv6':['2013693901','600108442','fhd'],'cctv7':['2024072001','600004092','fhd'],
        'cctv8':['2029793001','600001803','fhd'],'cctv9':['2024078601','600004078','fhd'],
        'cctv10':['2024078701','600001805','fhd'],'cctv11':['2027248701','600001806','fhd'],
        'cctv12':['2027248801','600001807','fhd'],'cctv13':['2029797201','600001811','fhd'],
        'cctv14':['2027248901','600001809','fhd'],'cctv15':['2027249001','600001815','fhd'],
        'cctv16':['2027249101','600098637','fhd'],'cctv164k':['2027249301','600099502','fhd'],
        'cctv17':['2027249401','600001810','fhd'],'cctv4k':['2029810301','600002264','fhd'],
        'cctv8k':['2026774101','600156816','fhd'],'cgtn':['2024181701','600014550','fhd'],
        'cgtnfy':['2024181801','600084704','fhd'],'cgtney':['2024181901','600084758','fhd'],
        'cgtnalby':['2024182001','600084782','fhd'],'cgtnxby':['2024182101','600084744','fhd'],
        'cgtnwyjl':['2024182301','600084781','fhd'],'cctvfyjc':['2025637103','600099658','fhd'],
        'cctvdyjc':['2026874203','600099655','fhd'],'cctvhjjc':['2026874303','600099620','fhd'],
        'cctvsjdl':['2026874403','600099637','fhd'],'cctvfyyy':['2026874503','600099660','fhd'],
        'cctvbqkj':['2026874603','600099649','fhd'],'cctvfyzq':['2026966203','600099636','fhd'],
        'cctvgeqwq':['2026874703','600099659','fhd'],'cctvnxss':['2026874803','600099650','fhd'],
        'cctvyswhjp':['2026874903','600099653','fhd'],'cctvystq':['2026875003','600099652','fhd'],
        'cctvdszn':['2026875103','600099656','fhd'],'cctvwsjk':['2025637003','600099651','fhd'],
        'bjws':['2024052703','600002309','fhd'],'jsws':['2024171103','600002521','fhd'],
        'dfws':['2024054503','600002483','fhd'],'zjws':['2024054703','600002520','fhd'],
        'hnws':['2024054803','600002475','fhd'],'hbws':['2024171203','600002508','fhd'],
        'gdws':['2024060903','600002485','fhd'],'gxws':['2024060703','600002509','fhd'],
        'hljws':['2029797003','600002498','fhd'],'hnws2':['2024055603','600002506','fhd'],
        'cqws':['2024061103','600002531','fhd'],'szws':['2024061303','600002481','fhd'],
        'scws':['2024061403','600002516','fhd'],'henanws':['2029797303','600002525','fhd'],
        'fjdnhz':['2024061503','600002484','fhd'],'gzhws':['2024061603','600002490','fhd'],
        'jxws':['2024061703','600002503','fhd'],'lnws':['2024171303','600002505','fhd'],
        'ahws':['2024171403','600002532','fhd'],'hbws2':['2024171503','600002493','fhd'],
        'sdws':['2029787903','600002513','fhd'],'tjws':['2019927003','600152137','fhd'],
        'jlws':['2025561503','600190405','fhd'],'shanxiws':['2029795103','600190400','fhd'],
        'nxws':['2025608503','600190737','fhd'],'nmgws':['2025561203','600190401','fhd'],
        'ynws':['2025561303','600190402','fhd'],'shanxiws2':['2025560803','600190407','fhd'],
        'qhws':['2025559103','600190406','fhd'],'xzws':['2025558003','600190403','fhd'],
        'cetv1':['2022823801','600171827','fhd'],'xjws':['2019927403','600152138','fhd']
    };

    var inputUrl = item.url || '';
    var id = ku9.getQuery(inputUrl, 'id') || 'cctv1';
    var playseek = ku9.getQuery(inputUrl, 'playseek') || null;
    if (!playseek || playseek === '') playseek = null;
    var isLive = !playseek;

    if (!CHANNELS[id]) {
        return { url: '', msg: '频道不存在' };
    }
    var channelInfo = CHANNELS[id];
    var cnlid = channelInfo[0];
    var livepid = channelInfo[1];
    var defn = channelInfo[2];

    // ======================== 工具函数 ========================
    function strToBytes(s) {
        var a = [];
        for (var i = 0; i < s.length; i++) a.push(s.charCodeAt(i) & 0xFF);
        return a;
    }
    function bytesToStr(a) {
        var s = '';
        for (var i = 0; i < a.length; i++) s += String.fromCharCode(a[i]);
        return s;
    }
    function hex2bin(hex) {
        var s = '';
        for (var i = 0; i < hex.length; i+=2) s += String.fromCharCode(parseInt(hex.substr(i,2),16));
        return s;
    }
    function bin2hex(str) {
        var hex = '';
        for (var i = 0; i < str.length; i++) {
            var b = str.charCodeAt(i) & 0xFF;
            hex += (b < 16 ? '0' : '') + b.toString(16);
        }
        return hex;
    }
    function randomUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            var r = Math.random()*16|0, v = c==='x' ? r : (r&0x3|0x8);
            return v.toString(16);
        });
    }
    function generateGuid() {
        var s = '';
        for (var i = 0; i < 32; i++) s += Math.floor(Math.random()*16).toString(16);
        return s;
    }
    function packN(num) {
        return String.fromCharCode((num>>>24)&0xFF, (num>>>16)&0xFF, (num>>>8)&0xFF, num&0xFF);
    }
    function packn(num) {
        return String.fromCharCode((num>>>8)&0xFF, num&0xFF);
    }
    function calcSignature(byteArr) {
        var sig = 0;
        for (var i = 0; i < byteArr.length; i++) sig = (0x83 * sig + (byteArr[i] & 0xFF)) & 0x7FFFFFFF;
        return sig;
    }
    function xorArray(byteArr) {
        var r = [];
        for (var i = 0; i < byteArr.length; i++) r.push(byteArr[i] ^ XOR_KEY[i & 0xF]);
        return r;
    }

    // 标准字节级 Base64
    function base64EncodeBytes(bytes) {
        var alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
        var out = '';
        var i = 0;
        while (i < bytes.length) {
            var a = bytes[i++] || 0;
            var b = bytes[i++] || 0;
            var c = bytes[i++] || 0;
            var bits = (a << 16) | (b << 8) | c;
            out += alphabet[(bits >> 18) & 0x3F];
            out += alphabet[(bits >> 12) & 0x3F];
            out += (i - 2 < bytes.length) ? alphabet[(bits >> 6) & 0x3F] : '=';
            out += (i - 1 < bytes.length) ? alphabet[bits & 0x3F] : '=';
        }
        return out;
    }

    // ======================== AES-128-CBC ========================
    // AES S-Box
    var S = [
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
        0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16
    ];
    // Rcon
    var Rcon = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36];

    function keyExpansion(keyBytes) {
        var w = [];
        for (var i = 0; i < 16; i++) w.push(keyBytes[i]);
        for (i = 4; i < 44; i++) {
            var temp = [w[(i-1)*4], w[(i-1)*4+1], w[(i-1)*4+2], w[(i-1)*4+3]];
            if (i % 4 === 0) {
                // RotWord
                temp = [temp[1], temp[2], temp[3], temp[0]];
                // SubWord
                temp[0] = S[temp[0]];
                temp[1] = S[temp[1]];
                temp[2] = S[temp[2]];
                temp[3] = S[temp[3]];
                // XOR Rcon
                temp[0] ^= Rcon[(i/4)-1];
            }
            w.push((w[(i-4)*4] ^ temp[0]));
            w.push((w[(i-4)*4+1] ^ temp[1]));
            w.push((w[(i-4)*4+2] ^ temp[2]));
            w.push((w[(i-4)*4+3] ^ temp[3]));
        }
        return w;
    }

    function aesEncryptBlock(block, keyBytes) {
        var w = keyExpansion(keyBytes);
        var state = block.slice();

        function addRoundKey(round) {
            for (var i = 0; i < 16; i++) state[i] ^= w[round*16 + i];
        }
        function subBytes() {
            for (var i = 0; i < 16; i++) state[i] = S[state[i]];
        }
        function shiftRows() {
            var t = state[1]; state[1] = state[5]; state[5] = state[9]; state[9] = state[13]; state[13] = t;
            t = state[2]; state[2] = state[10]; state[10] = t;
            t = state[6]; state[6] = state[14]; state[14] = t;
            t = state[3]; state[3] = state[15]; state[15] = state[11]; state[11] = state[7]; state[7] = t;
        }
        function xtime(a) { return (a << 1) ^ ((a & 0x80) ? 0x11b : 0); }
        function mixColumns() {
            for (var c = 0; c < 4; c++) {
                var i0 = c*4, i1 = c*4+1, i2 = c*4+2, i3 = c*4+3;
                var s0 = state[i0], s1 = state[i1], s2 = state[i2], s3 = state[i3];
                state[i0] = xtime(s0) ^ (xtime(s1) ^ s1) ^ s2 ^ s3;
                state[i1] = s0 ^ xtime(s1) ^ (xtime(s2) ^ s2) ^ s3;
                state[i2] = s0 ^ s1 ^ xtime(s2) ^ (xtime(s3) ^ s3);
                state[i3] = (xtime(s0) ^ s0) ^ s1 ^ s2 ^ xtime(s3);
            }
        }

        addRoundKey(0);
        for (var round = 1; round <= 9; round++) {
            subBytes();
            shiftRows();
            mixColumns();
            addRoundKey(round);
        }
        subBytes();
        shiftRows();
        addRoundKey(10);
        return state;
    }

    function aesCbcEncrypt(plainBytes, keyBytes, ivBytes) {
        var padded = pkcs7Pad(plainBytes, 16);
        var result = [];
        var prev = ivBytes.slice();
        for (var i = 0; i < padded.length; i += 16) {
            var block = padded.slice(i, i+16);
            for (var j = 0; j < 16; j++) block[j] ^= prev[j];
            var enc = aesEncryptBlock(block, keyBytes);
            for (var j = 0; j < 16; j++) result.push(enc[j]);
            prev = enc.slice();
        }
        return result;
    }

    function pkcs7Pad(data, blockSize) {
        var padLen = blockSize - (data.length % blockSize);
        var out = data.slice();
        for (var i = 0; i < padLen; i++) out.push(padLen);
        return out;
    }

    // ======================== cKey 生成（AES 新版） ========================
    function calcQn(str) {
        var qn = 0;
        for (var i = 0; i < str.length; i++) {
            var code = str.charCodeAt(i);
            qn = ((qn << 5) - qn + code) >>> 0;
        }
        return qn >>> 0;
    }

    function generateCKey(cnlid, ts) {
        if (!ts) ts = Math.floor(Date.now() / 1000);
        var guid = generateGuid();
        var appVer = '3.0.37';
        var platform = '4330701';

        var base = '|' + cnlid + '|' + ts + '|' + SR + '|' + appVer + '|' + guid + '|' + platform + '|' + NN + UA_SUFFIX;
        var qn = calcQn(base);
        var encryptStr = '|' + qn + base;

        var keyBytes = strToBytes(hex2bin(AES_KEY_HEX));
        var ivBytes = strToBytes(hex2bin(AES_IV_HEX));
        var plainBytes = strToBytes(encryptStr);
        var encBytes = aesCbcEncrypt(plainBytes, keyBytes, ivBytes);
        var ckey = '--01' + bin2hex(bytesToStr(encBytes)).toUpperCase();

        return { ckey: ckey, guid: guid, params: { Timestamp: ts } };
    }

    // ======================== 请求 ========================
    function spvcode(defn) {
        var h = 1080;
        if(/4k|8k|hdr/i.test(defn)) h = 2160;
        var fr = [30,60,90,120];
        var h264 = fr.map(function(f){return f+':'+h;}).join(',');
        var h265 = fr.map(function(f){return f+':'+h;}).join(',');
        var raw = 'H('+h264+'|'+h264+');2('+h265+'|'+h265+')';
        return base64EncodeBytes(strToBytes(raw));
    }

    function makeLiveRequest(cnlid, livepid, defn, playseek) {
        var ck = generateCKey(cnlid);
        var flowid = randomUUID().toUpperCase() + '_4330701';
        var isPB = !!playseek;
        var pbTs = null;
        if(isPB) {
            var s = playseek.split('-')[0];
            var y=parseInt(s.substr(0,4)),m=parseInt(s.substr(4,2))-1,d=parseInt(s.substr(6,2)),
                h=parseInt(s.substr(8,2)),mi=parseInt(s.substr(10,2)),se=parseInt(s.substr(12,2));
            pbTs = Math.floor(new Date(y,m,d,h,mi,se).getTime()/1000);
        }

        var base = {
            atime:'120', livepid:livepid, cnlid:cnlid, appVer:'3.0.37',
            app_version:'300090', caplv:'1', cmd:'2', defn:defn, device:'iPhone',
            encryptVer:'8.1', getpreviewinfo:'0', hevclv:'33', lang:'zh-Hans_JP',
            livequeue:'0', logintype:'1', nettype:'1', newnettype:'1', newplatform:'4330701',
            platform:'4330701', sdtfrom:'v3021', spacode:'23', spaudio:'1', spdemuxer:'6',
            spdrm:'2', spdynamicrange:'7', spflv:'1', spflvaudio:'1', sphdrfps:'60',
            sphttps:'0', spvcode: spvcode(defn), spvideo:'4', stream:'1', system:'1',
            sysver:'ios18.2.1', uhd_flag:'4', cKey:ck.ckey, guid:ck.guid,
            fntick:String(ck.params.Timestamp), flowid:flowid
        };
        base.playbacktime = isPB ? String(pbTs) : '0';

        function send(p) {
            var qs = [];
            for(var k in p) qs.push(encodeURIComponent(k)+'='+encodeURIComponent(p[k]));
            var url = 'https://bkliveinfo.ysp.cctv.cn?' + qs.join('&');
            var res = ku9.request(url, 'GET', {'User-Agent':'qqlive','Accept':'application/json'}, null, true);
            if(!res || res.code!==200 || !res.body) return {s:false};
            try {
                var j = JSON.parse(res.body);
                if(j.iretcode===0) return {s:true, url:j.playurl||null};
                return {s:false};
            }catch(e){ return {s:false}; }
        }

        var r1 = send(base);
        if(r1.s && r1.url) return {s:true, url:r1.url};
        if(isPB) {
            delete base.playbacktime;
            var r2 = send(base);
            if(r2.s && r2.url) {
                var newUrl = r2.url.replace(/\/\/[^\/]+\//, '//tlivecloud-playback-cdn.ysp.cctv.cn/tcloud.cctv.com/');
                if(newUrl.indexOf('?')>=0) newUrl += '&starttime='+pbTs;
                else newUrl += '?starttime='+pbTs;
                return {s:true, url:newUrl};
            }
        }
        return {s:false};
    }

    // ======================== 主流程 ========================
    var cacheKey = 'ysp_'+id+'_'+(isLive?'live':'pb');
    var now = Math.floor(Date.now()/1000);
    var cacheTTL = isLive ? 80 : 0;
    var _cache = {};
    var playUrl = null;

    if(isLive && _cache[cacheKey] && (now - _cache[cacheKey].time) <= cacheTTL) {
        playUrl = _cache[cacheKey].url;
    } else {
        var result = makeLiveRequest(cnlid, livepid, defn, playseek);
        if(!result.s || !result.url) {
            return { url: '', msg: '获取播放地址失败' };
        }
        playUrl = result.url;
        if(isLive) _cache[cacheKey] = {url:playUrl, time:now};
    }

    if(!isLive) {
        return { url: playUrl, headers: {'User-Agent':'qqlive'} };
    }

    var m3u8Res = ku9.request(playUrl, 'GET', {'User-Agent':'qqlive'}, null, true);
    if(!m3u8Res || m3u8Res.code!==200 || !m3u8Res.body) {
        return { url: '', msg: '获取M3U8失败' };
    }
    var m3u8 = m3u8Res.body;
    var base = playUrl.substring(0, playUrl.lastIndexOf('/')+1);
    m3u8 = m3u8.replace(/^(\S+\.ts\S*)$/gm, function(match, ts) {
        if(ts.indexOf('http')===0) return ts;
        return base + ts;
    });

    return { m3u8: m3u8, headers: {'User-Agent':'qqlive'} };
}
