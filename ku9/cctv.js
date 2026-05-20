/**
 * 央视频直播/回看解析 - 酷9 JS版（修复二进制Base64问题）
 * 用法：?id=频道ID (如 cctv5)
 *       ?id=频道ID&playseek=20260517120000-20260517130000 (回看)
 */
function main(item) {
    // ======================== 常量 ========================
    var DELTA = 0x9e3779b9;
    var ROUNDS = 16;
    var LOG_ROUNDS = 4;
    var SALT_LEN = 2;
    var ZERO_LEN = 7;
    var TEA_CKEY = '59b2f7cf725ef43c34fdd7c123411ed3';
    var XOR_KEY = [0x84,0x2E,0xED,0x08,0xF0,0x66,0xE6,0xEA,0x48,0xB4,0xCA,0xA9,0x91,0xED,0x6F,0xF3];
    var STANDARD_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
    var CUSTOM_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-=';

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
    function unpackN(s, off) {
        return ((s.charCodeAt(off)&0xFF)<<24) | ((s.charCodeAt(off+1)&0xFF)<<16) |
               ((s.charCodeAt(off+2)&0xFF)<<8)  | (s.charCodeAt(off+3)&0xFF);
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

    // ★ 自定义字节级 Base64 编码/解码（完全替代内置函数，确保二进制安全）
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

    function base64DecodeToBytes(str) {
        var alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
        str = str.replace(/=+$/, '');
        var bytes = [];
        for (var i = 0; i < str.length; i += 4) {
            var c1 = alphabet.indexOf(str[i] || 'A');
            var c2 = alphabet.indexOf(str[i+1] || 'A');
            var c3 = alphabet.indexOf(str[i+2] || 'A');
            var c4 = alphabet.indexOf(str[i+3] || 'A');
            var bits = (c1 << 18) | (c2 << 12) | (c3 << 6) | c4;
            bytes.push((bits >> 16) & 0xFF);
            if (str[i+2] !== '=' && i+2 < str.length) bytes.push((bits >> 8) & 0xFF);
            if (str[i+3] !== '=' && i+3 < str.length) bytes.push(bits & 0xFF);
        }
        return bytes;
    }

    // 自定义编码：先标准 Base64 编码字节，再映射到自定义字符集
    function customEncodeFromBytes(bytes) {
        var stdB64 = base64EncodeBytes(bytes);
        var map = {};
        for (var i = 0; i < STANDARD_ALPHABET.length; i++) map[STANDARD_ALPHABET[i]] = CUSTOM_ALPHABET[i];
        var out = '';
        for (var i = 0; i < stdB64.length; i++) out += map[stdB64[i]] || stdB64[i];
        return out.replace(/=+$/, '');
    }

    // 自定义解码：反向映射后得到标准 Base64，再解码为字节数组
    function customDecodeToBytes(str) {
        // 补齐等号
        while (str.length % 4 !== 0) str += '=';
        var map = {};
        for (var i = 0; i < CUSTOM_ALPHABET.length; i++) map[CUSTOM_ALPHABET[i]] = STANDARD_ALPHABET[i];
        var stdB64 = '';
        for (var i = 0; i < str.length; i++) stdB64 += map[str[i]] || str[i];
        return base64DecodeToBytes(stdB64);
    }

    // ======================== TEA / CBC ========================
    function teaEncryptECB(plain, key) {
        var y = unpackN(plain,0), z = unpackN(plain,4);
        var k0 = unpackN(key,0), k1 = unpackN(key,4), k2 = unpackN(key,8), k3 = unpackN(key,12);
        var sum = 0;
        for (var i = 0; i < ROUNDS; i++) {
            sum = (sum + DELTA) >>> 0;
            y = (y + ((((z<<4)>>>0) + k0) ^ ((z+sum)>>>0) ^ ((z>>>5) + k1))) >>> 0;
            z = (z + ((((y<<4)>>>0) + k2) ^ ((y+sum)>>>0) ^ ((y>>>5) + k3))) >>> 0;
        }
        return packN(y) + packN(z);
    }
    function teaDecryptECB(enc, key) {
        var y = unpackN(enc,0), z = unpackN(enc,4);
        var k0 = unpackN(key,0), k1 = unpackN(key,4), k2 = unpackN(key,8), k3 = unpackN(key,12);
        var sum = (DELTA << LOG_ROUNDS) >>> 0;
        for (var i = 0; i < ROUNDS; i++) {
            z = (z - ((((y<<4)>>>0) + k2) ^ ((y+sum)>>>0) ^ ((y>>>5) + k3))) >>> 0;
            y = (y - ((((z<<4)>>>0) + k0) ^ ((z+sum)>>>0) ^ ((z>>>5) + k1))) >>> 0;
            sum = (sum - DELTA) >>> 0;
        }
        return packN(y) + packN(z);
    }
    function oiSymmetryEncrypt2(data, key) {
        var nLen = data.length;
        var padLen = (nLen + 1 + SALT_LEN + ZERO_LEN) % 8;
        if (padLen) padLen = 8 - padLen;
        var out = '';
        var buf = new Array(8);
        buf[0] = (Math.floor(Math.random()*256) & 0xF8) | padLen;
        var si = 1;
        while (padLen--) buf[si++] = Math.floor(Math.random()*256);
        var ivp = new Array(8), ivc = new Array(8);
        for (var j=0;j<8;j++){ivp[j]=0;ivc[j]=0;}

        function flush() {
            for (var j=0;j<8;j++) buf[j] ^= ivc[j];
            var enc = teaEncryptECB(bytesToStr(buf), key);
            var encB = strToBytes(enc);
            for (var j=0;j<8;j++) encB[j] ^= ivp[j];
            ivp = buf.slice();
            ivc = encB.slice();
            out += bytesToStr(encB);
            si = 0;
        }
        var salt=0; while(salt<SALT_LEN){ if(si<8){buf[si++]=Math.floor(Math.random()*256);salt++;}if(si===8)flush(); }
        var pos=0; while(pos<data.length){ if(si<8){buf[si++]=data.charCodeAt(pos++);}if(si===8)flush(); }
        var zero=0; while(zero<ZERO_LEN){ if(si<8){buf[si++]=0;zero++;}if(si===8)flush(); }
        if(si>0){ while(si<8)buf[si++]=0; flush(); }
        return out;
    }
    function oiSymmetryDecrypt2(data, key) {
        if(data.length%8!==0||data.length<16) return false;
        var dest = strToBytes(teaDecryptECB(data.substr(0,8), key));
        var padLen = dest[0] & 7;
        var plainLen = data.length - 1 - padLen - SALT_LEN - ZERO_LEN;
        if(plainLen<0) return false;
        var out = new Array(plainLen), outPos=0;
        var ivp = new Array(8), ivc = strToBytes(data.substr(0,8));
        var pos=8, di=1+padLen;
        function next() {
            ivp = ivc.slice();
            ivc = strToBytes(data.substr(pos,8));
            for(var j=0;j<8;j++){ if(pos+j>=data.length)return false; dest[j]^=ivc[j]; }
            dest = strToBytes(teaDecryptECB(bytesToStr(dest), key));
            pos+=8; di=0; return true;
        }
        var salt=0; while(salt<SALT_LEN){if(di<8){di++;salt++;}else if(di===8){if(!next())return false;}}
        while(outPos<plainLen){
            if(di<8){ out[outPos++]=dest[di]^ivp[di]; di++; }
            else if(di===8){ if(!next())return false; }
        }
        return bytesToStr(out);
    }

    // ======================== cKey 加解密 ========================
    function encryptDataToCKey(data) {
        var teaKey = hex2bin(TEA_CKEY);
        var dataB = strToBytes(data);
        var checksum = calcSignature(dataB);
        var enc = oiSymmetryEncrypt2(data, teaKey);
        enc += packN(checksum);
        var xored = xorArray(strToBytes(enc));
        var ckey = '--01' + customEncodeFromBytes(xored);
        return ckey;
    }

    function buildPacket(params) {
        var d = '';
        d += hex2bin('0000004200000004000004d2');
        d += packN(params.Platform);
        d += packN(0);
        d += packN(params.Timestamp);
        d += packn(params.Sdtfrom.length) + params.Sdtfrom;
        d += packn(params.randFlag.length) + params.randFlag;
        d += packn(params.appVer.length) + params.appVer;
        d += packn(params.vid.length) + params.vid;
        d += packn(params.guid.length) + params.guid;
        d += packN(1);
        d += packN(0);
        var uid='2622783A', bid='nil';
        d += packn(uid.length)+uid;
        d += packn(bid.length)+bid;
        d += packn(params.uuid4.length)+params.uuid4;
        d += packn(bid.length)+bid;
        var ver='v0.1.000', pkg='com.cctv.yangshipin.app.iphone', plat='4330403';
        d += packn(ver.length)+ver;
        d += packn(pkg.length)+pkg;
        d += packn(plat.length)+plat;
        d += packn(11)+'ex_json_bus';
        d += packn(10)+'ex_json_vs';
        d += packn(params.ck_guard_time.length)+params.ck_guard_time;

        var buf = packn(d.length) + d;
        var sig = calcSignature(strToBytes(buf));
        return buf.substr(0,18) + packN(sig) + buf.substr(22);
    }

    function generateCKey(cnlid, ts) {
        if(!ts) ts = Math.floor(Date.now()/1000);
        var guid = generateGuid();
        var params = {
            Platform: 4330403,
            Timestamp: ts,
            Sdtfrom: 'dcgh',
            vid: cnlid,
            guid: guid,
            appVer: 'V8.22.1035.3031',
            randFlag: '_zj1A5Gh6QYcxWjIUGos2w==',
            uuid4: '57eab0c4-2c58-44c6-8ae9-dd2757525dc5',
            ck_guard_time: '1907CEBB43DD91205C0AA24CAA050DCE0EA64FEA1AB8F3D20C45B08B35952308456EE297396350DAA26DDC14'
        };
        var buf = buildPacket(params);
        var ckey = encryptDataToCKey(buf);
        return {ckey:ckey, guid:guid, params:params};
    }

    // ======================== 请求 ========================
    function spvcode(defn) {
        var h = 1080;
        if(/4k|8k|hdr/i.test(defn)) h = 2160;
        var fr = [30,60,90,120];
        var h264 = fr.map(function(f){return f+':'+h;}).join(',');
        var h265 = fr.map(function(f){return f+':'+h;}).join(',');
        var raw = 'H('+h264+'|'+h264+');2('+h265+'|'+h265+')';
        return base64EncodeBytes(strToBytes(raw)); // 自定义字节级编码
    }

    function makeLiveRequest(cnlid, livepid, defn, playseek) {
        var ck = generateCKey(cnlid);
        var flowid = randomUUID().toUpperCase() + '_4330403';
        var isPB = !!playseek;
        var pbTs = null;
        if(isPB) {
            var s = playseek.split('-')[0];
            var y=parseInt(s.substr(0,4)),m=parseInt(s.substr(4,2))-1,d=parseInt(s.substr(6,2)),
                h=parseInt(s.substr(8,2)),mi=parseInt(s.substr(10,2)),se=parseInt(s.substr(12,2));
            pbTs = Math.floor(new Date(y,m,d,h,mi,se).getTime()/1000);
        }

        var base = {
            atime:'120', livepid:livepid, cnlid:cnlid, appVer:'V8.22.1035.3031',
            app_version:'300090', caplv:'1', cmd:'2', defn:defn, device:'iPhone',
            encryptVer:'4.2', getpreviewinfo:'0', hevclv:'33', lang:'zh-Hans_JP',
            livequeue:'0', logintype:'1', nettype:'1', newnettype:'1', newplatform:'4330403',
            platform:'4330403', sdtfrom:'v3021', spacode:'23', spaudio:'1', spdemuxer:'6',
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
        // 回看直接返回播放地址
        return { url: playUrl, headers: {'User-Agent':'qqlive'} };
    }

    // 直播：获取m3u8并补全ts路径
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
