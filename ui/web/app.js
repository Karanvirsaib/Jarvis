const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const state = {busy:false, view:'home', listening:false, pointerX:.5, pointerY:.5, pointerEnergy:0};

function api(){ return window.pywebview?.api; }
function setStatus(text, tone='ready'){
  $('#status').innerHTML=`<span style="background:${tone==='error'?'#e47d83':tone==='busy'?'#a989e8':'#64d6a7'}"></span>${text.toUpperCase()}`;
}
function showView(name){
  state.view=name;
  $$('.view').forEach(v=>v.classList.toggle('active',v.id===`${name}-view`));
  $$('.nav-item[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===name));
  if(name==='conversation') setTimeout(()=>$('#prompt').focus(),350);
}
function stamp(){return new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});}
function addMessage(role,text,loading=false){
  const article=document.createElement('article'); article.className=`message ${role}`;
  article.innerHTML=`<div class="message-meta"><span class="message-mark"></span>${role==='user'?'KARAN':'JARVIS'} <time>${stamp()}</time></div><p>${loading?'<span class="loading-dots"><i></i><i></i><i></i></span>':escapeHtml(text)}</p>`;
  $('#transcript').append(article); $('#transcript').scrollTop=$('#transcript').scrollHeight; return article;
}
function escapeHtml(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML;}
async function submit(command){
  command=(command||$('#prompt').value).trim(); if(!command||state.busy)return;
  state.busy=true; $('#prompt').value=''; showView('conversation'); addMessage('user',command); const wait=addMessage('jarvis','',true); setStatus('Jarvis is thinking','busy');
  let result;
  try{result=api()?await api().respond(command):{ok:'true',answer:'Preview mode — the Python assistant bridge is not connected.'};}
  catch(e){result={ok:'false',answer:String(e)}}
  wait.remove(); addMessage('jarvis',result.answer); setStatus(result.ok==='true'?'Online and ready':'Request failed',result.ok==='true'?'ready':'error'); state.busy=false;
  if($('#speak-answers').checked&&api()) api().speak(result.answer);
}
async function listen(){
  if(state.busy)return; state.busy=true; state.listening=true; $('#mic').classList.add('active'); $('#hero-orb').classList.add('active'); $('#rail-listen').classList.add('active'); $('#listen-label').textContent='Listening…'; setStatus('Listening');
  let result; try{result=api()?await api().listen():{ok:'false',text:''};}catch(e){result={ok:'false',text:String(e)}}
  $('#mic').classList.remove('active'); $('#hero-orb').classList.remove('active'); $('#rail-listen').classList.remove('active'); $('#listen-label').textContent='Tap the orb to speak'; state.busy=false; state.listening=false;
  if(result.ok==='true'&&result.text) submit(result.text); else setStatus(result.text||'I did not catch that','error');
}
async function chooseDataset(){
  if(!api()){showView('conversation');addMessage('jarvis','File selection is available in the desktop app.');return;}
  const result=await api().choose_dataset(); if(result.ok==='true'&&result.path) submit(`analyze "${result.path}"`);
}
async function chooseResume(){
  showView('conversation');
  addMessage('jarvis','Choose your current resume. I will use it as the factual boundary, then ask you for the complete job description.');
  if(!api()){addMessage('jarvis','File selection is available in the desktop app.');return;}
  const result=await api().choose_resume(); if(result.ok==='true'&&result.path) submit(`load resume "${result.path}"`);
}
function setMode(mode){
  $$('.mode-switch button').forEach(b=>b.classList.toggle('selected',b.dataset.mode===mode));
  if(api()) api().set_mode(mode); setStatus(`${mode} intelligence enabled`);
}
function updateClock(){const d=new Date();$('#clock').textContent=d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',hour12:false});$('#date').textContent=d.toLocaleDateString([],{weekday:'long',month:'long',day:'numeric'});const h=d.getHours();$('#greeting').textContent=h<12?'Good morning,':h<17?'Good afternoon,':'Good evening,';}

$$('[data-view]').forEach(b=>b.addEventListener('click',()=>showView(b.dataset.view)));
$$('[data-command]').forEach(b=>b.addEventListener('click',()=>submit(b.dataset.command)));
$$('[data-mode]').forEach(b=>b.addEventListener('click',()=>setMode(b.dataset.mode)));
$('#send').addEventListener('click',()=>submit()); $('#prompt').addEventListener('keydown',e=>{if(e.key==='Enter')submit()});
$('#mic').addEventListener('click',listen); $('#hero-orb').addEventListener('click',listen); $('#rail-listen').addEventListener('click',listen);
$('#attach').addEventListener('click',chooseDataset); $('#dataset-card').addEventListener('click',chooseDataset);
$('#resume-nav').addEventListener('click',chooseResume); $('#resume-card').addEventListener('click',chooseResume);
$$('.message time').forEach(t=>t.textContent=stamp()); updateClock(); setInterval(updateClock,1000);

// Living waveform: layered energy waves react to time, pointer position, hover, and listening state.
const waveCanvas=$('#orb-wave');
const waveCtx=waveCanvas.getContext('2d');
const hero=$('#home-view');
hero.addEventListener('pointermove',e=>{
  const r=waveCanvas.getBoundingClientRect();
  state.pointerX=Math.max(0,Math.min(1,(e.clientX-r.left)/r.width));
  state.pointerY=Math.max(0,Math.min(1,(e.clientY-r.top)/r.height));
  state.pointerEnergy=1;
});
hero.addEventListener('pointerleave',()=>{state.pointerEnergy=0});
function drawWave(now){
  const w=waveCanvas.width,h=waveCanvas.height,mid=h*.44,t=now*.001;
  waveCtx.clearRect(0,0,w,h);
  state.pointerEnergy+=(0-state.pointerEnergy)*.018;
  const hover=$('#hero-orb').matches(':hover')?1:0;
  const active=state.listening?1:0;
  const energy=1+hover*.45+active*1.65;
  const px=state.pointerX*w;
  const fade=waveCtx.createLinearGradient(0,0,w,0);
  fade.addColorStop(0,'rgba(139,234,242,0)');fade.addColorStop(.14,'rgba(139,234,242,.6)');fade.addColorStop(.5,'rgba(139,234,242,.92)');fade.addColorStop(.86,'rgba(139,234,242,.6)');fade.addColorStop(1,'rgba(139,234,242,0)');
  const layers=[
    {amp:14,freq:.030,speed:1.7,alpha:.46,width:1.15,phase:0},
    {amp:9,freq:.047,speed:-1.15,alpha:.28,width:.8,phase:1.7},
    {amp:5,freq:.081,speed:2.35,alpha:.17,width:.7,phase:3.4},
    {amp:20,freq:.018,speed:.7,alpha:.10,width:1.4,phase:4.8}
  ];
  layers.forEach((l,index)=>{
    waveCtx.beginPath();
    for(let x=0;x<=w;x+=2){
      const centerDistance=Math.abs(x-w/2)/(w/2);
      const envelope=Math.pow(Math.max(0,1-centerDistance),1.55);
      const pointerEnvelope=Math.exp(-Math.pow((x-px)/115,2))*state.pointerEnergy;
      const modulation=1+.34*Math.sin(x*.009-t*.8+index);
      const y=mid+Math.sin(x*l.freq+t*l.speed+l.phase)*l.amp*envelope*energy*modulation
        +Math.sin(x*.012-t*2.1)*12*pointerEnvelope*(state.pointerY-.5);
      if(x===0)waveCtx.moveTo(x,y);else waveCtx.lineTo(x,y);
    }
    waveCtx.strokeStyle=fade;waveCtx.globalAlpha=l.alpha;waveCtx.lineWidth=l.width;waveCtx.shadowColor='rgba(90,220,238,.42)';waveCtx.shadowBlur=index===0?8:3;waveCtx.stroke();
  });
  waveCtx.globalAlpha=.5+.25*Math.sin(t*1.4);waveCtx.shadowBlur=12;
  for(let i=0;i<5;i++){
    const x=(w*.18+((t*(28+i*4)+i*127)%(w*.64)));const d=Math.abs(x-w/2)/(w/2);const y=mid+Math.sin(x*.03+t*1.7)*14*(1-d);
    waveCtx.beginPath();waveCtx.arc(x,y,1.3+(i%2),0,Math.PI*2);waveCtx.fillStyle=i%2?'#8beaf2':'#a989e8';waveCtx.fill();
  }
  waveCtx.globalAlpha=1;waveCtx.shadowBlur=0;requestAnimationFrame(drawWave);
}
requestAnimationFrame(drawWave);
