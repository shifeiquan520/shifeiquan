function main(item) {
    var urlStr = item.url || '';
    var id = item.id || '';
    if (!id) {
        var qm = urlStr.indexOf('?');
        if (qm >= 0) {
            var qs = urlStr.substring(qm + 1).split('&');
            for (var i = 0; i < qs.length; i++) {
                var p = qs[i].split('=');
                if (p[0] === 'id' && p.length > 1) id = p[1];
            }
        }
    }
    if (!id) id = 'cctv1';

    var playseek = item.playseek || '';
    if (!playseek) {
        var qm = urlStr.indexOf('?');
        if (qm >= 0) {
            var qs = urlStr.substring(qm + 1).split('&');
            for (var i = 0; i < qs.length; i++) {
                var p = qs[i].split('=');
                if (p[0] === 'playseek' && p.length > 1) playseek = p[1];
            }
        }
    }

    // Strip ku9 markers (/ku9/js/ and /k-web/ku9/js/) to get the real URL path
    var cleanUrl = urlStr;
    cleanUrl = cleanUrl.replace(/\/k-web\/ku9\/js\//i, '/');
    cleanUrl = cleanUrl.replace(/\/ku9\/js\//i, '/');

    var lastSlash = cleanUrl.lastIndexOf('/');
    var baseDir = lastSlash >= 0 ? cleanUrl.substring(0, lastSlash + 1) : '';
    var qmIdx = cleanUrl.indexOf('?');
    var qStr = qmIdx >= 0 ? cleanUrl.substring(qmIdx) : '';
    var phpUrl = baseDir + 'ysp.php' + qStr;
    if (playseek) {
        phpUrl += (phpUrl.indexOf('?') >= 0 ? '&' : '?') + 'playseek=' + playseek;
    }

    return { url: phpUrl, headers: { 'User-Agent': 'qqlive', 'Referer': 'https://tv.cctv.com/' } };
}
if (typeof module !== 'undefined' && module.exports) { module.exports = { main: main }; }
