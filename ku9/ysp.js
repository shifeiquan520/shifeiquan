function main(item) {
    var url = item.url;
    var id = item.id || ku9.getQuery(url, 'id') || 'cctv1';
    var playseek = item.playseek || ku9.getQuery(url, 'playseek') || '';

    var ch = CHANNELS[id];
    if (!ch) return JSON.stringify({ url: '' });

    var cnlid = ch[0], livepid = ch[1], defn = ch[2];

    var guid = generateGuid();
    var ckeyResult = generateCKey(cnlid, guid);
    var ckey = ckeyResult.ckey;
    var params = ckeyResult.params;

    var flowid = generateFlowId();

    var spv = spvcode(defn);
    var ts = params.Timestamp;

    var reqParams = {
        atime: '120',
        livepid: livepid,
        cnlid: cnlid,
        appVer: 'V8.22.1035.3031',
        app_version: '300090',
        caplv: '1',
        cmd: '2',
        defn: defn,
        device: 'iPhone',
        encryptVer: '4.2',
        getpreviewinfo: '0',
        hevclv: '33',
        lang: 'zh-Hans_JP',
        livequeue: '0',
        logintype: '1',
        nettype: '1',
        newnettype: '1',
        newplatform: '4330403',
        platform: '4330403',
        sdtfrom: 'v3021',
        spacode: '23',
        spaudio: '1',
        spdemuxer: '6',
        spdrm: '2',
        spdynamicrange: '7',
        spflv: '1',
        spflvaudio: '1',
        sphdrfps: '60',
        sphttps: '0',
        spvcode: spv,
        spvideo: '4',
        stream: '1',
        system: '1',
        sysver: 'ios18.2.1',
        uhd_flag: '4',
        cKey: ckey,
        guid: guid,
        fntick: ts,
        flowid: flowid
    };

    var isPlayback = playseek && playseek !== '';
    var finalUrl = '';

    if (isPlayback) {
        var parts = playseek.split('-');
        if (parts.length === 2) {
            var startStr = parts[0];
            var playbackTs = parsePlaybackTime(startStr);
            if (playbackTs > 0) {
                reqParams.playbacktime = playbackTs;
                var apiUrl = buildQueryString('https://bkliveinfo.ysp.cctv.cn', reqParams);
                var headers = {
                    'User-Agent': 'qqlive',
                    'Connection': 'Keep-Alive',
                    'Accept': 'application/json'
                };
                var res = ku9.request(apiUrl, 'GET', headers, null, false);
                if (res.code == 200 && res.body) {
                    try {
                        var data = JSON.parse(res.body);
                        if (data.iretcode == 0 && data.playurl) {
                            finalUrl = processPlaybackUrl(data.playurl, playbackTs);
                            return JSON.stringify({ url: finalUrl });
                        }
                    } catch (e) {}
                }
                delete reqParams.playbacktime;
                var apiUrl2 = buildQueryString('https://bkliveinfo.ysp.cctv.cn', reqParams);
                var res2 = ku9.request(apiUrl2, 'GET', headers, null, false);
                if (res2.code == 200 && res2.body) {
                    try {
                        var data2 = JSON.parse(res2.body);
                        if (data2.iretcode == 0 && data2.playurl) {
                            finalUrl = processPlaybackUrl(data2.playurl, playbackTs);
                            return JSON.stringify({ url: finalUrl });
                        }
                    } catch (e) {}
                }
            }
        }
        return JSON.stringify({ url: '' });
    } else {
        reqParams.playbacktime = '0';
        var apiUrl = buildQueryString('https://bkliveinfo.ysp.cctv.cn', reqParams);
        var headers = {
            'User-Agent': 'qqlive',
            'Connection': 'Keep-Alive',
            'Accept': 'application/json'
        };
        var res = ku9.request(apiUrl, 'GET', headers, null, false);
        if (res.code == 200 && res.body) {
            try {
                var data = JSON.parse(res.body);
                if (data.iretcode == 0 && data.playurl) {
                    finalUrl = data.playurl;
                    return JSON.stringify({ url: finalUrl });
                }
            } catch (e) {}
        }
        return JSON.stringify({ url: '' });
    }
}

function generateGuid() {
    var hex = '0123456789abcdef';
    var s = '';
    for (var i = 0; i < 32; i++) s += hex[Math.floor(Math.random() * 16)];
    return s;
}

