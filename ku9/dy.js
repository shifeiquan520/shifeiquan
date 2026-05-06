//识别名称 斗鱼直播 (Douyu)
//优化说明：修复签名逻辑、增强异常处理、优化代码结构、兼容最新接口规则

function main(item) {
    const url = item.url;
    var roomId = ku9.getQuery(url, "id");

    // --- 1. 获取直播列表 (默认展示“颜值”板块) ---
    if (roomId === "list" || !roomId) {
        var baseUrl = url.split('?')[0];
        // 颜值区 ID: 2_208
        var listUrl = "https://www.douyu.com/gapi/rknc/directory/mixListV1/2_208/1";
        try {
            var res = ku9.request(listUrl, "GET", {}, "", true);
            var data = JSON.parse(res.body);
            
            var content = "#EXTM3U\n";
            if (data && data.data && data.data.rl) {
                data.data.rl.forEach(function(room) {
                    var title = room.nn + " - " + room.rn;
                    content += "#EXTINF:-1 tvg-logo=\"" + room.av + "\" group-title=\"" + room.c2name + "\"," + title + "\n";
                    content += baseUrl + "?id=" + room.rid + "\n";
                });
            }
            return { m3u8: content };
        } catch (e) {
            return { m3u8: "#EXTM3U\n#EXTINF:-1,获取直播列表失败\n" };
        }
    }

    // --- 2. 工具函数：MD5 逻辑 ---
    function getMD5(str) {
        return ku9.md5(str);
    }

    // --- 3. 核心解析逻辑 ---
    try {
        // 校验房间ID合法性
        if (!roomId || isNaN(roomId)) {
            return { url: "", message: "无效的房间ID" };
        }

        // A. 生成随机 did (32位十六进制)
        var did = getMD5(Math.random().toString() + Date.now().toString());
        
        var commonHeaders = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Referer': 'https://www.douyu.com/' + roomId,
            'X-Requested-With': 'XMLHttpRequest',
            'Cookie': 'dy_did=' + did
        };

        // B. 获取加密参数 (WebSec 获取 key/rand_str)
        var encUrl = "https://www.douyu.com/wgapi/livenc/liveweb/websec/getEncryption?did=" + did;
        var encRes = ku9.request(encUrl, "GET", commonHeaders, "", true);
        
        // 处理请求异常
        if (!encRes || !encRes.body) {
            return { url: "", message: "加密接口请求失败" };
        }
        
        var encJson = JSON.parse(encRes.body);

        if (!encJson || encJson.error !== 0) {
            return { url: "", message: "无法获取加密配置：" + (encJson.msg || "未知错误") };
        }

        var keyData = encJson.data;
        // 校验加密参数完整性
        if (!keyData.rand_str || !keyData.key || !keyData.enc_data || !keyData.enc_time) {
            return { url: "", message: "加密参数不完整" };
        }

        var timestamp = Math.floor(Date.now() / 1000);

        // C. 计算 Auth 签名 (斗鱼官方标准逻辑)
        var u = keyData.rand_str;
        var key = keyData.key;
        // 循环加密：严格按照 enc_time 次数执行
        for (var i = 0; i < keyData.enc_time; i++) {
            u = getMD5(u + key);
        }
        // 最终签名：标准拼接方式 u + key + roomId + timestamp
        var auth = getMD5(u + key + roomId + timestamp);

        // D. 请求 H5 播放接口（POST表单格式）
        var playApi = "https://www.douyu.com/lapi/live/getH5PlayV1/" + roomId;
        var postFields = "enc_data=" + encodeURIComponent(keyData.enc_data) + 
                         "&tt=" + timestamp + 
                         "&did=" + did + 
                         "&auth=" + auth + 
                         "&cdn=&rate=0&hevc=0&fa=0&ive=0";

        var playRes = ku9.request(playApi, "POST", 
            Object.assign({}, commonHeaders, { 
                'Content-Type': 'application/x-www-form-urlencoded' 
            }), 
            postFields, true);

        // 处理播放接口请求异常
        if (!playRes || !playRes.body) {
            return { url: "", message: "播放接口请求失败" };
        }

        var playJson = JSON.parse(playRes.body);

        if (!playJson || playJson.error !== 0) {
            return { url: "", message: "播放失败：" + (playJson.msg || "主播未开播/房间不存在") };
        }

        // E. 提取最终播放链接（优先HLS，兼容多清晰度）
        var streamData = playJson.data;
        var finalUrl = "";

        // 优先使用 m3u8 (HLS) 流媒体格式
        if (streamData.hls_url) {
            finalUrl = streamData.hls_url;
        } 
        // 兼容备用RTMP地址
        else if (streamData.rtmp_url && streamData.rtmp_live) {
            finalUrl = streamData.rtmp_url + '/' + streamData.rtmp_live;
        }

        if (finalUrl) {
            return {
                url: finalUrl,
                headers: {
                    'User-Agent': commonHeaders['User-Agent'],
                    'Referer': 'https://www.douyu.com/'
                }
            };
        } else {
            return { url: "", message: "未获取到可用的播放地址" };
        }

    } catch (e) {
        // 精准输出异常信息，方便排查问题
        return { url: "", message: "解析异常：" + (e.message || "未知错误") };
    }
}