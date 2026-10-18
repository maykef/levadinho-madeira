// Route map + altitude profile (with optional mobile-signal columns) for trail pages with a field-walk track.
// Markup: <div id="trackmaps" data-src="/gpx/<name>.json" data-labels='{...}'> plus svg#busplan, #busalt, #walkplan,
// #walkalt and div#walklegend. Data and labels come from the page; nothing here is page-specific.
(function(){
const box=document.getElementById('trackmaps'); if(!box) return;
const T=JSON.parse(box.dataset.labels||'{}');
const css=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const NS='http://www.w3.org/2000/svg';
const el=(p,t,a,txt)=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;p.appendChild(e);return e};
function draw(B,wp,ids,o){
const near=w=>{let b=B[0],d=1e9;B.forEach(p=>{const q=(p[0]-w.lat)**2+(p[1]-w.lon)**2;if(q<d){d=q;b=p}});return b};
// plan, line coloured by altitude
const svg=document.getElementById(ids[0]);
const lat0=B.reduce((s,p)=>s+p[0],0)/B.length,k=Math.cos(lat0*Math.PI/180);
const xs=B.map(p=>p[1]*k),ys=B.map(p=>p[0]);
const mnx=Math.min(...xs),mxx=Math.max(...xs),mny=Math.min(...ys),mxy=Math.max(...ys);
const pad=50,s=Math.min((800-2*pad)/(mxx-mnx),(o.H-2*pad)/(mxy-mny));
const ox=(800-(mxx-mnx)*s)/2,oy=(o.H-(mxy-mny)*s)/2;
const P=(la,lo)=>[ox+(lo*k-mnx)*s,o.H-(oy+(la-mny)*s)];
const emin=Math.min(...B.map(p=>p[2])),emax=Math.max(...B.map(p=>p[2]));
const ecol=e=>{const t=(e-emin)/(emax-emin);return `hsl(${150-t*120} 55% ${css('--bg').startsWith('#1')?'58%':'38%'})`};
el(svg,'polyline',{points:B.map(p=>P(p[0],p[1]).join(',')).join(' '),fill:'none',stroke:css('--track'),'stroke-width':9,'stroke-linecap':'round','stroke-linejoin':'round'});
for(let i=1;i<B.length;i++){const a=P(B[i-1][0],B[i-1][1]),b=P(B[i][0],B[i][1]);el(svg,'line',{x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:ecol((B[i][2]+B[i-1][2])/2),'stroke-width':5,'stroke-linecap':'round'})}
const km1=o.bar/111320*s;el(svg,'line',{x1:20,y1:o.H-20,x2:20+km1,y2:o.H-20,stroke:css('--fg'),'stroke-width':2});el(svg,'text',{x:20,y:o.H-30,class:'ax'},o.barl);
el(svg,'text',{x:780,y:24,'text-anchor':'end',class:'ax'},'N ↑');
wp.forEach((w,i)=>{const[x,y]=P(w.lat,w.lon);el(svg,'circle',{cx:x,cy:y,r:6,fill:css('--card'),stroke:css('--fg'),'stroke-width':2});
 const right=o.alt?i%2===1:x<o.split;el(svg,'text',{x:right?x+12:x-12,y:y+4,'text-anchor':right?'start':'end'},`${w.label||w.name.replace('Bus Stop ','')}${o.notime?'':' · '+w.t} · ${Math.round(near(w)[2])} m`)});
(o.pins||[]).forEach(q=>{const[x,y]=P(q.lat,q.lon);el(svg,'circle',{cx:x,cy:y,r:9,fill:css('--ink'),stroke:css('--card'),'stroke-width':2});el(svg,'text',{x:x,y:y+4,'text-anchor':'middle',style:'fill:#fff;font-size:10px;font-weight:700'},q.n);q.label&&el(svg,'text',{x:x+14,y:y+4},q.label)});
// legend
[['low',emin],['high',emax]].forEach(([l,e],i)=>{el(svg,'rect',{x:20+i*80,y:16,width:14,height:14,fill:ecol(e)});el(svg,'text',{x:40+i*80,y:28,class:'ax'},Math.round(e)+' m')});
// altitude profile
const a=document.getElementById(ids[1]);const X0=56,X1=785,Y0=16,Y1=220;const L=B[B.length-1][3]/1000;
const PX=km=>X0+km/L*(X1-X0),bot=Math.max(o.min0?0:-1e9,Math.floor((emin-o.padm)/o.step)*o.step),top=Math.ceil((emax+o.padm)/o.step)*o.step,PY=e=>Y1-(e-bot)/(top-bot)*(Y1-Y0);
for(let e=bot;e<=top;e+=o.step){el(a,'line',{x1:X0,x2:X1,y1:PY(e),y2:PY(e),stroke:css('--line')});el(a,'text',{x:X0-6,y:PY(e)+4,'text-anchor':'end',class:'ax'},e+' m')}
for(let km=0;km<=L+1e-9;km+=o.kstep)el(a,'text',{x:PX(km),y:Y1+16,'text-anchor':'middle',class:'ax'},(+km.toFixed(2))+(km===0?' km':''));
const line=B.map(p=>PX(p[3]/1000)+','+PY(p[2])).join(' ');
if(o.cols){const R=o.cols,band=r=>r.dbm===-200?'s-pr':r.dbm>=-85?'s-ex':r.dbm>=-95?'s-gd':r.dbm>=-105?'s-fr':r.dbm>=-115?'s-pr':'s-no';
 for(let i=0;i<B.length;i++){const km=B[i][3]/1000;let b=R[0],d=1e9;R.forEach(q=>{const e=Math.abs(q.km-km);if(e<d){d=e;b=q}});
  const xa=PX(i?(B[i-1][3]+B[i][3])/2000:0),xb=PX(i<B.length-1?(B[i][3]+B[i+1][3])/2000:L);
  const c=el(a,'rect',{x:xa,y:PY(B[i][2]),width:Math.max(.5,xb-xa+.4),height:PY(bot)-PY(B[i][2]),fill:d<=0.05?`var(--${band(b)})`:css('--track'),opacity:.85});}}
else el(a,'polygon',{points:`${PX(0)},${PY(bot)} ${line} ${PX(L)},${PY(bot)}`,fill:css('--good'),opacity:.15});
(o.pins||[]).forEach(q=>{const x=PX(q.km);el(a,'line',{x1:x,x2:x,y1:Y0,y2:Y1,stroke:css('--ink'),'stroke-width':1.5,'stroke-dasharray':'3 3'});el(a,'circle',{cx:x,cy:Y0+8,r:9,fill:css('--ink')});el(a,'text',{x:x,y:Y0+12,'text-anchor':'middle',style:'fill:#fff;font-size:10px;font-weight:700'},q.n)});
el(a,'polyline',{points:line,fill:'none',stroke:o.cols?css('--fg'):css('--good'),'stroke-width':2.5,'stroke-linejoin':'round'});
wp.forEach((w,i)=>{const p=o.endName&&w.name===o.endName?B[B.length-1]:near(w);const x=PX(p[3]/1000),y=PY(p[2]);el(a,'circle',{cx:x,cy:y,r:4.5,fill:css('--card'),stroke:css('--fg'),'stroke-width':2});
 el(a,'text',o.cols?{x:i?x-4:x+4,y:y-12,'text-anchor':i?'end':'start',stroke:css('--card'),'stroke-width':4,'paint-order':'stroke'}:{x:Math.min(Math.max(x,X0+40),X1-40),y:o.alt&&i%2===0?y+20:y-10,'text-anchor':'middle'},(w.label||w.name).replace('Bus Stop ',''))});
}

fetch(box.dataset.src).then(r=>r.json()).then(D=>{
 const L=[['s-ex',T.ex],['s-gd',T.gd],['s-fr',T.fr],['s-pr',T.pr],['s-no',T.no],['track',T.nr]];
 const lg=document.getElementById('walklegend');
 if(lg) lg.innerHTML='<b style="color:var(--ink)">'+T.sig+'</b>'+L.map(([b,t])=>`<span><i style="background:var(--${b})"></i>${t}</span>`).join('');
 if(document.getElementById('busplan')) draw(D.bus,[{lat:D.bstart.lat,lon:D.bstart.lon,name:'s',label:T.bstart},{lat:D.bend.lat,lon:D.bend.lon,name:'e',label:T.bend}],['busplan','busalt'],{notime:1,H:640,bar:1000,barl:'1 km',split:560,padm:0,min0:1,step:200,kstep:2,endName:'e'});
 if(document.getElementById('walkplan')) draw(D.walk,[{lat:D.start.lat,lon:D.start.lon,name:'s',label:T.start},{lat:D.end.lat,lon:D.end.lon,name:'e',label:T.end}],['walkplan','walkalt'],{notime:1,cols:D.readings,pins:D.pins,H:560,bar:200,barl:'200 m',split:520,padm:20,step:10,kstep:0.25,alt:1,endName:'e'});
}).catch(()=>{});
})();
