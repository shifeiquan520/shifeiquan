//识别名称 虎牙直播 (Huya)

function main(item) {
    const url = item.url;
    var roomId = ku9.getQuery(url, "id") || "11342412"; // 默认 ID

    // --- 1. 获取直播列表 (可选，此处仅根据 ID 解析) ---
    if (roomId === "list") {
        var baseUrl = url.split('?')[0];
        // 示例列表，可根据需要扩展
        var content = "#EXTM3U\n";
        content += "#EXTINF:-1,虎牙默认频道\n";
        content += baseUrl + "?id=11342412\n";
        return { m3u8: content };
    }

    // --- 2. 核心解析逻辑 ---
    try {
        // A. 请求虎牙移动端缓存接口
        var apiUrl = "https://mp.huya.com/cache.php?m=Live&do=profileRoom&roomid=" + roomId;
        var res = ku9.request(apiUrl, "GET", {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'
        }, "", true);
        
        var json = JSON.parse(res.body);
        if (!json.data) return { url: "", message: "未获取到房间信息" };

        var data = json.data;
        var uid = data.profileInfo.uid;
        // 获取主流名 (sStreamName)
        var streamName = data.stream.baseSteamInfoList[0].sStreamName;

        // B. 时间戳与 ID 计算
        var now = Math.floor(Date.now() / 1000);
        var seqid = uid.toString() + now.toString();
        
        // C. 签名算法 (还原 PHP 中的 md5 逻辑)
        // 计算 ss
        var ss = ku9.md5(seqid + "|huya_adr|102");
        
        // 计算 wsTime (当前时间 + 6小时后的16进制)
        var wsTime = (now + 21600).toString(16);
        
        // 计算 wsSecret: MD5(盐值 + uid + streamName + ss + wsTime)
        // 盐值 "DWq8BcJ3h6DJt6TY" 是虎牙旧版常用的 Key
        var salt = "DWq8BcJ3h6DJt6TY";
        var wsSecret = ku9.md5(salt + "_" + uid + "_" + streamName + "_" + ss + "_" + wsTime);

        // D. 拼接最终地址
        // 建议优先使用 m3u8，如果原代码是 FLV，也可以保持 FLV
        var baseUrlLink = "http://al.flv.huya.com/src/" + streamName + ".flv";
        var finalUrl = baseUrlLink + "?wsSecret=" + wsSecret + 
                       "&wsTime=" + wsTime + 
                       "&ctype=huya_adr&seqid=" + seqid + 
                       "&uid=" + uid + 
                       "&fs=bgct&ver=1&t=102";

        return {
            url: finalUrl,
            headers: {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'
            }
        };

    } catch (e) {
        return { url: "", message: "脚本解析异常: " + e.message };
    }
}