// ==================== 咪咕视频直播（ku9版） ====================
// 基于 migu.py 转换
// 用法：http://xxx/ku9/js/migu.js?id=cctv1

var CHANNEL_MAP = {
    "gdzj":"639731952","cctv1":"608807420","cctv2":"631780532","cctv3":"624878271",
    "cctv4":"631780421","cctv5":"641886683","cctv5p":"641886773",
    "cctv6":"624878396","cctv7":"673168121","cctv8":"624878356",
    "cctv9":"673168140","cctv10":"624878405","cctv11":"667987558",
    "cctv12":"673168185","cctv13":"608807423","cctv14":"624878440",
    "cctv15":"673168223","cctv17":"673168256","cctv4e":"608807419",
    "cctv4a":"608807416","cgtn":"609017205","cgtnf":"609006476",
    "cgtnr":"609006446","cgtna":"609154345","cgtne":"609006450",
    "cgtnjl":"609006487","dfws":"651632648","jsws":"623899368",
    "gdws":"608831231","bjws":"630287636","lnws":"630291707",
    "hbws":"962042070","jxws":"783847495","hnws":"790187291",
    "sxws":"738910838","dwqws":"608917627","hubws":"947472496",
    "jlws":"947472500","qhws":"947472506","dnws":"849116810",
    "hinws":"947472502","hxws":"849119120","nlws":"956904896",
    "btws":"956923145","nxws":"738910535","cqws":"738910914",
    "sxsws":"961023778","sszdj":"646596895","ttmlh":"629943305",
    "shdy":"637444975","sxtyxx":"956909356","wssj":"958475359",
    "kldy":"961930263","lntyxx":"962067526","tyxx":"626064707",
    "shxwzh":"651632657","shdys":"617290047","shdycj":"608780988",
    "njxwzh":"838109047","njkj":"838153729","njsb":"838151753",
    "jscs":"626064714","jsgj":"626064674","jsjy":"628008321",
    "jsys":"626064697","jszy":"626065193","jsggxw":"626064693",
    "ymkt":"626064703","sxyl":"956909362","sxdsqc":"956909358",
    "sxqq":"956909303","sxxwzx":"956909289","cftx":"956923159",
    "jdxgdy":"625703337","kzjdyp":"617432318","xpfyt":"619495952",
    "chcyy":"952383261","chcdz":"644368714","chcjt":"644368373",
    "zgtq":"959986621","cetv1":"923287154","cetv2":"923287211",
    "cetv4":"923287339","sdjy":"609154353","xmhd":"609158151",
    "xm1":"608933610","xm2":"608933640","xm3":"608934619",
    "xm4":"608934721","xm5":"608935104","xm6":"608935797",
    "xm7":"609169286","xm8":"609169287","xm9":"609169226",
    "xm10":"609169285","zqzyb":"629942228","jjkt":"614952364",
    "jddh":"629942219","xdm":"961930269","zhtc":"959986618",
    "hqly":"958475356","c":"961930369","lg":"884121956",
    "fxzl":"624878970","zxs":"708869532",
    
};

function ddCalcu(puData, pid) {
    var keys = "cdabyzwxkl";
    var now = new Date();
    var ds = String(now.getFullYear()) +
        ("0" + (now.getMonth() + 1)).slice(-2) +
        ("0" + now.getDate()).slice(-2);
    var result = [];
    var n = puData.length;
    for (var i = 0; i < Math.floor(n / 2); i++) {
        result.push(puData[n - i - 1]);
        result.push(puData[i]);
        if (i === 1) {
            result.push("v");
        } else if (i === 2) {
            var idx2 = parseInt(ds[2]) || 0;
            result.push(keys[idx2 % keys.length]);
        } else if (i === 3) {
            var idx3 = (pid.length > 6) ? parseInt(pid[6]) || 0 : 0;
            result.push(keys[idx3 % keys.length]);
        } else if (i === 4) {
            result.push("a");
        }
    }
    return result.join("");
}

function getPlayUrl(pid) {
    var timestamp = Date.now();
    var appVer = "2600034600";
    var appVerShort = appVer.substring(0, 8);
    var clientId = ku9.md5(String(timestamp));

    var headers = {
        "AppVersion": appVer,
        "TerminalId": "android",
        "X-UP-CLIENT-CHANNEL-ID": appVer + "-99000-201600010010028",
        "ClientId": clientId,
        "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36",
        "Referer": "https://www.miguvideo.com/"
    };

    if (pid !== "641886683" && pid !== "641886773") {
        headers["appCode"] = "miguvideo_default_android";
    }

    var signStr = String(timestamp) + pid + appVerShort;
    var md5Hash = ku9.md5(signStr);

    var saltNum = Math.floor(Math.random() * 1000000);
    var salt = ("000000" + saltNum).slice(-6) + "25";

    var suffix = "2cac4f2c6c3346a5b34e085725ef7e33migu" + salt.substring(0, 4);
    var sign = ku9.md5(md5Hash + suffix);

    var rateType = (pid === "608831231") ? 2 : 3;

    var params = "sign=" + encodeURIComponent(sign)
        + "&rateType=" + rateType
        + "&contId=" + encodeURIComponent(pid)
        + "&timestamp=" + timestamp
        + "&salt=" + encodeURIComponent(salt)
        + "&flvEnable=true&super4k=true&h265N=true&4kvivid=true&2Kvivid=true&vivid=2";

    var apiUrl = "https://play.miguvideo.com/playurl/v1/play/playurl?" + params;
    var resp = ku9.request(apiUrl, "GET", headers, null, true);

    if (!resp || resp.code != 200 || !resp.body) return null;

    try {
        var data = JSON.parse(resp.body);
        if (data && data.body && data.body.urlInfo) {
            var playUrl = data.body.urlInfo.url;
            if (playUrl) {
                var puMatch = playUrl.match(/[?&]puData=([^&]+)/);
                if (puMatch) {
                    var dd = ddCalcu(puMatch[1], pid);
                    if (dd) {
                        playUrl = playUrl + "&ddCalcu=" + dd + "&sv=10004&ct=android";
                    }
                }
                return playUrl;
            }
        }
    } catch (e) {}
    return null;
}

function main(item) {
    if (!item || !item.url) return { url: "" };

    var url = item.url.toString();
    var id = ku9.getQuery(url, "id");
    if (!id) return { url: "" };

    var pid = CHANNEL_MAP[id];
    if (!pid) return { url: "" };

    var playUrl = getPlayUrl(pid);
    if (!playUrl) return { url: "" };

    return {
        url: playUrl,
        headers: {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36",
            "Referer": "https://www.miguvideo.com/"
        }
    };
}
