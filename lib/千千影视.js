var csp_QianQianYS = {

    HOST: "https://www.moxy.top",
    UA: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",

    init: async function(ext) {
        try {
            var resp = await req(this.HOST, {
                headers: {"User-Agent": this.UA},
                timeout: 15000,
                redirect: true,
                withRedirectUrl: true,
            });
            if (resp.url && resp.url.indexOf("moxy") === -1) {
                this.HOST = resp.url.replace(/\/+$/, "");
            }
        } catch (e) {}
    },

    homeContent: async function(filter) {
        var r = {"class": [], "list": [], "filter": {}};
        var cats = {"1":"电影","2":"连续剧","3":"综艺","4":"动漫","5":"短剧"};
        for (var k in cats) {
            r["class"].push({"type_id": k, "type_name": cats[k]});
        }
        try {
            var resp = await req(this.HOST, {
                headers: {"User-Agent": this.UA},
                timeout: 30000,
            });
            r["list"] = this._items(resp.content).slice(0, 60);
        } catch (e) {}
        return JSON.stringify(r);
    },

    homeVideoContent: async function() {
        var d = JSON.parse(await this.homeContent(false));
        return JSON.stringify({"list": d.list || []});
    },

    categoryContent: async function(tid, pg, filter, extend) {
        var pn = 1;
        try { pn = Math.max(parseInt(String(pg)) || 1, 1); } catch (e) {}
        var cid = String(tid);
        if ("12345".indexOf(cid) === -1) cid = "1";
        try {
            var url = pn > 1
                ? this.HOST + "/vodshow/" + cid + "--------" + pn + "---.html"
                : this.HOST + "/vodshow/" + cid + "-----------.html";
            var resp = await req(url, {
                headers: {"User-Agent": this.UA},
                timeout: 30000,
            });
            var items = this._items(resp.content);
            return JSON.stringify({
                "page": pn,
                "pagecount": this._pagecount(resp.content),
                "limit": 50,
                "total": items.length,
                "list": items
            });
        } catch (e) {
            return JSON.stringify({"page": pn, "pagecount": 1, "limit": 50, "total": 0, "list": []});
        }
    },

    detailContent: async function(ids) {
        var idStr = (ids && ids.length > 0) ? String(ids[0]) : "";
        var m = idStr.match(/(\d+)/);
        var vid = m ? m[1] : "";
        if (!vid) return JSON.stringify({"list": []});
        var resp;
        try {
            resp = await req(this.HOST + "/voddetail" + vid + ".html", {
                headers: {"User-Agent": this.UA},
                timeout: 30000,
            });
        } catch (e) {
            return JSON.stringify({"list": []});
        }
        var h = resp.content;
        var d = {
            "vod_id": vid, "vod_name": "", "vod_pic": "", "vod_year": "",
            "vod_area": "", "vod_class": "", "vod_director": "", "vod_actor": "",
            "vod_content": "", "vod_remarks": "", "vod_play_from": "", "vod_play_url": ""
        };
        var t1 = h.match(/<h1[^>]*>(.*?)<\/h1>/);
        if (t1) d["vod_name"] = t1[1].trim();
        if (!d["vod_name"]) {
            var t2 = h.match(/<title>(.*?)<\/title>/);
            if (t2) d["vod_name"] = t2[1].split("-")[0].trim();
        }
        var picMatch = h.match(/data-original="([^"]+)"/);
        if (picMatch) d["vod_pic"] = picMatch[1];
        var yearsArr = Array.from(h.matchAll(/<a[^>]*title="(\d{4})"/g));
        if (yearsArr.length > 0) d["vod_year"] = yearsArr[0][1];
        var areaList = ["中国大陆","中国","香港","台湾","美国","日本","韩国","英国","法国","泰国","印度"];
        var areaArr = Array.from(h.matchAll(/<a[^>]*title="([^"]*)"/g));
        for (var i = 0; i < areaArr.length; i++) {
            if (areaList.indexOf(areaArr[i][1]) !== -1) {
                d["vod_area"] = areaArr[i][1];
                break;
            }
        }
        var descM = h.match(/<div[^>]*class="[^"]*module-info-introduction-content[^"]*"[^>]*>\s*<p>(.*?)<\/p>/s);
        if (descM) d["vod_content"] = descM[1].replace(/<[^>]+>/g, "").trim().substring(0, 500);
        var infoIter = Array.from(h.matchAll(/<div[^>]*class="[^"]*module-info-item[^"]*"[^>]*>(.*?)<\/div>/gs));
        for (var i = 0; i < infoIter.length; i++) {
            var t = infoIter[i][1].replace(/<[^>]+>/g, "").trim();
            if (t.indexOf("导演") !== -1) d["vod_director"] = t.replace(/导演[：:]/, "").trim();
            else if (t.indexOf("主演") !== -1) d["vod_actor"] = t.replace(/主演[：:]/, "").trim();
            else if (t.indexOf("备注") !== -1) d["vod_remarks"] = t.replace(/备注[：:]/, "").trim();
        }
        try {
            var srcMatch = Array.from(h.matchAll(/data-dropdown-value="([^"]+)"/g));
            var sources = srcMatch.map(function(m) { return m[1]; });
            if (sources.length === 0) sources = ["默认"];
            var blocks = Array.from(h.matchAll(/<div[^>]*class="[^"]*module-play-list[^"]*"[^>]*>(.*?)<\/div>\s*<\/div>\s*<\/div>/gs));
            if (blocks.length === 0) {
                blocks = Array.from(h.matchAll(/<div[^>]*class="[^"]*module-play-list-content[^"]*"[^>]*>(.*?)<\/div>/gs));
            }
            var pf = [], pu = [];
            for (var i = 0; i < blocks.length; i++) {
                var blk = blocks[i][0];
                var epsM = Array.from(blk.matchAll(/<a[^>]*href="(\/vodplay\/[^"]+)"[^>]*>(?:<[^>]+>)*([^<]{1,20})(?:<\/[^>]+>)*<\/a>/g));
                if (epsM.length === 0) {
                    epsM = Array.from(blk.matchAll(/<a[^>]*href="(\/vodplay\/[^"]+)"[^>]*>.*?<span>(.*?)<\/span>/g));
                }
                if (epsM.length > 0) {
                    var src = i < sources.length ? sources[i] : "源" + (i + 1);
                    var el = [];
                    for (var j = 0; j < epsM.length; j++) {
                        var name = epsM[j][2].trim();
                        if (name) {
                            var href = epsM[j][1];
                            var fullUrl = href.startsWith("/") ? this.HOST + href : href;
                            el.push(name + "$" + fullUrl);
                        }
                    }
                    if (el.length > 0) {
                        pf.push(src);
                        pu.push(el.join("#"));
                    }
                }
            }
            if (pf.length > 0) {
                d["vod_play_from"] = pf.join("$$$");
                d["vod_play_url"] = pu.join("$$$");
            }
        } catch (e) {}
        return JSON.stringify({"list": [d]});
    },

    searchContent: async function(key, quick) {
        try {
            var resp = await req(this.HOST + "/vodsearch/" + encodeURIComponent(key) + "-------------.html", {
                headers: {"User-Agent": this.UA},
                timeout: 15000,
            });
            if (resp.content.length > 200) {
                return JSON.stringify({"list": this._items(resp.content).slice(0, 30)});
            }
        } catch (e) {}
        return JSON.stringify({"list": []});
    },

    playerContent: async function(flag, id, vipFlags) {
        var a = String(flag);
        var b = id ? String(id) : "";
        var url;
        if (a.indexOf("http") === 0 || a.indexOf("/vodplay/") !== -1) {
            url = a;
        } else if (b.indexOf("http") === 0 || b.indexOf("/vodplay/") !== -1) {
            url = b;
        } else if (a.startsWith("/")) {
            url = this.HOST + a;
        } else if (b.startsWith("/")) {
            url = this.HOST + b;
        } else {
            url = a;
        }
        var resp;
        try {
            resp = await req(url, {
                headers: {"User-Agent": this.UA},
                timeout: 30000,
            });
        } catch (e) {
            return JSON.stringify({"url": ""});
        }
        var pdM = resp.content.match(/player_data\s*=\s*(\{.*?\})/s);
        if (pdM) {
            try {
                var data = JSON.parse(pdM[1]);
                var u = data.url || "";
                if (u) {
                    try {
                        var real_url = decodeURIComponent(atob(u));
                    } catch (e2) {
                        var real_url = u;
                    }
                    if (real_url.indexOf("http") === 0) {
                        return JSON.stringify({"url": real_url});
                    }
                }
            } catch (e) {}
        }
        return JSON.stringify({"url": ""});
    },

    localProxy: function(param) {
        return [];
    },

    _pagecount: function(html) {
        var pc = 1;
        var last = html.match(/<a[^>]*href="[^"]*vodshow\/\d+[^"]*(\d+)---\.html"[^>]*>尾页/s);
        if (last) pc = Math.max(pc, parseInt(last[1]) || 1);
        var pl = Array.from(html.matchAll(/<a[^>]*href="[^"]*vodshow\/\d+-(\d+)/g));
        for (var i = 0; i < pl.length; i++) {
            var n = parseInt(pl[i][1]);
            if (n > 100) continue;
            pc = Math.max(pc, n);
        }
        var an = Array.from(html.matchAll(/class="[^"]*page-number[^"]*"[^>]*>\s*(\d+)\s*</g));
        for (var i = 0; i < an.length; i++) {
            pc = Math.max(pc, parseInt(an[i][1]) || 1);
        }
        return pc;
    },

    _items: function(html) {
        var HOST = this.HOST;
        var items = [], seen = {};
        function ext(href, block) {
            var v = href.match(/\/voddetail(\d+)\.html/);
            if (!v || seen[v[1]]) return null;
            seen[v[1]] = true;
            var t = block.match(/title="([^"]*)"/) || block.match(/alt="([^"]*)"/);
            if (!t) return null;
            var p = block.match(/data-original="([^"]+)"/);
            var n = block.match(/<div[^>]*class="[^"]*module-item-note[^"]*"[^>]*>([^<]+)<\/div>/);
            var fullUrl = href.startsWith("/") ? HOST + href : href;
            return {
                "vod_id": v[1],
                "vod_name": t[1],
                "vod_pic": p ? p[1] : "",
                "vod_remarks": n ? n[1].trim() : "",
                "vod_url": fullUrl
            };
        }
        var iter1 = Array.from(html.matchAll(/<a[^>]*href="(\/voddetail\d+\.html)"[^>]*title="([^"]*)"[^>]*class="[^"]*module-poster-item[^"]*"[^>]*>.*?<\/a>/gs));
        for (var i = 0; i < iter1.length; i++) {
            var item = ext(iter1[i][1], iter1[i][0]);
            if (item) items.push(item);
        }
        var iter2 = Array.from(html.matchAll(/<a[^>]*href="(\/voddetail\d+\.html)"[^>]*class="[^"]*module-card-item-poster[^"]*"[^>]*>.*?<\/a>/gs));
        for (var i = 0; i < iter2.length; i++) {
            var item = ext(iter2[i][1], iter2[i][0]);
            if (item) items.push(item);
        }
        return items;
    },
};