function generateFlowId() {
    var hex = '0123456789ABCDEF';
    var s = '';
    for (var i = 0; i < 8; i++) s += hex[Math.floor(Math.random() * 16)];
    s += '-';
    for (var i = 0; i < 4; i++) s += hex[Math.floor(Math.random() * 16)];
    s += '-';
    for (var i = 0; i < 4; i++) s += hex[Math.floor(Math.random() * 16)];
    s += '-';
    for (var i = 0; i < 4; i++) s += hex[Math.floor(Math.random() * 16)];
    s += '-';
    for (var i = 0; i < 12; i++) s += hex[Math.floor(Math.random() * 16)];
    return s + '_4330403';
}

function parsePlaybackTime(timeStr) {
    if (timeStr.length !== 14) return 0;
    var year = parseInt(timeStr.substr(0, 4), 10);
    var month = parseInt(timeStr.substr(4, 2), 10) - 1;
    var day = parseInt(timeStr.substr(6, 2), 10);
    var hour = parseInt(timeStr.substr(8, 2), 10);
    var min = parseInt(timeStr.substr(10, 2), 10);
    var sec = parseInt(timeStr.substr(12, 2), 10);
    var d = new Date(year, month, day, hour, min, sec);
    return Math.floor(d.getTime() / 1000);
}

function buildQueryString(baseUrl, params) {
    var qs = '';
    var keys = Object.keys(params);
    for (var i = 0; i < keys.length; i++) {
        if (i > 0) qs += '&';
        qs += encodeURIComponent(keys[i]) + '=' + encodeURIComponent(params[keys[i]]);
    }
    return baseUrl + '?' + qs;
}

function spvcode(defn) {
    var height = (defn && defn.match(/(4k|8k|hdr)/i)) ? 2160 : 1080;
    var rates = [30, 60, 90, 120];
    var h264 = [], h265 = [];
    for (var i = 0; i < rates.length; i++) {
        h264.push(rates[i] + ':' + height);
        h265.push(rates[i] + ':' + height);
    }
    var raw = 'H(' + h264.join(',') + '|' + h264.join(',') + ');2(' + h265.join(',') + '|' + h265.join(',') + ')';
    return b64Encode(raw);
}

function processPlaybackUrl(playurl, playbackTimestamp) {
    var parts = playurl.split('/');
    if (parts.length >= 3) {
        parts[2] = 'tlivecloud-playback-cdn.ysp.cctv.cn/tcloud.cctv.com';
        playurl = parts.join('/');
        if (playurl.indexOf('?') >= 0) {
            playurl += '&starttime=' + playbackTimestamp;
        } else {
            playurl += '?starttime=' + playbackTimestamp;
        }
    }
    return playurl;
}

