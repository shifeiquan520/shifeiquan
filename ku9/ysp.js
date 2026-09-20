// ==================== 央视直播解析（酷9版） ====================
// 参数：id=频道名称（例如 cctv1, cctv2, bjws 等）
// 支持频道：cctv1~cctv17, cctv4k, cctv8k, cgtn系列, 各地方卫视等

// ---------- 1. 适配ku9.request ----------
var HttpBridge = {
    fetchWithHeaders: function(url, headers) {
        var resp = ku9.request(url, 'GET', headers, null, true);
        if (resp && resp.code === 200) {
            return resp.body;
        }
        return null;
    }
};

// ---------- 2. 嵌入原压缩代码（会自动解压并定义 getPlayUrl） ----------
// 注意：以下为原始压缩代码，执行后会在全局作用域生成 getPlayUrl 函数

function getPlayUrl(q){var r=(q||"cctv1").replace(/\/$/,"");var t={'cctv1':['2024078201','600001859','fhd'],'cctv2':['2024075401','600001800','fhd'],'cctv3':['2024068501','600001801','fhd'],'cctv4':['2029797101','600001814','fhd'],'cctv5':['2024078401','600001818','fhd'],'cctv5p':['2024078001','600001817','fhd'],'cctv6':['2013693901','600108442','fhd'],'cctv7':['2024072001','600004092','fhd'],'cctv8':['2029793001','600001803','fhd'],'cctv9':['2024078601','600004078','fhd'],'cctv10':['2024078701','600001805','fhd'],'cctv11':['2027248701','600001806','fhd'],'cctv12':['2027248801','600001807','fhd'],'cctv13':['2029797201','600001811','fhd'],'cctv14':['2027248901','600001809','fhd'],'cctv15':['2027249001','600001815','fhd'],'cctv16':['2027249101','600098637','fhd'],'cctv164k':['2027249301','600099502','fhd'],'cctv17':['2027249401','600001810','fhd'],'cctv4k':['2029810301','600002264','fhd'],'cctv8k':['2026774101','600156816','fhd'],'cgtn':['2024181701','600014550','fhd'],'cgtnfy':['2024181801','600084704','fhd'],'cgtney':['2024181901','600084758','fhd'],'cgtnalby':['2024182001','600084782','fhd'],'cgtnxby':['2024182101','600084744','fhd'],'cgtnwyjl':['2024182301','600084781','fhd'],'cctvfyjc':['2025637103','600099658','shd'],'cctvdyjc':['2026874203','600099655','shd'],'cctvhjjc':['2026874303','600099620','shd'],'cctvsjdl':['2026874403','600099637','shd'],'cctvfyyy':['2026874503','600099660','shd'],'cctvbqkj':['2026874603','600099649','shd'],'cctvfyzq':['2026966203','600099636','shd'],'cctvgeqwq':['2026874703','600099659','shd'],'cctvnxss':['2026874803','600099650','shd'],'cctvyswhjp':['2026874903','600099653','shd'],'cctvystq':['2026875003','600099652','shd'],'cctvdszn':['2026875103','600099656','shd'],'cctvwsjk':['2025637003','600099651','shd'],'bjws':['2024052703','600002309','fhd'],'jsws':['2024171103','600002521','fhd'],'dfws':['2024054503','600002483','fhd'],'zjws':['2024054703','600002520','fhd'],'hnws':['2024054803','600002475','fhd'],'hbws':['2024171203','600002508','fhd'],'gdws':['2024060903','600002485','fhd'],'gxws':['2024060703','600002509','fhd'],'hljws':['2029797003','600002498','fhd'],'hnws2':['2024055603','600002506','fhd'],'cqws':['2024061103','600002531','fhd'],'szws':['2024061303','600002481','fhd'],'scws':['2024061403','600002516','fhd'],'henanws':['2029797303','600002525','fhd'],'fjdnhz':['2024061503','600002484','fhd'],'gzhws':['2024061603','600002490','fhd'],'jxws':['2024061703','600002503','fhd'],'lnws':['2024171303','600002505','fhd'],'ahws':['2024171403','600002532','fhd'],'hbws2':['2024171503','600002493','fhd'],'sdws':['2029787903','600002513','fhd'],'tjws':['2019927003','600152137','fhd'],'jlws':['2025561503','600190405','fhd'],'shanxiws':['2029795103','600190400','fhd'],'nxws':['2025608503','600190737','fhd'],'nmgws':['2025561203','600190401','fhd'],'ynws':['2025561303','600190402','fhd'],'shanxiws2':['2025560803','600190407','fhd'],'qhws':['2025559103','600190406','fhd'],'xzws':['2025558003','600190403','fhd'],'cetv1':['2022823801','600171827','fhd'],'gxpd':['2029360403','600213139','fhd'],'xjws':['2019927403','600152138','fhd']};if(!t[r])return"";var u=t[r][0];var w=t[r][1];var x=t[r][2];function hexToBytes(a){var b=[];for(var i=0;i<a.length;i+=2)b.push(parseInt(a.substr(i,2),16));return b}function bytesToHex(a){var b="";for(var i=0;i<a.length;i++){var v=a[i]&0xFF;b+=(v<16?"0":"")+v.toString(16)}return b}function calcSignature(a){var b=0;for(var i=0;i<a.length;i++){b=(0x83*b+(a[i]&0xFF))&0x7FFFFFFF}return b}function teaEncryptECB(a,b){var y=((a[0]&0xFF)<<24)|((a[1]&0xFF)<<16)|((a[2]&0xFF)<<8)|(a[3]&0xFF);var z=((a[4]&0xFF)<<24)|((a[5]&0xFF)<<16)|((a[6]&0xFF)<<8)|(a[7]&0xFF);var k=[((b[0]&0xFF)<<24)|((b[1]&0xFF)<<16)|((b[2]&0xFF)<<8)|(b[3]&0xFF),((b[4]&0xFF)<<24)|((b[5]&0xFF)<<16)|((b[6]&0xFF)<<8)|(b[7]&0xFF),((b[8]&0xFF)<<24)|((b[9]&0xFF)<<16)|((b[10]&0xFF)<<8)|(b[11]&0xFF),((b[12]&0xFF)<<24)|((b[13]&0xFF)<<16)|((b[14]&0xFF)<<8)|(b[15]&0xFF)];var c=0;var d=0x9e3779b9;for(var i=0;i<16;i++){c=(c+d)|0;y=(y+((((z<<4)+k[0])^(z+c)^((z>>>5)+k[1]))|0))|0;z=(z+((((y<<4)+k[2])^(y+c)^((y>>>5)+k[3]))|0))|0}return[(y>>>24)&0xFF,(y>>>16)&0xFF,(y>>>8)&0xFF,y&0xFF,(z>>>24)&0xFF,(z>>>16)&0xFF,(z>>>8)&0xFF,z&0xFF]}function oiSymmetryEncrypt2(b,c){var d=b.length;var e=d+1+2+7;var f=e%8;if(f)f=8-f;var g=[];var h=[0,0,0,0,0,0,0,0];h[0]=(Math.floor(Math.random()*256)&0xF8)|f;var k=1;while(f>0){h[k]=Math.floor(Math.random()*256);k++;f--}var l=[0,0,0,0,0,0,0,0];var m=[0,0,0,0,0,0,0,0];function processBlock(){for(var j=0;j<8;j++)h[j]^=m[j];var a=teaEncryptECB(h,c);for(var j=0;j<8;j++)a[j]^=l[j];l=h.slice();m=a.slice();for(var j=0;j<8;j++)g.push(a[j]);k=0}var i=0;while(i<2){if(k<8){h[k]=Math.floor(Math.random()*256);k++;i++}if(k==8)processBlock()}var n=0;var o=d;while(o>0){if(k<8){h[k]=b[n];n++;k++;o--}if(k==8)processBlock()}i=0;while(i<7){if(k<8){h[k]=0;k++;i++}if(k==8)processBlock()}if(k>0){for(var j=k;j<8;j++)h[j]=0;processBlock()}return g}function packN(a){return[(a>>>24)&0xFF,(a>>>16)&0xFF,(a>>>8)&0xFF,a&0xFF]}function packn(a){return[(a>>>8)&0xFF,a&0xFF]}function strToBytes(s){var b=[];for(var i=0;i<s.length;i++)b.push(s.charCodeAt(i)&0xFF);return b}function generateCkGuardTime(a,c,d,e,f){if(!d)d='-1';if(!e)e='null';if(!f)f='null';function guardLastFive(s){s=s.toString();return s.length>=5?s.substring(s.length-5):''}var g=packN(a);var h=[guardLastFive(c),guardLastFive(e),guardLastFive(f),d];for(var i=0;i<h.length;i++){var b=strToBytes(h[i]);g=g.concat(packn(b.length),b)}var j=packn(g.length).concat(g);var k=calcSignature(j);var l=hexToBytes("110DBEC10C23E7D2E56A1CAD6914EF1B");var m=oiSymmetryEncrypt2(j,l);m=m.concat(packN(k));var n=[0xB3,0xC9,0x53,0xA0,0x69,0x13,0xAD,0x4D];for(var i=0;i<m.length;i++)m[i]^=n[i&7];return bytesToHex(m).toUpperCase()}function buildPacket(a){var c=[];c=c.concat(hexToBytes('0000004200000004000004d2'));c=c.concat(packN(a.Platform));c=c.concat(packN(0));c=c.concat(packN(a.Timestamp));var d=[a.Sdtfrom,a.randFlag,a.appVer,a.vid,a.guid];for(var i=0;i<d.length;i++){var b=strToBytes(d[i]);c=c.concat(packn(b.length),b)}c=c.concat(packN(1));c=c.concat(packN(1));d=["2622783A","nil",a.uuid4,"nil","v0.1.000","com.cctv.yangshipin.app.iphone","4330403","ex_json_bus","ex_json_vs",a.ck_guard_time];for(var i=0;i<d.length;i++){var b=strToBytes(d[i]);c=c.concat(packn(b.length),b)}var e=packn(c.length).concat(c);var f=calcSignature(e);var g=packN(f);e[18]=g[0];e[19]=g[1];e[20]=g[2];e[21]=g[3];return e}function customEncode(a){var b="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=";var c="";var i=0;while(i<a.length){var d=a[i++]&0xFF;var e=i<a.length?a[i++]&0xFF:NaN;var f=i<a.length?a[i++]&0xFF:NaN;var g=d>>2;var h=((d&3)<<4)|(isNaN(e)?0:(e>>4));var k=isNaN(e)?64:(((e&15)<<2)|(isNaN(f)?0:(f>>6)));var l=isNaN(f)?64:(f&63);c+=b.charAt(g)+b.charAt(h)+b.charAt(k)+b.charAt(l)}var m="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-=";var n="";for(var j=0;j<c.length;j++){var o=c.charAt(j);var p=b.indexOf(o);n+=m.charAt(p)}return n.replace(/=+$/,'')}function encryptDataToCKey(a){var b=hexToBytes("59b2f7cf725ef43c34fdd7c123411ed3");var c=calcSignature(a);var d=oiSymmetryEncrypt2(a,b);d=d.concat(packN(c));var e=[0x84,0x2E,0xED,0x08,0xF0,0x66,0xE6,0xEA,0x48,0xB4,0xCA,0xA9,0x91,0xED,0x6F,0xF3];var f=[];for(var i=0;i<d.length;i++)f.push(d[i]^e[i&0xF]);var g=customEncode(f);return"--01"+g}function generateGuid(){function rh(){return Math.floor(Math.random()*65536).toString(16).padStart(4,'0')}var a=rh()+rh()+rh()+rh()+rh()+rh()+rh()+rh();if(a.length!==32)a=(a+"00000000000000000000000000000000").substring(0,32);return a}function generateUUID(){function rh(a){var s="";for(var i=0;i<a;i++)s+=Math.floor(Math.random()*16).toString(16);return s}return rh(8)+"-"+rh(4)+"-4"+rh(3)+"-a"+rh(3)+"-"+rh(12)}var A=generateGuid();var B=Math.floor(Date.now()/1000);var C='_zj1A5Gh6QYcxWjIUGos2w==';var D=generateUUID();var E=generateCkGuardTime(B,A);var F={Platform:4330403,Timestamp:B,Sdtfrom:'dcgh',vid:u,guid:A,appVer:'V8.22.1035.3031',randFlag:C,uuid4:D,ck_guard_time:E};var G=buildPacket(F);var H=encryptDataToCKey(G);function generateFlowid(){return generateUUID()+"_"+4330403}var I=generateFlowid();var J={"atime":"120","livepid":w,"cnlid":u,"appVer":"V8.22.1035.3031","app_version":"300090","caplv":"1","cmd":"2","defn":x,"device":"iPhone","encryptVer":"4.2","getpreviewinfo":"0","hevclv":"33","lang":"zh-Hans_JP","livequeue":"0","logintype":"1","nettype":"1","newnettype":"1","newplatform":"4330403","platform":"4330403","sdtfrom":"v3021","spacode":"23","spaudio":"1","spdemuxer":"6","spdrm":"2","spdynamicrange":"7","spflv":"1","spflvaudio":"1","sphdrfps":"60","sphttps":"1","spvcode":"MSgzMDoyMTYwLDYwOjIxNjB8MzA6MjE2MCw2MDoyMTYwKTsyKDMwOjIxNjAsNjA6MjE2MHwzMDoyMTYwLDYwOjIxNjAp","spvideo":"4","stream":"1","system":"1","sysver":"ios18.2.1","uhd_flag":"4","cKey":H,"guid":A,"fntick":B.toString(),"flowid":I,"playbacktime":"0"};var K="";for(var k in J){if(K.length>0)K+="&";K+=encodeURIComponent(k)+"="+encodeURIComponent(J[k])}var L="https://bkliveinfo.ysp.cctv.cn?"+K;var M={"User-Agent":"qqlive","Connection":"Keep-Alive","Accept":"application/json"};var N=M;var O="";var P=HttpBridge.fetchWithHeaders(L,N);if(P){try{var Q=JSON.parse(P);if(Q.playurl){O=Q.playurl}}catch(e){}}return O}

