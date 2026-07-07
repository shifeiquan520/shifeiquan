function main(item) {
    const id = jz.getQuery(item.url, "id") || "cctv1";
       const fmt = jz.getQuery(item.url, "fmt") || "hls";
   const n = {
   'cctv1':'484', //CCTV1综合
   'cctv2':'485', //CCTV2财经
   'cctv3':'486', //CCTV3综艺
   'cctv4':'487', //CCTV4中文国际
   'cctv4a':'501', //CCTV4中文国际-美洲
   'cctv4o':'502', //CCTV4中文国际-欧洲
   'cctv5':'488', //CCTV5体育
   'cctv5p':'489', //CCTV5+体育赛事
   'cctv6':'490', //CCTV6电影
   'cctv7':'491', //CCTV7国防军事
   'cctv8':'492', //CCTV8电视剧
   'cctv9':'493', //CCTV9纪录
   'cctv10':'494', //CCTV10科教
   'cctv11':'495', //CCTV11戏曲
   'cctv12':'496', //CCTV12社会与法
   'cctv13':'497', //CCTV13新闻
   'cctv14':'498', //CCTV14少儿
   'cctv15':'499', //CCTV15音乐
   'cctv17':'500', //CCTV17农业农村
   'bjws':'514', //北京卫视
   'dfws':'503', //东方卫视
   'tjws':'517', //天津卫视
   'cqws':'513', //重庆卫视
   'hljws':'527', //黑龙江卫视
   'jlws':'507', //吉林卫视
   'lnws':'526', //辽宁卫视
   'gsws':'528', //甘肃卫视
   'qhws':'511', //青海卫视
   'sxws':'509', //陕西卫视
   'hbws':'521', //河北卫视
   'sdws':'519', //山东卫视
   'ahws':'518', //安徽卫视
   'hnws':'522', //河南卫视
   'hubws':'510', //湖北卫视
   'hunws':'515', //湖南卫视
   'jxws':'508', //江西卫视
   'jsws':'505', //江苏卫视
   'zjws':'523', //浙江卫视
   'dnws':'524', //东南卫视
   'gdws':'504', //广东卫视
   'szws':'512', //深圳卫视
   'gxws':'520', //广西卫视
   'gzws':'525', //贵州卫视
   'scws':'516', //四川卫视   
   'xjws':'529', //新疆卫视
   'btws':'530', //兵团卫视
   'hinws':'506', //海南卫视   
 };

   
    if (!n[id]) {
                return { error: `未知的频道ID: ${id}` };

    }

    const apiUrl = "https://kzb29rda.com/prod-api/iptv/getIptvList?liveType=0&deviceType=1";
    let res;
    
    try {
        res = jz.get(apiUrl, { 'User-Agent': 'Mozilla/5.0' });
    } catch (e) {
        return { error: `Failed to fetch API data: ${e.message}` };
    }

    if (!res) {
        return { error: "Empty response from API" };
    }

    let data;
    try {
        data = JSON.parse(res).list;
    } catch (e) {
        return { error: "Failed to parse API response" };
    }

    let m3u8, flv;
    for (const v of data) {
        if (n[id] == v.id) {
            m3u8 = v.play_source_url.replace(/^https/, 'http');
            flv = m3u8.replace('.m3u8', '.flv');
            break;
        }
    }

    if (!m3u8) {
        return { error: "Stream URL not found for the specified channel" };
    }

    return {
        url: fmt === 'flv' ? flv : m3u8,
        headers: { 
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://kzb29rda.com/'
        }
    };
}