var CHANNELS = {
    'cctv1': ['2024078201', '600001859', 'fhd'],
    'cctv2': ['2024075401', '600001800', 'fhd'],
    'cctv3': ['2024068501', '600001801', 'fhd'],
    'cctv4': ['2029797101', '600001814', 'fhd'],
    'cctv5': ['2024078401', '600001818', 'fhd'],
    'cctv5p': ['2024078001', '600001817', 'fhd'],
    'cctv6': ['2013693901', '600108442', 'fhd'],
    'cctv7': ['2024072001', '600004092', 'fhd'],
    'cctv8': ['2029793001', '600001803', 'fhd'],
    'cctv9': ['2024078601', '600004078', 'fhd'],
    'cctv10': ['2024078701', '600001805', 'fhd'],
    'cctv11': ['2027248701', '600001806', 'fhd'],
    'cctv12': ['2027248801', '600001807', 'fhd'],
    'cctv13': ['2029797201', '600001811', 'fhd'],
    'cctv14': ['2027248901', '600001809', 'fhd'],
    'cctv15': ['2027249001', '600001815', 'fhd'],
    'cctv16': ['2027249101', '600098637', 'fhd'],
    'cctv164k': ['2027249301', '600099502', 'fhd'],
    'cctv17': ['2027249401', '600001810', 'fhd'],
    'cctv4k': ['2029810301', '600002264', 'fhd'],
    'cctv8k': ['2026774101', '600156816', 'fhd'],
    'cgtn': ['2024181701', '600014550', 'fhd'],
    'cgtnfy': ['2024181801', '600084704', 'fhd'],
    'cgtney': ['2024181901', '600084758', 'fhd'],
    'cgtnalby': ['2024182001', '600084782', 'fhd'],
    'cgtnxby': ['2024182101', '600084744', 'fhd'],
    'cgtnwyjl': ['2024182301', '600084781', 'fhd'],
    'cctvfyjc': ['2025637103', '600099658', 'fhd'],
    'cctvdyjc': ['2026874203', '600099655', 'fhd'],
    'cctvhjjc': ['2026874303', '600099620', 'fhd'],
    'cctvsjdl': ['2026874403', '600099637', 'fhd'],
    'cctvfyyy': ['2026874503', '600099660', 'fhd'],
    'cctvbqkj': ['2026874603', '600099649', 'fhd'],
    'cctvfyzq': ['2026966203', '600099636', 'fhd'],
    'cctvgeqwq': ['2026874703', '600099659', 'fhd'],
    'cctvnxss': ['2026874803', '600099650', 'fhd'],
    'cctvyswhjp': ['2026874903', '600099653', 'fhd'],
    'cctvystq': ['2026875003', '600099652', 'fhd'],
    'cctvdszn': ['2026875103', '600099656', 'fhd'],
    'cctvwsjk': ['2025637003', '600099651', 'fhd'],
    'bjws': ['2024052703', '600002309', 'fhd'],
    'jsws': ['2024171103', '600002521', 'fhd'],
    'dfws': ['2024054503', '600002483', 'fhd'],
    'zjws': ['2024054703', '600002520', 'fhd'],
    'hnws': ['2024054803', '600002475', 'fhd'],
    'hbws': ['2024171203', '600002508', 'fhd'],
    'gdws': ['2024060903', '600002485', 'fhd'],
    'gxws': ['2024060703', '600002509', 'fhd'],
    'hljws': ['2029797003', '600002498', 'fhd'],
    'hnws2': ['2024055603', '600002506', 'fhd'],
    'cqws': ['2024061103', '600002531', 'fhd'],
    'szws': ['2024061303', '600002481', 'fhd'],
    'scws': ['2024061403', '600002516', 'fhd'],
    'henanws': ['2029797303', '600002525', 'fhd'],
    'fjdnhz': ['2024061503', '600002484', 'fhd'],
    'gzhws': ['2024061603', '600002490', 'fhd'],
    'jxws': ['2024061703', '600002503', 'fhd'],
    'lnws': ['2024171303', '600002505', 'fhd'],
    'ahws': ['2024171403', '600002532', 'fhd'],
    'hbws2': ['2024171503', '600002493', 'fhd'],
    'sdws': ['2029787903', '600002513', 'fhd'],
    'tjws': ['2019927003', '600152137', 'fhd'],
    'jlws': ['2025561503', '600190405', 'fhd'],
    'shanxiws': ['2029795103', '600190400', 'fhd'],
    'nxws': ['2025608503', '600190737', 'fhd'],
    'nmgws': ['2025561203', '600190401', 'fhd'],
    'ynws': ['2025561303', '600190402', 'fhd'],
    'shanxiws2': ['2025560803', '600190407', 'fhd'],
    'qhws': ['2025559103', '600190406', 'fhd'],
    'xzws': ['2025558003', '600190403', 'fhd'],
    'cetv1': ['2022823801', '600171827', 'fhd'],
    'xjws': ['2019927403', '600152138', 'fhd']
};

var DELTA = 0x9e3779b9;
var ROUNDS = 16;
var LOG_ROUNDS = 4;
var SALT_LEN = 2;
var ZERO_LEN = 7;
var TEA_CKEY_HEX = '59b2f7cf725ef43c34fdd7c123411ed3';

var XOR_KEY = [0x84, 0x2E, 0xED, 0x08, 0xF0, 0x66, 0xE6, 0xEA, 0x48, 0xB4, 0xCA, 0xA9, 0x91, 0xED, 0x6F, 0xF3];

var STD_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
var CUS_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-=';

function hex2bin(hex) {
    var s = '';
    for (var i = 0; i < hex.length; i += 2) {
        s += String.fromCharCode(parseInt(hex.substr(i, 2), 16));
    }
    return s;
}

