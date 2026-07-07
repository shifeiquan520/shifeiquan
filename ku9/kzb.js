function main(item) {
    // 根据频道ID前缀或类型动态选择API
    const isCCTV = item.id && item.id.startsWith('cctv');
    const liveType = isCCTV ? 1 : 2;
    const apiUrl = "https://kzb001.net/prod-api/iptv/getIptvList?liveType=" + liveType + "&deviceType=1";
    
    const res = ku9.request(apiUrl);
    
    if (res.code !== 200) {
        return { error: "API请求失败（状态码 " + res.code + "）" };
    }
    
    try {
        const data = JSON.parse(res.body);
        if (data.code !== "0") {
            return { error: "API错误：" + (data.msg || "未知错误") };
        }
        
        const list = data.list;
        // 优先按 play_source_code 匹配，兼容原逻辑
        let target = list.find(ch => ch.play_source_code === item.id);
        
        // 如果没找到，尝试按 play_source_name 匹配（兼容卫视名称传入）
        if (!target) {
            target = list.find(ch => ch.play_source_name === item.id);
        }
        
        if (!target) {
            return { error: "未找到ID为 " + item.id + " 的频道" };
        }
        
        return {
            url: target.play_source_url
        };
        
    } catch (e) {
        return { error: "数据解析失败" };
    }
}
