function main(item) {
    var url = item.url;
    var id = item.id || 'cctv1';
    return { url: 'http://43.136.81.155:8888/' + id, headers: { 'User-Agent': 'qqlive', 'Referer': 'https://tv.cctv.com/' } };
}
if (typeof module !== 'undefined' && module.exports) { module.exports = { main: main }; }