function bin2hex(str) {
    var h = '';
    for (var i = 0; i < str.length; i++) {
        var c = str.charCodeAt(i).toString(16);
        if (c.length === 1) c = '0' + c;
        h += c;
    }
    return h;
}

function strToBytes(str) {
    var b = [];
    for (var i = 0; i < str.length; i++) b.push(str.charCodeAt(i));
    return b;
}

function bytesToStr(bytes) {
    var s = '';
    for (var i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
    return s;
}

function packN(val) {
    return String.fromCharCode((val >>> 24) & 0xFF, (val >>> 16) & 0xFF, (val >>> 8) & 0xFF, val & 0xFF);
}

function packn(val) {
    return String.fromCharCode((val >>> 8) & 0xFF, val & 0xFF);
}

function calcSignature(buffer) {
    var sig = 0;
    var len = buffer.length;
    for (var i = 0; i < len; i++) {
        sig = (0x83 * sig + (buffer[i] & 0xFF)) & 0x7FFFFFFF;
    }
    return sig;
}

function b64Encode(text) {
    var b = '';
    for (var i = 0; i < text.length; i += 3) {
        var n = (text.charCodeAt(i) << 16) | ((i + 1 < text.length ? text.charCodeAt(i + 1) : 0) << 8) | (i + 2 < text.length ? text.charCodeAt(i + 2) : 0);
        var c1 = STD_ALPHABET[(n >>> 18) & 0x3F];
        var c2 = STD_ALPHABET[(n >>> 12) & 0x3F];
        var c3 = i + 1 < text.length ? STD_ALPHABET[(n >>> 6) & 0x3F] : '=';
        var c4 = i + 2 < text.length ? STD_ALPHABET[n & 0x3F] : '=';
        b += c1 + c2 + c3 + c4;
    }
    return b;
}

function b64Decode(text) {
    text = text.replace(/[^A-Za-z0-9+/=]/g, '');
    var t = '';
    for (var i = 0; i < text.length; i += 4) {
        if (text.length - i < 4) break;
        var n = (STD_ALPHABET.indexOf(text[i]) << 18) | (STD_ALPHABET.indexOf(text[i + 1]) << 12) | (STD_ALPHABET.indexOf(text[i + 2]) << 6) | STD_ALPHABET.indexOf(text[i + 3]);
        t += String.fromCharCode((n >>> 16) & 0xFF);
        if (text[i + 2] !== '=') t += String.fromCharCode((n >>> 8) & 0xFF);
        if (text[i + 3] !== '=') t += String.fromCharCode(n & 0xFF);
    }
    return t;
}

function customEncode(text) {
    var encoded = b64Encode(text);
    var result = '';
    for (var i = 0; i < encoded.length; i++) {
        var idx = STD_ALPHABET.indexOf(encoded[i]);
        if (idx >= 0) result += CUS_ALPHABET[idx];
        else result += encoded[i];
    }
    result = result.replace(/=+$/, '');
    return result;
}

function customDecode(text) {
    if (!text) return '';
    var padding = 4 - (text.length % 4);
    if (padding < 4) {
        for (var i = 0; i < padding; i++) text += '=';
    }
    var translated = '';
    for (var i = 0; i < text.length; i++) {
        var idx = CUS_ALPHABET.indexOf(text[i]);
        if (idx >= 0) translated += STD_ALPHABET[idx];
        else translated += text[i];
    }
    return b64Decode(translated);
}

function xorArray(bytes) {
    var result = [];
    var len = bytes.length;
    for (var i = 0; i < len; i++) {
        result.push(bytes[i] ^ XOR_KEY[i & 0xF]);
    }
    return result;
}

function teaEncryptECB(inBuf, key) {
    while (inBuf.length < 8) inBuf += '\0';

    var v0 = ((inBuf.charCodeAt(0) << 24) | (inBuf.charCodeAt(1) << 16) | (inBuf.charCodeAt(2) << 8) | inBuf.charCodeAt(3)) >>> 0;
    var v1 = ((inBuf.charCodeAt(4) << 24) | (inBuf.charCodeAt(5) << 16) | (inBuf.charCodeAt(6) << 8) | inBuf.charCodeAt(7)) >>> 0;

    var k = [
        ((key.charCodeAt(0) << 24) | (key.charCodeAt(1) << 16) | (key.charCodeAt(2) << 8) | key.charCodeAt(3)) >>> 0,
        ((key.charCodeAt(4) << 24) | (key.charCodeAt(5) << 16) | (key.charCodeAt(6) << 8) | key.charCodeAt(7)) >>> 0,
        ((key.charCodeAt(8) << 24) | (key.charCodeAt(9) << 16) | (key.charCodeAt(10) << 8) | key.charCodeAt(11)) >>> 0,
        ((key.charCodeAt(12) << 24) | (key.charCodeAt(13) << 16) | (key.charCodeAt(14) << 8) | key.charCodeAt(15)) >>> 0
    ];

    var sum = 0;
    for (var i = 0; i < ROUNDS; i++) {
        sum = (sum + DELTA) >>> 0;
        v0 = (v0 + ((((v1 << 4) >>> 0) + k[0]) ^ (v1 + sum) ^ ((v1 >>> 5) + k[1]))) >>> 0;
        v1 = (v1 + ((((v0 << 4) >>> 0) + k[2]) ^ (v0 + sum) ^ ((v0 >>> 5) + k[3]))) >>> 0;
    }

    return String.fromCharCode(
        (v0 >>> 24) & 0xFF, (v0 >>> 16) & 0xFF, (v0 >>> 8) & 0xFF, v0 & 0xFF,
        (v1 >>> 24) & 0xFF, (v1 >>> 16) & 0xFF, (v1 >>> 8) & 0xFF, v1 & 0xFF
    );
}

function oiSymmetryEncrypt2(pInBuf, pKey) {
    var nInBufLen = pInBuf.length;
    var nPadSaltBodyZeroLen = nInBufLen + 1 + SALT_LEN + ZERO_LEN;
    var nPadlen = nPadSaltBodyZeroLen % 8;
    if (nPadlen) nPadlen = 8 - nPadlen;

    var pOutBuf = '';
    var srcBuf = [0, 0, 0, 0, 0, 0, 0, 0];
    srcBuf[0] = (Math.floor(Math.random() * 256) & 0xF8) | nPadlen;
    var src_i = 1;

    while (nPadlen > 0) {
        srcBuf[src_i] = Math.floor(Math.random() * 256);
        src_i++;
        nPadlen--;
    }

    var ivPlain = [0, 0, 0, 0, 0, 0, 0, 0];
    var ivCrypt = [0, 0, 0, 0, 0, 0, 0, 0];

    var i = 0;
    while (i < SALT_LEN) {
        if (src_i < 8) {
            srcBuf[src_i] = Math.floor(Math.random() * 256);
            src_i++;
            i++;
        }
        if (src_i === 8) {
            for (var j = 0; j < 8; j++) srcBuf[j] ^= ivCrypt[j];
            var tempOut = teaEncryptECB(bytesToStr(srcBuf), pKey);
            var tempBytes = strToBytes(tempOut);
            for (var j = 0; j < 8; j++) tempBytes[j] ^= ivPlain[j];
            ivPlain = srcBuf.slice();
            ivCrypt = tempBytes.slice();
            pOutBuf += bytesToStr(tempBytes);
            src_i = 0;
        }
    }

    var pInBufIndex = 0;
    while (nInBufLen > 0) {
        if (src_i < 8) {
            srcBuf[src_i] = pInBuf.charCodeAt(pInBufIndex);
            pInBufIndex++;
            src_i++;
            nInBufLen--;
        }
        if (src_i === 8) {
            for (var j = 0; j < 8; j++) srcBuf[j] ^= ivCrypt[j];
            var tempOut = teaEncryptECB(bytesToStr(srcBuf), pKey);
            var tempBytes = strToBytes(tempOut);
            for (var j = 0; j < 8; j++) tempBytes[j] ^= ivPlain[j];
            ivPlain = srcBuf.slice();
            ivCrypt = tempBytes.slice();
            pOutBuf += bytesToStr(tempBytes);
            src_i = 0;
        }
    }

    i = 0;
    while (i < ZERO_LEN) {
        if (src_i < 8) {
            srcBuf[src_i] = 0;
            src_i++;
            i++;
        }
        if (src_i === 8) {
            for (var j = 0; j < 8; j++) srcBuf[j] ^= ivCrypt[j];
            var tempOut = teaEncryptECB(bytesToStr(srcBuf), pKey);
            var tempBytes = strToBytes(tempOut);
            for (var j = 0; j < 8; j++) tempBytes[j] ^= ivPlain[j];
            ivPlain = srcBuf.slice();
            ivCrypt = tempBytes.slice();
            pOutBuf += bytesToStr(tempBytes);
            src_i = 0;
        }
    }

    if (src_i > 0) {
        for (var j = src_i; j < 8; j++) srcBuf[j] = 0;
        for (var j = 0; j < 8; j++) srcBuf[j] ^= ivCrypt[j];
        var tempOut = teaEncryptECB(bytesToStr(srcBuf), pKey);
        var tempBytes = strToBytes(tempOut);
        for (var j = 0; j < 8; j++) tempBytes[j] ^= ivPlain[j];
        pOutBuf += bytesToStr(tempBytes);
    }

    return pOutBuf;
}

function buildPacket(params) {
    var data = '';

    data += hex2bin('0000004200000004000004d2');
    data += packN(params.Platform);
    data += packN(0);
    data += packN(params.Timestamp);

    data += packn(params.Sdtfrom.length) + params.Sdtfrom;
    data += packn(params.randFlag.length) + params.randFlag;
    data += packn(params.appVer.length) + params.appVer;
    data += packn(params.vid.length) + params.vid;
    data += packn(params.guid.length) + params.guid;

    data += packN(1);
    data += packN(0);

    var uid = '2622783A';
    data += packn(uid.length) + uid;

    var bundleID = 'nil';
    data += packn(bundleID.length) + bundleID;

    data += packn(params.uuid4.length) + params.uuid4;
    data += packn(bundleID.length) + bundleID;

    var ckeyVersion = 'v0.1.000';
    data += packn(ckeyVersion.length) + ckeyVersion;

    var packageName = 'com.cctv.yangshipin.app.iphone';
    data += packn(packageName.length) + packageName;

    var platformStr = '4330403';
    data += packn(platformStr.length) + platformStr;

    var exJsonBus = 'ex_json_bus';
    data += packn(exJsonBus.length) + exJsonBus;

    var exJsonVs = 'ex_json_vs';
    data += packn(exJsonVs.length) + exJsonVs;

    data += packn(params.ck_guard_time.length) + params.ck_guard_time;

    var bodyLength = data.length;
    var buffer = packn(bodyLength) + data;

    var bufferBytes = strToBytes(buffer);
    var signature = calcSignature(bufferBytes);

    buffer = buffer.substr(0, 18) + packN(signature) + buffer.substr(22);

    return buffer;
}

function generateCKey(cnlid, guid) {
    var timestamp = Math.floor(Date.now() / 1000);

    var randFlag = '_zj1A5Gh6QYcxWjIUGos2w==';
    var uuid4 = '57eab0c4-2c58-44c6-8ae9-dd2757525dc5';
    var ckGuardTime = '1907CEBB43DD91205C0AA24CAA050DCE0EA64FEA1AB8F3D20C45B08B35952308456EE297396350DAA26DDC14';

    var params = {
        Platform: 4330403,
        Timestamp: timestamp,
        Sdtfrom: 'dcgh',
        vid: cnlid,
        guid: guid,
        appVer: 'V8.22.1035.3031',
        randFlag: randFlag,
        uuid4: uuid4,
        ck_guard_time: ckGuardTime
    };

    var buffer = buildPacket(params);

    var teaCkey = hex2bin(TEA_CKEY_HEX);

    var dataLen = buffer.length;

    var dataBytes = strToBytes(buffer);
    var checksum = calcSignature(dataBytes);

    var encrypted = oiSymmetryEncrypt2(buffer, teaCkey);

    var checksumBytes = packN(checksum);
    encrypted += checksumBytes;

    var encBytes = strToBytes(encrypted);
    var xorBytes = xorArray(encBytes);
    var xorEncrypted = bytesToStr(xorBytes);

    var base64Encoded = customEncode(xorEncrypted);

    return {
        ckey: '--01' + base64Encoded,
        params: params,
        buffer: buffer
    };
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        main: main,
        generateCKey: generateCKey,
        spvcode: spvcode,
        processPlaybackUrl: processPlaybackUrl
    };
}
