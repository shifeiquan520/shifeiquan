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

function hex2bin(hex) {
    var s = '';
    for (var i = 0; i < hex.length; i += 2)
        s += String.fromCharCode(parseInt(hex.substr(i, 2), 16));
    return s;
}

function packN(v) {
    return String.fromCharCode((v >>> 24) & 255, (v >>> 16) & 255, (v >>> 8) & 255, v & 255);
}

function packn(v) {
    return String.fromCharCode((v >>> 8) & 255, v & 255);
}

function bytesToStr(b) {
    var s = '';
    for (var i = 0; i < b.length; i++) s += String.fromCharCode(b[i]);
    return s;
}

function strToBytes(s) {
    var b = [];
    for (var i = 0; i < s.length; i++) b.push(s.charCodeAt(i) & 255);
    return b;
}

function calcSignature(buffer) {
    var s = 0;
    for (var i = 0; i < buffer.length; i++) {
        s = (0x83 * s + (buffer[i] & 255)) & 0x7FFFFFFF;
    }
    return s;
}

var STD_ALPH = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
var CUS_ALPH = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-=';

function customEncode(text) {
    var encoded = btoa(text);
    var result = '';
    for (var i = 0; i < encoded.length; i++) {
        var idx = STD_ALPH.indexOf(encoded[i]);
        result += (idx >= 0) ? CUS_ALPH[idx] : encoded[i];
    }
    while (result.charAt(result.length - 1) === '=') result = result.substring(0, result.length - 1);
    return result;
}

function customDecode(text) {
    var normalized = '';
    var pad = 4 - (text.length % 4);
    if (pad < 4) { for (var i = 0; i < pad; i++) normalized += '='; }
    for (var i = 0; i < text.length; i++) {
        var idx = CUS_ALPH.indexOf(text[i]);
        normalized += (idx >= 0) ? STD_ALPH[idx] : text[i];
    }
    return atob(normalized);
}

var XOR_KEY = [0x84, 0x2E, 0xED, 0x08, 0xF0, 0x66, 0xE6, 0xEA, 0x48, 0xB4, 0xCA, 0xA9, 0x91, 0xED, 0x6F, 0xF3];

function xorArray(bytes) {
    var r = [];
    for (var i = 0; i < bytes.length; i++)
        r.push(bytes[i] ^ XOR_KEY[i & 15]);
    return r;
}

function teaEncryptECB(inBuf, key) {
    var y = ((inBuf.charCodeAt(0) << 24) | (inBuf.charCodeAt(1) << 16) | (inBuf.charCodeAt(2) << 8) | inBuf.charCodeAt(3)) >>> 0;
    var z = ((inBuf.charCodeAt(4) << 24) | (inBuf.charCodeAt(5) << 16) | (inBuf.charCodeAt(6) << 8) | inBuf.charCodeAt(7)) >>> 0;
    var k = [
        ((key.charCodeAt(0) << 24) | (key.charCodeAt(1) << 16) | (key.charCodeAt(2) << 8) | key.charCodeAt(3)) >>> 0,
        ((key.charCodeAt(4) << 24) | (key.charCodeAt(5) << 16) | (key.charCodeAt(6) << 8) | key.charCodeAt(7)) >>> 0,
        ((key.charCodeAt(8) << 24) | (key.charCodeAt(9) << 16) | (key.charCodeAt(10) << 8) | key.charCodeAt(11)) >>> 0,
        ((key.charCodeAt(12) << 24) | (key.charCodeAt(13) << 16) | (key.charCodeAt(14) << 8) | key.charCodeAt(15)) >>> 0
    ];
    var sum = 0;
    var delta = 0x9E3779B9;
    for (var i = 0; i < 16; i++) {
        sum = (sum + delta) >>> 0;
        y = (y + ((((z << 4) >>> 0) + k[0]) ^ (z + sum) ^ (((z >>> 5) >>> 0) + k[1]))) >>> 0;
        z = (z + ((((y << 4) >>> 0) + k[2]) ^ (y + sum) ^ (((y >>> 5) >>> 0) + k[3]))) >>> 0;
    }
    return String.fromCharCode((y >>> 24) & 255, (y >>> 16) & 255, (y >>> 8) & 255, y & 255) +
           String.fromCharCode((z >>> 24) & 255, (z >>> 16) & 255, (z >>> 8) & 255, z & 255);
}

