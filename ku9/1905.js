//识别名称：1905电影网

function main(item) {
    const url = item.url;
    var channelId = ku9.getQuery(url, "id") || "1905";

    // 1. 频道映射
    var channels = {
        'cctv6': 'LIVEOYY31H24H48NE',    // CCTV6电影频道
        '1905': 'LIVEOYY31H24H48NE',     // 1905国内电影 (同CCTV6)
        '1905b': 'LIVE8J4LTCXPI7QJ5_258' // 1905国外电影
    };

    if (channelId == "list") {
        var baseUrl = url.split('?')[0];
        return { m3u8: "#EXTM3U\n#EXTINF:-1,CCTV6电影\n" + baseUrl + "?id=cctv6\n#EXTINF:-1,1905国外电影\n" + baseUrl + "?id=1905b\n" };
    }

    var streamName = channels[channelId];
    if (!streamName) return { url: "", message: "无效的频道ID" };

    // 2. 构造参数与签名
    var salt = "689d471d9240010534b531f8409c9ac31e0e6521";
    var ts = Math.floor(Date.now() / 1000).toString();
    var playerid = ts.substring(ts.length - 4) + '12312345678';

    // 严格匹配 PHP 的 http_build_query 顺序
    var params = {
        'cid': 999999,
        'expiretime': 2000000600,
        'nonce': 2000000000,
        'page': 'https://www.1905.com',
        'playerid': playerid,
        'streamname': streamName,
        'uuid': 1
    };

    // 手动构造 URL 编码字符串以确保顺序与 PHP 一致
    var queryStr = "cid=" + params.cid + 
                   "&expiretime=" + params.expiretime + 
                   "&nonce=" + params.nonce + 
                   "&page=" + encodeURIComponent(params.page).replace(/%20/g, '+') + 
                   "&playerid=" + params.playerid + 
                   "&streamname=" + params.streamname + 
                   "&uuid=" + params.uuid;

    // 使用酷9内置的 sha1 加密
    var sign = ku9.sha1(queryStr + "." + salt);

    // 3. 发送 POST 请求
    var apiUrl = "https://profile.m1905.com/mvod/liveinfo.php";
    params['appid'] = 'W0hUwz8D'; // 补充 appid 到请求体

    var headers = {
        'Authorization': sign,
        'Content-Type': 'application/json',
        'Origin': 'https://www.1905.com',
        'Referer': 'https://www.1905.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    };

    try {
        // ku9.request 参数：url, type, headers, body
        let res = ku9.request(apiUrl, "POST", headers, JSON.stringify(params));
        
        if (res.code === 200) {
            var json = JSON.parse(res.body);
            if (json.data && json.data.quality && json.data.quality.hd) {
                // 拼接地址：host + uri + hashuri
                var host = json.data.quality.hd.host;
                var path = json.data.path.hd.uri;
                var hashuri = json.data.sign.hd.hashuri;
                
                var playURL = host + path + hashuri;

                return {
                    url: playURL,
                    headers: {
                        'User-Agent': 'Mozilla/5.0',
                        'Referer': 'https://www.1905.com/'
                    }
                };
            }
        }
        return { url: "", message: "接口获取失败" };
    } catch (e) {
        return { url: "", message: "错误: " + e.message };
    }
}