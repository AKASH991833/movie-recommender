/* CineMatch - content-based recommendation on MovieLens top-280. */
(()=>{
const $=s=>document.querySelector(s);
let ratings=JSON.parse(localStorage.getItem('cinematch-ratings')||'{}'); // idx -> 1..5
let tab='rate',genreFilter=null;
const save=()=>localStorage.setItem('cinematch-ratings',JSON.stringify(ratings));
const GENRES=[...new Set(MOVIES.flatMap(m=>m[2]))].sort();
const POSTER_HUES={Action:8,Adventure:24,Animation:42,Children:52,Comedy:96,Crime:262,Documentary:160,Drama:210,Fantasy:290,'Film-Noir':0,Horror:340,'IMAX':180,Musical:300,Mystery:250,Romance:330,'Sci-Fi':190,Thriller:270,War:15,Western:30};
function posterStyle(m){
  const h=POSTER_HUES[m[2][0]]??200,h2=(h+42)%360;
  return`background:
    radial-gradient(90px 60px at 80% 12%,hsla(${h2},75%,70%,.5),transparent 70%),
    radial-gradient(130px 90px at 12% 88%,hsla(${h2},65%,60%,.4),transparent 70%),
    linear-gradient(160deg,hsl(${h},48%,34%),hsl(${h2},55%,20%))`;
}
function tasteVector(){
  const v={};let w=0;
  Object.entries(ratings).forEach(([i,r])=>{
    const m=MOVIES[i];if(!m)return;
    const weight=(r-3);w+=Math.abs(weight);
    m[2].forEach(g=>{v[g]=(v[g]||0)+weight;});
  });
  const n=Object.keys(v).length?Math.max(...Object.values(v).map(Math.abs),1):1;
  Object.keys(v).forEach(g=>v[g]/=n);
  return{v,rated:Object.keys(ratings).length};
}
function recommend(){
  const{v,rated}=tasteVector();
  return MOVIES.map((m,i)=>{
    if(ratings[i]!=null)return null;
    let s=0,why=[];
    m[2].forEach(g=>{if(v[g]){s+=v[g];if(v[g]>0.05)why.push(g);}});
    s=s*0.75+m[3]*0.55; // taste + quality prior
    // find the rated movie with the most genre overlap for "because you liked"
    let because=null,best=-1;
    Object.entries(ratings).forEach(([ri,r])=>{
      if(r<4)return;const om=MOVIES[ri];if(!om)return;
      const ov=m[2].filter(g=>om[2].includes(g)).length;
      if(ov>best){best=ov;because=om[0];}
    });
    return{i,s,why,because,m};
  }).filter(Boolean).sort((a,b)=>b.s-a.s);
}
function stars(i){
  const r=ratings[i]||0;
  return`<div class="stars" data-i="${i}">${[1,2,3,4,5].map(s=>`<span class="star${s<=r?' on':''}" data-s="${s}">★</span>`).join('')}</div>`;
}
function card(m,i,extra=''){
  return`<div class="mcard"><div class="poster" style="${posterStyle(m)}">
    <h3>${m[0]}</h3><div class="yr">${m[1]||''}</div></div>
    <div class="mbody"><div class="gtags">${m[2].slice(0,3).map(g=>`<span class="gtag">${g}</span>`).join('')}</div>
    <div class="mscore"><span>★ ${m[3].toFixed(2)}</span><span>${m[4]} ratings</span></div>
    ${extra}${stars(i)}</div></div>`;
}
function render(){
  const st=$('#stage');
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('on',t.dataset.t===tab));
  const recs=recommend();
  $('#recCount').textContent=Object.keys(ratings).length?' ('+recs.length+')':'';
  if(tab==='rate'){
    let list=MOVIES.map((m,i)=>({m,i})).filter(x=>!genreFilter||x.m[2].includes(genreFilter));
    const unrated=list.filter(x=>ratings[x.i]==null);
    const ratedFirst=list.filter(x=>ratings[x.i]!=null);
    list=[...unrated.slice(0,24),...ratedFirst].slice(0,30);
    st.innerHTML=`<div class="filters">
      <button class="fchip${!genreFilter?' on':''}" data-g="">All genres</button>
      ${GENRES.map(g=>`<button class="fchip${genreFilter===g?' on':''}" data-g="${g}">${g}</button>`).join('')}</div>
      <div class="mgrid">${list.map(x=>card(x.m,x.i)).join('')}</div>`;
  }else if(tab==='recs'){
    if(!Object.keys(ratings).length){st.innerHTML=`<div class="card empty">Rate a few movies first - 5 or more gives the best picks.</div>`;return;}
    st.innerHTML=`<div class="mgrid">${recs.slice(0,18).map(r=>card(r.m,r.i,
      `<div class="why">Because you liked ${r.because||('top '+r.why[0]+' films')}${r.why.length?' · '+r.why.slice(0,2).join(', '):''}</div>`)).join('')}</div>`;
  }else{
    const{v,rated}=tasteVector();
    const top=Object.entries(v).sort((a,b)=>b[1]-a[1]);
    const pos=top.filter(x=>x[1]>0.05),neg=top.filter(x=>x[1]<-0.05);
    st.innerHTML=`<section class="card"><div class="card-body">
      <h2 class="sect">Your taste profile (${rated} rated)</h2>
      ${rated?`<p style="font-size:14px;color:var(--muted);margin-bottom:14px">Genres your ratings pull toward, and away from:</p>
      <div class="taste">${pos.map(([g,w])=>`<span class="taste-tag">${g} <b>+${w.toFixed(2)}</b></span>`).join('')||'<span style="color:var(--muted)">Rate movies 4-5 stars to build positive signals.</span>'}</div>
      <div class="taste" style="margin-top:10px">${neg.map(([g,w])=>`<span class="taste-tag">${g} <b style="color:#dc2626">${w.toFixed(2)}</b></span>`).join('')}</div>`
      :'<div class="empty">No ratings yet.</div>'}
      <button class="btn ghost" id="reset" style="margin-top:18px">Reset all ratings</button></div></section>`;
    st.querySelector('#reset').onclick=()=>{if(confirm('Clear all ratings?')){ratings={};save();render();}};
    return;
  }
  st.querySelectorAll('.stars').forEach(el=>{
    el.querySelectorAll('.star').forEach(s=>s.onclick=()=>{
      const i=el.dataset.i,v=+s.dataset.s;
      if(ratings[i]===v)delete ratings[i];else ratings[i]=v;
      save();render();toast(ratings[i]?`Rated ${v}/5`:'Rating removed');});});
  st.querySelectorAll('.fchip').forEach(c=>c.onclick=()=>{genreFilter=c.dataset.g||null;render();});
}
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{tab=t.dataset.t;render();});
render();
})();