// ---------- 3. 酷9主入口 ----------
function main(item) {
    if (!item || !item.url) {
        return { url: "" };
    }

    var url = item.url.toString();
    var id = ku9.getQuery(url, "id");
    if (!id) {
        return { url: "" };
    }

    try {
        // 获取解压后的函数（原压缩代码会定义 getPlayUrl）
        var getPlayUrlFunc = null;
        try {
            getPlayUrlFunc = getPlayUrl;
        } catch (e) {}
        if (!getPlayUrlFunc) {
            try {
                getPlayUrlFunc = eval("getPlayUrl");
            } catch (e) {}
        }
        if (!getPlayUrlFunc) {
            // 如果仍然找不到，尝试其他可能名称
            try {
                getPlayUrlFunc = playUrl;
            } catch (e) {}
        }
        if (!getPlayUrlFunc) {
            return { url: "" };
        }

        var resolvedUrl = getPlayUrlFunc(id);
        if (resolvedUrl && resolvedUrl.indexOf('http') === 0) {
            // 处理回看参数
            var playseek = ku9.getQuery(url, "playseek");
            if (playseek) {
                var parts = playseek.split('-');
                if (parts.length === 2) {
                    var start = parts[0].trim();
                    var end = parts[1].trim();
                    var separator = resolvedUrl.indexOf('?') > -1 ? '&' : '?';
                    resolvedUrl += separator + "playbackbegin=" + start + "&playbackend=" + end;
                }
            }
            return { url: resolvedUrl, headers: {"User-Agent": "qqlive"} };
        }
    } catch (e) {
        // 忽略异常
    }
    return { url: "" };
}
