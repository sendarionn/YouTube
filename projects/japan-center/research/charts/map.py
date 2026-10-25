"""中心点を一覧できる HTML の地図（output/japan-center/research/centers_map.html）を作る

- 外部のライブラリや地図タイルを使わない単独の HTML（地形は地球地図日本の陸地を簡略化して埋め込む）
- 投影は計算と同じランベルト正積方位図法（中心 北緯36度・東経137度）
- 分類ごとに色と形を変え、分類・分野で絞り込める。点を選ぶと名称・定義・所在地・出典などを表示する
- 人口重心の推移（1965〜2020年）を線で、日本標準時子午線（東経135度）を経線で示す
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import geo  # noqa: E402
from geometry_centers import islands  # noqa: E402

OUT = geo.REPO / "output" / "japan-center" / "research"
SOURCES = Path(__file__).resolve().parents[1] / "sources.md"

CATEGORY_STYLE = {  # 分類：(色の変数名, 形)
    "幾何学的中心": ("c1", "diamond"),
    "分布の重心": ("c2", "circle"),
    "ネットワークの中心": ("c3", "square"),
    "アクセスの中心": ("c4", "triangle"),
    "制度的中心": ("c5", "square"),
    "制度的・歴史的中心": ("c6", "triangle"),
    "象徴的・通称的中心": ("c7", "star"),
}


def land_paths(min_km2=3, tol=800):
    paths = []
    for p in islands():
        if p.area < min_km2 * 1e6:
            continue
        s = p.simplify(tol)
        c = np.asarray(s.exterior.coords) / 1000
        paths.append("M" + "L".join(f"{x:.1f},{-y:.1f}" for x, y in c) + "Z")
    return paths


def xy(lon, lat):
    x, y = geo.TO_XY.transform(lon, lat)
    return round(x / 1000, 2), round(-y / 1000, 2)


def main():
    c = pd.read_csv(geo.DATA / "centers.csv")
    pts = []
    for _, r in c.dropna(subset=["lat"]).iterrows():
        x, y = xy(r["lon"], r["lat"])
        rec = {k: (None if pd.isna(v) else v) for k, v in r.items()}
        rec.update(x=x, y=y)
        pts.append(rec)
    others = c[c["lat"].isna()]
    hist = pd.read_csv(geo.DATA / "pop_centroid_history.csv")
    hist = hist[~((hist["year"] == 2000) & (hist["method"] == "2005年からの方式"))]
    track = [dict(year=int(r["year"]), x=xy(r["lon"], r["lat"])[0], y=xy(r["lon"], r["lat"])[1]) for _, r in hist.iterrows()]
    meridian = [xy(135, lat) for lat in np.arange(30, 46.01, 0.5)]
    def box(xs, ys, pad):
        x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
        return dict(x=x0, y=y0, w=x1 - x0, h=y1 - y0)
    views = dict(all=box([p["x"] for p in pts] + [-1300, 1500], [p["y"] for p in pts] + [-1080, 1720], 60),
                 main=box([-900, 1000], [-1080, 720], 40),
                 center=box([p["x"] for p in pts if abs(p["x"]) < 400 and abs(p["y"]) < 400],
                            [p["y"] for p in pts if abs(p["x"]) < 400 and abs(p["y"]) < 400], 40),
                 track=box([t["x"] for t in track], [t["y"] for t in track], 6))
    data = dict(land=land_paths(), points=pts, track=track, meridian=meridian, views=views,
                categories={k: v for k, v in CATEGORY_STYLE.items()},
                regions=json.loads(others.to_json(orient="records", force_ascii=False)))
    html = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "centers_map.html").write_text(html)
    print(OUT / "centers_map.html", f"{len(html) / 1024:.0f} KB", len(pts), "点")


TEMPLATE = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>日本の中心マップ</title>
<style>
:root{--bg:#f7f7f5;--panel:#ffffff;--ink:#1d1d1f;--sub:#5f6368;--line:#d9d9d6;--land:#e6e4dd;--landline:#b9b5aa;--sea:#eef3f6;
--c1:#3b6fb6;--c2:#d9822b;--c3:#2a9d8f;--c4:#8e5cc4;--c5:#5a6472;--c6:#b5472f;--c7:#c9a227;--track:#d9822b}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#17181a;--panel:#202124;--ink:#ececec;--sub:#a5a8ad;--line:#3a3c40;
--land:#2f3134;--landline:#4b4e53;--sea:#1b2024;--c1:#6d9be0;--c2:#f0a050;--c3:#4cc2b2;--c4:#b38be6;--c5:#9aa4b2;--c6:#e0735a;--c7:#e3c14f;--track:#f0a050}}
:root[data-theme="dark"]{--bg:#17181a;--panel:#202124;--ink:#ececec;--sub:#a5a8ad;--line:#3a3c40;--land:#2f3134;--landline:#4b4e53;--sea:#1b2024;
--c1:#6d9be0;--c2:#f0a050;--c3:#4cc2b2;--c4:#b38be6;--c5:#9aa4b2;--c6:#e0735a;--c7:#e3c14f;--track:#f0a050}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.6 "Hiragino Sans","Noto Sans JP",system-ui,sans-serif}
.wrap{display:grid;grid-template-columns:280px 1fr 340px;height:100vh}
aside{background:var(--panel);border-right:1px solid var(--line);padding:16px;overflow:auto}
#info{border-right:0;border-left:1px solid var(--line)}
h1{font-size:17px;margin:0 0 12px}
h2{font-size:13px;color:var(--sub);margin:16px 0 6px;font-weight:600}
label{display:flex;align-items:center;gap:8px;padding:2px 0;cursor:pointer}
select,button{font:inherit;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:4px 8px}
button{cursor:pointer}
.count{color:var(--sub);margin-left:auto;font-variant-numeric:tabular-nums}
#mapbox{position:relative;overflow:hidden;background:var(--sea)}
svg{width:100%;height:100%;display:block;touch-action:none}
.land{fill:var(--land);stroke:var(--landline);stroke-width:.6;vector-effect:non-scaling-stroke}
.meridian{stroke:var(--sub);stroke-dasharray:4 4;stroke-width:1;fill:none;vector-effect:non-scaling-stroke}
.track{stroke:var(--track);stroke-width:2;fill:none;vector-effect:non-scaling-stroke}
.pt{cursor:pointer;stroke:var(--panel);stroke-width:1.2;vector-effect:non-scaling-stroke}
.pt.sel{stroke:var(--ink);stroke-width:2.5}
.zoom{position:absolute;right:12px;top:12px;display:flex;flex-direction:column;gap:6px}
.zoom button{width:34px;height:34px;padding:0;background:var(--panel)}
.legend-swatch{width:12px;height:12px;flex:none}
dl{margin:0}dt{color:var(--sub);font-size:12px;margin-top:10px}dd{margin:2px 0 0;overflow-wrap:anywhere}
.muted{color:var(--sub)}
table{border-collapse:collapse;width:100%;font-size:12px}td{padding:3px 4px;border-top:1px solid var(--line);vertical-align:top}
@media (max-width:900px){.wrap{grid-template-columns:1fr;grid-template-rows:auto 60vh auto;height:auto}
aside,#info{border:0;border-bottom:1px solid var(--line)}}
</style>
</head>
<body>
<div class="wrap">
<aside>
<h1>日本の中心マップ</h1>
<h2>分類</h2><div id="cats"></div>
<h2>分野</h2><select id="field"><option value="">すべて</option></select>
<h2>表示</h2>
<label><input type="checkbox" id="showTrack" checked>人口重心の推移（1965〜2020年）</label>
<label><input type="checkbox" id="showMeridian" checked>日本標準時子午線（東経135度）</label>
<h2>拡大</h2>
<button data-view="all">全域</button> <button data-view="main">主要4島</button> <button data-view="center">点の集中域</button> <button data-view="track">人口重心の推移</button>
<h2>点にならない中心（最大集積地など）</h2><table id="regions"></table>
</aside>
<div id="mapbox"><svg id="map"><g id="vp"></g></svg>
<div class="zoom"><button id="zin" aria-label="拡大">＋</button><button id="zout" aria-label="縮小">−</button></div></div>
<aside id="info"><p class="muted">点を選ぶと、名称・定義・所在地・出典を表示します</p></aside>
</div>
<script>
const D=__DATA__;
const NS="http://www.w3.org/2000/svg";
const svg=document.getElementById("map"),vp=document.getElementById("vp");
const el=(t,a={},p=vp)=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);p.appendChild(e);return e};
D.land.forEach(d=>el("path",{d,class:"land"}));
const mer=el("polyline",{points:D.meridian.map(p=>p.join(",")).join(" "),class:"meridian"});
const trk=el("g");
el("polyline",{points:D.track.map(p=>p.x+","+p.y).join(" "),class:"track"},trk);
D.track.forEach(p=>el("circle",{cx:p.x,cy:p.y,r:0.6,fill:"var(--track)"},trk));
const shape=(s,x,y,r)=>{
 if(s==="circle")return["circle",{cx:x,cy:y,r}];
 if(s==="square")return["rect",{x:x-r,y:y-r,width:2*r,height:2*r}];
 if(s==="diamond")return["polygon",{points:`${x},${y-r*1.3} ${x+r*1.3},${y} ${x},${y+r*1.3} ${x-r*1.3},${y}`}];
 if(s==="triangle")return["polygon",{points:`${x},${y-r*1.3} ${x+r*1.2},${y+r} ${x-r*1.2},${y+r}`}];
 const pts=[];for(let i=0;i<10;i++){const a=Math.PI/5*i-Math.PI/2,rr=i%2?r*.55:r*1.4;pts.push((x+rr*Math.cos(a))+","+(y+rr*Math.sin(a)))}
 return["polygon",{points:pts.join(" ")}]};
let scale=1,sel=null;const marks=[];
D.points.forEach(p=>{const st=D.categories[p.category]||["c5","circle"];
 const [t,a]=shape(st[1],p.x,p.y,6);const m=el(t,{...a,class:"pt",fill:`var(--${st[0]})`});
 m.dataset.r=6;m.addEventListener("click",ev=>{ev.stopPropagation();show(p,m)});
 const tt=el("title",{},m);tt.textContent=p.name;marks.push({p,m,st,t})});
const fields=[...new Set(D.points.map(p=>p.field))].sort();
fields.forEach(f=>{const o=document.createElement("option");o.value=f;o.textContent=f;document.getElementById("field").appendChild(o)});
const catBox=document.getElementById("cats");const on={};
Object.keys(D.categories).forEach(c=>{on[c]=true;const n=D.points.filter(p=>p.category===c).length;
 const l=document.createElement("label");const sw=`<svg class="legend-swatch" viewBox="-8 -8 16 16"><${shapeTag(D.categories[c][1])} fill="var(--${D.categories[c][0]})"/></svg>`;
 l.innerHTML=`<input type="checkbox" checked>${sw}<span>${c}</span><span class="count">${n}</span>`;
 l.querySelector("input").onchange=e=>{on[c]=e.target.checked;filter()};catBox.appendChild(l)});
function shapeTag(s){const [t,a]=shape(s,0,0,5);return t+" "+Object.entries(a).map(([k,v])=>`${k}="${v}"`).join(" ")}
function filter(){const f=document.getElementById("field").value;
 marks.forEach(({p,m})=>{m.style.display=(on[p.category]&&(!f||p.field===f))?"":"none"})}
document.getElementById("field").onchange=filter;
document.getElementById("showTrack").onchange=e=>trk.style.display=e.target.checked?"":"none";
document.getElementById("showMeridian").onchange=e=>mer.style.display=e.target.checked?"":"none";
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function show(p,m){if(sel)sel.classList.remove("sel");sel=m;m.classList.add("sel");
 const rows=[["分類",p.category],["分野",p.field],["定義",p.definition],["場所（資料）",p.place],["座標の所在地",p.located],
 ["陸上・海上",p.land],["座標",`北緯 ${p.lat_dms}／東経 ${p.lon_dms}`],["対象年",p.year],["集計単位",p.unit_level],["算出方法",p.method],
 ["出典",p.source],["信頼性",p.reliability],["備考",p.note]];
 document.getElementById("info").innerHTML=`<h1>${esc(p.name)}</h1><dl>`+rows.filter(r=>r[1]).map(r=>`<dt>${r[0]}</dt><dd>${esc(r[1])}</dd>`).join("")+"</dl>"}
const rt=document.getElementById("regions");
D.regions.forEach(r=>{const tr=document.createElement("tr");tr.innerHTML=`<td>${esc(r.name)}</td><td>${esc(r.place)}</td>`;
 tr.style.cursor="pointer";tr.onclick=()=>{document.getElementById("info").innerHTML=`<h1>${esc(r.name)}</h1><dl>`+
 [["定義",r.definition],["場所",r.place],["対象年",r.year],["出典",r.source],["備考",r.note]].filter(x=>x[1]).map(x=>`<dt>${x[0]}</dt><dd>${esc(x[1])}</dd>`).join("")+"</dl>"};rt.appendChild(tr)});
// 表示範囲（km、投影座標）
const views=D.views;let view={...views.main};
function apply(){svg.setAttribute("viewBox",`${view.x} ${view.y} ${view.w} ${view.h}`);
 const k=view.w/svg.clientWidth;marks.forEach(({p,m,st,t})=>{const [tt,a]=shape(st[1],p.x,p.y,6*k);for(const key in a)m.setAttribute(key,a[key])});
 trk.querySelectorAll("circle").forEach(c=>c.setAttribute("r",2.5*k))}
function zoom(f,cx,cy){cx=cx??view.x+view.w/2;cy=cy??view.y+view.h/2;view={x:cx-(cx-view.x)*f,y:cy-(cy-view.y)*f,w:view.w*f,h:view.h*f};apply()}
document.getElementById("zin").onclick=()=>zoom(0.6);document.getElementById("zout").onclick=()=>zoom(1/0.6);
document.querySelectorAll("[data-view]").forEach(b=>b.onclick=()=>{view={...views[b.dataset.view]};apply()});
const toMap=(ev)=>{const r=svg.getBoundingClientRect();const s=Math.max(view.w/r.width,view.h/r.height);
 const ox=view.x+(view.w-r.width*s)/2,oy=view.y+(view.h-r.height*s)/2;return[ox+(ev.clientX-r.left)*s,oy+(ev.clientY-r.top)*s,s]};
svg.addEventListener("wheel",ev=>{ev.preventDefault();const [x,y]=toMap(ev);zoom(ev.deltaY>0?1.15:1/1.15,x,y)},{passive:false});
let drag=null;svg.addEventListener("pointerdown",ev=>{drag=[ev.clientX,ev.clientY];svg.setPointerCapture(ev.pointerId)});
svg.addEventListener("pointermove",ev=>{if(!drag)return;const s=toMap(ev)[2];view.x-=(ev.clientX-drag[0])*s;view.y-=(ev.clientY-drag[1])*s;drag=[ev.clientX,ev.clientY];apply()});
svg.addEventListener("pointerup",()=>drag=null);
window.addEventListener("resize",apply);apply();
// URL の # に id を書くと、その点を選んだ状態で開く（例 centers_map.html#emp_ict）
const hid=decodeURIComponent(location.hash.slice(1));const hm=marks.find(o=>o.p.id===hid);
if(hm){view={...views.center};apply();show(hm.p,hm.m)}
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
