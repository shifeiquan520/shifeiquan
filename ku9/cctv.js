// 引用加密库（用于 HMAC-MD5）
const CryptoJS = require("crypto");

// 生成设备 ID（COOCAA_ + UUID v4）
function generateDeviceId() {
    function randomHex(len) {
        let result = '';
        for (let i = 0; i < len; i++) {
            result += Math.floor(Math.random() * 16).toString(16);
        }
        return result;
    }
    const parts = [
        randomHex(8),
        randomHex(4),
        '4' + randomHex(3),
        ((Math.floor(Math.random() * 4) + 8).toString(16)) + randomHex(3),
        randomHex(12)
    ];
    return 'COOCAA_' + parts.join('-');
}

function main(item) {
    // 1. 获取频道 ID
    const id = ku9.getQuery(item.url, "id");
    if (!id) {
        return { url: "", msg: "缺少频道 ID 参数" };
    }

    // 2. 频道映射表（与 PHP 完全一致）
    const channels = {
        'cctv1': 165, 'cctv2': 166, 'cctv4': 167, 'cctv7': 168,
        'cctv9': 169, 'cctv10': 170, 'cctv11': 171, 'cctv12': 172,
        'cctv13': 173, 'cctv14': 174, 'cctv15': 175, 'cctv17': 176,
        'cetv1': 204, 'cetv2': 206, 'cetv4': 218,
        'bjws': 196, 'dfws': 179, 'tjws': 191, 'cqws': 195,
        'hljws': 188, 'jlws': 210, 'lnws': 194, 'nmws': 213,
        'nxws': 203, 'gsws': 212, 'qhws': 202, 'sxws': 201,
        'hbws': 183, 'sxiws': 211, 'sdws': 185, 'ahws': 190,
        'hnws': 198, 'hubws': 186, 'hunws': 180, 'jxws': 193,
        'jsws': 181, 'zjws': 182, 'dnws': 155, 'hxws': 163,
        'xmws': 164, 'gdws': 184, 'szws': 187, 'gxws': 200,
        'ynws': 197, 'gzws': 189, 'scws': 192, 'xjws': 214,
        'btws': 215, 'xzws': 216, 'hinws': 199, 'ssws': 217,
        'kkse': 209, 'dfcj': 227, 'dmxc': 222, 'dsjc': 220,
        'dcwt': 219, 'fztd': 226, 'ly': 225, 'jsxt': 40,
        'shss': 230, 'yxfy': 224, 'jykt': 208, 'klcd': 229,
        'fjzh': 154, 'fjxw': 157, 'fjwt': 159, 'fjse': 162,
        'jjkt': 223
    };

    if (!channels[id]) {
        return { url: "", msg: "无效的频道 ID" };
    }
    const channelId = channels[id];

    // 3. 准备公共参数
    const salt = "557f1d838112de4fc349b8558781fe17";
    const timestamp = Math.floor(Date.now() / 1000);
    const deviceId = generateDeviceId();

    // 4. 第一步：获取 clientID
    const param = `deviceid=${deviceId}&market=coocaa&timestamp=${timestamp}`;
    const signature = CryptoJS.HmacMD5(param, salt).toString(); // HMAC-MD5 签名
    const url1 = `https://kylinapi.bbtv.cn/5g/v1/client-id-by-region?${param}&signature=${signature}`;

    const res1 = ku9.request(url1, "GET", null, "", true);
    if (!res1 || res1.code !== 200) {
        return { url: "", msg: "获取 clientID 失败" };
    }

    let data1;
    try {
        data1 = JSON.parse(res1.body);
    } catch (e) {
        return { url: "", msg: "解析 clientID 响应失败" };
    }
    const clientID = data1.clientID;
    if (!clientID) {
        return { url: "", msg: "clientID 为空" };
    }

    // 5. 第二步：获取播放地址
    const url2 = `https://kylinapi.bbtv.cn/5g/v1/tv/now/${channelId}?client=${clientID}`;
    const sign2 = ku9.md5(timestamp + salt);
    const headers2 = {
        "timestamp": timestamp.toString(),
        "sign": sign2
    };

    const res2 = ku9.request(url2, "GET", headers2, "", true);
    if (!res2 || res2.code !== 200) {
        return { url: "", msg: "获取播放地址失败" };
    }

    let data2;
    try {
        data2 = JSON.parse(res2.body);
    } catch (e) {
        return { url: "", msg: "解析播放地址响应失败" };
    }
    let playUrl = data2.playUrl;
    if (!playUrl) {
        return { url: "", msg: "播放地址为空" };
    }

    // 6. 提取 m3u8 地址（去掉 &userid 及其后参数）
    const m3u8 = playUrl.split('&userid')[0];

    // 可选：添加常用请求头，避免部分服务器检查 UA
    const headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    };

    return { url: m3u8, headers: headers };
}