function oiSymmetryEncrypt2(pInBuf, pKey) {
    var nInBufLen = pInBuf.length;
    var SALT_LEN = 2, ZERO_LEN = 7;
    var nPadSaltBodyZeroLen = nInBufLen + 1 + SALT_LEN + ZERO_LEN;
    var nPadlen = nPadSaltBodyZeroLen % 8;
    if (nPadlen) nPadlen = 8 - nPadlen;
    var pOutBuf = '';
    var src_buf = [0, 0, 0, 0, 0, 0, 0, 0];
    src_buf[0] = (Math.floor(Math.random() * 256) & 0xF8) | nPadlen;
    var src_i = 1;
    while (nPadlen) {
        src_buf[src_i] = Math.floor(Math.random() * 256);
        src_i++;
        nPadlen--;
    }
    var iv_plain = [0, 0, 0, 0, 0, 0, 0, 0];
    var iv_crypt = [0, 0, 0, 0, 0, 0, 0, 0];
    var i = 0;
    while (i < SALT_LEN) {
        if (src_i < 8) {
            src_buf[src_i] = Math.floor(Math.random() * 256);
            src_i++;
            i++;
        }
        if (src_i === 8) {
            for (var j = 0; j < 8; j++) src_buf[j] ^= iv_crypt[j];
            var temp_out = teaEncryptECB(bytesToStr(src_buf), pKey);
            var temp_bytes = strToBytes(temp_out);
            for (var j = 0; j < 8; j++) temp_bytes[j] ^= iv_plain[j];
            iv_plain = src_buf.slice();
            iv_crypt = temp_bytes.slice();
            pOutBuf += bytesToStr(temp_bytes);
            src_i = 0;
        }
    }
    var pInBufIndex = 0;
    var nLen = nInBufLen;
    while (nLen) {
        if (src_i < 8) {
            src_buf[src_i] = pInBuf.charCodeAt(pInBufIndex);
            pInBufIndex++;
            src_i++;
            nLen--;
        }
        if (src_i === 8) {
            for (var j = 0; j < 8; j++) src_buf[j] ^= iv_crypt[j];
            var temp_out = teaEncryptECB(bytesToStr(src_buf), pKey);
            var temp_bytes = strToBytes(temp_out);
            for (var j = 0; j < 8; j++) temp_bytes[j] ^= iv_plain[j];
            iv_plain = src_buf.slice();
            iv_crypt = temp_bytes.slice();
            pOutBuf += bytesToStr(temp_bytes);
            src_i = 0;
        }
    }
    i = 0;
    while (i < ZERO_LEN) {
        if (src_i < 8) {
            src_buf[src_i] = 0;
            src_i++;
            i++;
        }
        if (src_i === 8) {
            for (var j = 0; j < 8; j++) src_buf[j] ^= iv_crypt[j];
            var temp_out = teaEncryptECB(bytesToStr(src_buf), pKey);
            var temp_bytes = strToBytes(temp_out);
            for (var j = 0; j < 8; j++) temp_bytes[j] ^= iv_plain[j];
            iv_plain = src_buf.slice();
            iv_crypt = temp_bytes.slice();
            pOutBuf += bytesToStr(temp_bytes);
            src_i = 0;
        }
    }
    if (src_i > 0) {
        for (var j = src_i; j < 8; j++) src_buf[j] = 0;
        for (var j = 0; j < 8; j++) src_buf[j] ^= iv_crypt[j];
        var temp_out = teaEncryptECB(bytesToStr(src_buf), pKey);
        var temp_bytes = strToBytes(temp_out);
        for (var j = 0; j < 8; j++) temp_bytes[j] ^= iv_plain[j];
        pOutBuf += bytesToStr(temp_bytes);
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
    var params = {
        Platform: 4330403,
        Timestamp: timestamp,
        Sdtfrom: 'dcgh',
        vid: cnlid,
        guid: guid,
        appVer: 'V8.22.1035.3031',
        randFlag: '_zj1A5Gh6QYcxWjIUGos2w==',
        uuid4: '57eab0c4-2c58-44c6-8ae9-dd2757525dc5',
        ck_guard_time: '1907CEBB43DD91205C0AA24CAA050DCE0EA64FEA1AB8F3D20C45B08B35952308456EE297396350DAA26DDC14'
    };
    var buffer = buildPacket(params);
    var teaCkey = hex2bin('59b2f7cf725ef43c34fdd7c123411ed3');
    var dataBytes = strToBytes(buffer);
    var checksum = calcSignature(dataBytes);
    var encrypted = oiSymmetryEncrypt2(buffer, teaCkey);
    encrypted += packN(checksum);
    var encBytes = strToBytes(encrypted);
    var xorBytes = xorArray(encBytes);
    var xorEncrypted = bytesToStr(xorBytes);
    var base64Encoded = customEncode(xorEncrypted);
    return { ckey: '--01' + base64Encoded, params: params, buffer: buffer };
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
    var d = new Date(
        parseInt(timeStr.substr(0, 4), 10),
        parseInt(timeStr.substr(4, 2), 10) - 1,
        parseInt(timeStr.substr(6, 2), 10),
        parseInt(timeStr.substr(8, 2), 10),
        parseInt(timeStr.substr(10, 2), 10),
        parseInt(timeStr.substr(12, 2), 10)
    );
    return Math.floor(d.getTime() / 1000);
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

function main(item) {
    try {
        var urlStr = item.url || '';
        var id = item.id || '';
        if (!id) {
            var qm = urlStr.indexOf('?');
            if (qm >= 0) {
                var qs = urlStr.substring(qm + 1).split('&');
                for (var i = 0; i < qs.length; i++) {
                    var p = qs[i].split('=');
                    if (p[0] === 'id' && p.length > 1) id = p[1];
                }
            }
        }
        if (!id) id = 'cctv1';

        var playseek = item.playseek || '';
        if (!playseek) {
            var qm = urlStr.indexOf('?');
            if (qm >= 0) {
                var qs = urlStr.substring(qm + 1).split('&');
                for (var i = 0; i < qs.length; i++) {
                    var p = qs[i].split('=');
                    if (p[0] === 'playseek' && p.length > 1) playseek = p[1];
                }
            }
        }

        var ch = CHANNELS[id];
        if (!ch) return { url: '', headers: {} };

        var cnlid = ch[0], livepid = ch[1], defn = ch[2];
        var guid = generateGuid();
        var ckeyResult = generateCKey(cnlid, guid);
        var ckey = ckeyResult.ckey;
        var ts = ckeyResult.params.Timestamp;
        var flowid = generateFlowId();

        var pk = [];
        function ap(k, v) { pk[pk.length] = k + '=' + v; }
        ap('atime', '120');
        ap('livepid', livepid);
        ap('cnlid', cnlid);
        ap('appVer', 'V8.22.1035.3031');
        ap('app_version', '300090');
        ap('caplv', '1');
        ap('cmd', '2');
        ap('defn', defn);
        ap('device', 'iPhone');
        ap('encryptVer', '4.2');
        ap('getpreviewinfo', '0');
        ap('hevclv', '33');
        ap('lang', 'zh-Hans_JP');
        ap('livequeue', '0');
        ap('logintype', '1');
        ap('nettype', '1');
        ap('newnettype', '1');
        ap('newplatform', '4330403');
        ap('platform', '4330403');
        ap('sdtfrom', 'v3021');
        ap('spacode', '23');
        ap('spaudio', '1');
        ap('spdemuxer', '6');
        ap('spdrm', '2');
        ap('spdynamicrange', '7');
        ap('spflv', '1');
        ap('spflvaudio', '1');
        ap('sphdrfps', '60');
        ap('sphttps', '0');
        ap('spvcode', 'MSgzMDoyMTYwLDYwOjIxNjB8MzA6MjE2MCw2MDoyMTYwKTsyKDMwOjIxNjAsNjA6MjE2MHwzMDoyMTYwLDYwOjIxNjAp');
        ap('spvideo', '4');
        ap('stream', '1');
        ap('system', '1');
        ap('sysver', 'ios18.2.1');
        ap('uhd_flag', '4');
        ap('cKey', ckey);
        ap('guid', guid);
        ap('fntick', ts);
        ap('flowid', flowid);
        var qBase = pk.join('&');

        var reqHeaders = {
            'User-Agent': 'qqlive',
            'Accept': 'application/json'
        };

        var isPlayback = playseek && playseek !== '';
        var playurl = '';

        if (isPlayback) {
            var parts = playseek.split('-');
            if (parts.length === 2) {
                var startStr = parts[0];
                var playbackTs = parsePlaybackTime(startStr);
                if (playbackTs > 0) {
                    var apiUrl1 = 'https://bkliveinfo.ysp.cctv.cn?' + qBase + '&playbacktime=' + playbackTs;
                    var res1 = ku9.request(apiUrl1, 'GET', reqHeaders, null, false);
                    if (res1.code == 200 && res1.body) {
                        try {
                            var d1 = JSON.parse(res1.body);
                            if (d1.iretcode == 0 && d1.playurl) {
                                playurl = processPlaybackUrl(d1.playurl, playbackTs);
                            }
                        } catch (e) {}
                    }
                    if (!playurl) {
                        var apiUrl2 = 'https://bkliveinfo.ysp.cctv.cn?' + qBase;
                        var res2 = ku9.request(apiUrl2, 'GET', reqHeaders, null, false);
                        if (res2.code == 200 && res2.body) {
                            try {
                                var d2 = JSON.parse(res2.body);
                                if (d2.iretcode == 0 && d2.playurl) {
                                    playurl = processPlaybackUrl(d2.playurl, playbackTs);
                                }
                            } catch (e) {}
                        }
                    }
                }
            }
        } else {
            var apiUrl = 'https://bkliveinfo.ysp.cctv.cn?' + qBase + '&playbacktime=0';
            var res = ku9.request(apiUrl, 'GET', reqHeaders, null, false);
            if (res.code == 200 && res.body) {
                try {
                    var data = JSON.parse(res.body);
                    if (data.iretcode == 0 && data.playurl) {
                        playurl = data.playurl;
                    }
                } catch (e) {}
            }
        }

        if (playurl) {
            return { url: playurl, headers: { 'User-Agent': 'qqlive', 'Referer': 'https://tv.cctv.com/', 'UID': guid } };
        }
    } catch (e) {}

    // Fallback: call PHP backend (same real directory, strip /ku9/js/ marker)
    try {
        var cleanUrl = urlStr;
        cleanUrl = cleanUrl.replace(/\/k-web\/ku9\/js\//i, '/');
        cleanUrl = cleanUrl.replace(/\/ku9\/js\//i, '/');
        var lastSlash = cleanUrl.lastIndexOf('/');
        var baseDir = lastSlash >= 0 ? cleanUrl.substring(0, lastSlash + 1) : '';
        var qmIdx = cleanUrl.indexOf('?');
        var qStr = qmIdx >= 0 ? cleanUrl.substring(qmIdx) : '';
        var phpUrl = baseDir + 'ysp.php' + qStr;
        return { url: phpUrl, headers: { 'User-Agent': 'qqlive', 'Referer': 'https://tv.cctv.com/' } };
    } catch (e) {
        return { url: 'http://43.136.81.155:8888/' + id, headers: { 'User-Agent': 'qqlive' } };
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { main: main, generateCKey: generateCKey, processPlaybackUrl: processPlaybackUrl };
}
