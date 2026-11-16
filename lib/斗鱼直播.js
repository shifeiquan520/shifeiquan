var rule = {
    title: '斗鱼直播',
    host: 'https://www.douyu.com',
    homeUrl: '/api/room/list?page=1&type=wzry',
    url: '/api/room/list?page=fypage&type=fyclass',
    class_name: '王者荣耀&英雄联盟&和平精英&主机游戏&娱乐&户外&颜值&二次元&语音&音乐&体育&科技&美食&旅游&手工&绘画&舞蹈&颜值&脱口秀',
    class_url: 'wzry&LOL&hpjy&100032&ecy&yule&yz&ecy2&yy&music&ty&tech&food&travel&handicraft&drawing&dance&yz2&talk',
    filterable: 1,
    filter_url: '{{fl.cateId}}',
    filter_def: {
        wzry: { cateId: 'wzry' },
        LOL: { cateId: 'LOL' },
        hpjy: { cateId: 'hpjy' },
        '100032': { cateId: '100032' }
    },
    filter: {
        wzry: [{ key: 'cateId', name: '分类', value: [{ n: '王者荣耀', v: 'wzry' }, { n: '英雄联盟手游', v: 'LOLM' }, { n: '和平精英', v: 'hpjy' }, { n: '穿越火线', v: 'cf' }, { n: '第五人格', v: 'dwrg' }, { n: '金铲铲之战', v: 'JGAME' }] }],
        LOL: [{ key: 'cateId', name: '分类', value: [{ n: '英雄联盟', v: 'LOL' }, { n: '云顶之弈', v: 'TFT' }, { n: 'LOL赛事', v: 'lolesports' }] }],
        hpjy: [{ key: 'cateId', name: '分类', value: [{ n: '和平精英', v: 'hpjy' }, { n: '绝地求生', v: 'pubg' }, { n: '吃鸡手游', v: 'pubgm' }] }],
        '100032': [{ key: 'cateId', name: '分类', value: [{ n: '主机游戏', v: '100032' }, { n: '单机热游', v: 'single' }, { n: '互动点播', v: 'interactive' }] }]
    },
    searchUrl: 'https://m.douyu.com/api/search/liveRoom;post',
    searchable: 2,
    quickSearch: 0,
    headers: {
        'User-Agent': 'MOBILE_UA',
        'Referer': 'https://m.douyu.com/',
        'Content-Type': 'application/json'
    },
    timeout: 5000,
    limit: 8,
    play_parse: true,
    lazy: 'js: let rid = input.match(/(\\d+)/)[1]; let apis = ["https://www.douyu.com/lapi/live/getH5Play/" + rid + "?rpos=1", "https://playweb.douyucdn.cn/lapi/live/getH5Play/" + rid + "?rpos=1"]; function tryApi(apiUrl) { try { let tt = (Date.now() / 1000).toFixed(0); let sign = md5(rid + tt + "zNzMV1y4EMxOHS6I5WKm"); let url = apiUrl + "&tt=" + tt + "&sign=" + sign; let html = request(url, { headers: { "User-Agent": "MOBILE_UA", "Referer": "https://www.douyu.com" } }); let data = JSON.parse(html); if (data.error === 0 && data.data) { let stream = data.data; let flvUrl = stream.rtmp_url + "/" + stream.rtmp_live; if (stream.rtmp_multi_bitrate && stream.rtmp_multi_bitrate.length > 0) { flvUrl = stream.rtmp_multi_bitrate[0].url; } return { jx: 0, url: flvUrl, parse: 0, header: JSON.stringify({ "user-agent": "Mozilla/5.0" }) }; } } catch (e) { log("API尝试失败: " + e.message); } return null; } for (let api of apis) { let result = tryApi(api); if (result) { input = result; return; } } try { let pageHtml = request("https://m.douyu.com/" + rid, { headers: { "User-Agent": "MOBILE_UA" } }); let match = pageHtml.match(/hls_url\\?:\\?([^?]+)/); if (match) { let hlsUrl = match[1].replace(/\\\\/g, ""); input = { jx: 0, url: hlsUrl, parse: 0, header: JSON.stringify({ "user-agent": "Mozilla/5.0" }) }; return; } } catch (e) { log("页面提取失败: " + e.message); } input = { jx: 0, url: "https://live.iill.top/douyu/" + rid, parse: 0, header: JSON.stringify({ "user-agent": "MXPlayer/1.86.0" }) };'},
    推荐: 'js: let d = []; let html = request(input); let data = JSON.parse(html); if (data.code === 0 && data.data.list) { data.data.list.forEach(it => { if (it.isLive === 1) { d.push({ url: "/" + it.rid, title: it.roomName, img: it.roomSrc, desc: "👁" + it.hn + "  🆙" + it.nickname }) } }) } setResult(d);',
    一级: 'js: let d = []; let html = request(input); let data = JSON.parse(html); if (data.code === 0 && data.data.list) { data.data.list.forEach(it => { if (it.isLive === 1) { d.push({ url: "/" + it.rid, title: it.roomName, img: it.roomSrc, desc: "👁" + it.hn + "  🆙" + it.nickname }) } }) } setResult(d);',
    二级: '*',
    搜索: 'js: let d = []; let html = post(input.split(";")[0], { body: input.split(";")[1] || "{}" }); let data = JSON.parse(html); if (data.code === 0 && data.data.list) { data.data.list.forEach(it => { d.push({ url: "/" + it.roomId, title: it.roomName, img: it.roomSrc, desc: "👁" + it.hn + "  🆙" + it.nickname }) }) } setResult(d);'
};
