function main(item) {
    let channelId = ku9.getQuery(item.url, "id");
    if (!channelId) return { url: "" };

    let tokenRes = ku9.request("https://jscn-auth-user.live.gitv.tv/v1/getAppToken", "POST", {
        "Content-Type": "application/json",
        "checksum": "e4b13e6cb63bf456e4f42e44c238f01a"
    }, '{"partnerCode":"JSCN","timestamp":"1710725285"}');
    
    if (!tokenRes?.body) return { url: "" };
    
    let token = JSON.parse(tokenRes.body)?.data?.token;
    if (!token) return { url: "" };

    let playUrlRes = ku9.request("https://jxcbn.live.gitv.tv/gitv_live/" + channelId + "/" + channelId + ".m3u8?partnerCode=JXCN&gAppChannel=XIAOMI&gMac=02:00:00:00:00:00&token=" + encodeURIComponent(token), "GET");
    
    if (!playUrlRes?.body) return { url: "" };
    
    let playUrl = JSON.parse(playUrlRes.body)?.data?.playinfo?.playurl;
    return playUrl ? { url: playUrl } : { url: "" };
}
