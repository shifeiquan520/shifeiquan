function main(item) {
    const url = item.url;
    
    let id = ku9.getQuery(url, 'id');
    let cid = ku9.getQuery(url, 'cid');
    let playseek = ku9.getQuery(url, 'playseek');
    let starttime = ku9.getQuery(url, 'starttime');
    let endtime = ku9.getQuery(url, 'endtime');
    let ip = ku9.getQuery(url, 'ip');
    
    if (!id) id = ku9.getQuery(url, 'Contentid') || '3000000020000031315';
    if (!cid) cid = ku9.getQuery(url, 'channel-id') || 'FifastbLive';
    if (!ip) ip = '36.155.98.21';
    
    let finalUrl = '';
    
    if (playseek) {

        const times = playseek.split('-');
        if (times.length === 2) {
            const start = convertDateTimeFormat(times[0]);
            const end = convertDateTimeFormat(times[1]);
            finalUrl = createM3u8Url(ip, id, cid, start, end);
        } else {

            finalUrl = createM3u8Url(ip, id, cid);
        }
    } else if (starttime && endtime) {

        finalUrl = createM3u8Url(ip, id, cid, starttime, endtime);
    } else {
  
        finalUrl = createM3u8Url(ip, id, cid);
    }
    
   
    return JSON.stringify({ url: finalUrl });
}


function createM3u8Url(ip, id, cid, start, end) {

    const isPlayback = start && end;
    const pcode = isPlayback ? '000000002000' : '000000001000';
    const livemode = isPlayback ? '4' : '1';
    

    let url = `http://${ip}/gslbserv.itv.cmvideo.cn/${pcode}/${id}/1.m3u8?channel-id=${cid}&Contentid=${id}&livemode=${livemode}&stbId=m`;
    

    if (isPlayback) {
        url += `&starttime=${start}&endtime=${end}`;
    }
    
    return url;
}


function convertDateTimeFormat(dateTimeStr) {
    if (dateTimeStr.length !== 14) {

        return dateTimeStr;
    }
    const datePart = dateTimeStr.substring(0, 8);  
    const timePart = dateTimeStr.substring(8);     

    return datePart + 'T' + timePart + '.00Z';
}