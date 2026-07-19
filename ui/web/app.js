const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const state = {busy:false, view:'home', listening:false, bridgeReady:false, modelMonitorStarted:false, pointerX:.5, pointerY:.5, pointerEnergy:0};

let desktopApi=null;
let resolveBridge;
const bridgeReady=new Promise(resolve=>{resolveBridge=resolve});
function captureBridge(){
  const bridge=window.pywebview?.api;
  if(!bridge||typeof bridge.respond!=='function')return null;
  desktopApi=bridge;
  state.bridgeReady=true;
  resolveBridge(bridge);
  document.body.classList.add('bridge-connected');
  const gate=$('#bridge-gate');if(gate)setTimeout(()=>gate.remove(),420);
  if(typeof bridge.ready==='function')bridge.ready().catch(()=>{});
  monitorModel(bridge);
  return bridge;
}
async function monitorModel(bridge){
  if(state.modelMonitorStarted||typeof bridge.model_status!=='function')return;
  state.modelMonitorStarted=true;
  for(let attempt=0;attempt<90;attempt++){
    try{
      const result=await bridge.model_status();
      if(result.complete==='true'){
        setStatus(result.ready==='true'?'Online and ready':'Model available on first request',result.ready==='true'?'ready':'busy');
        return;
      }
      setStatus('Warming local model','busy');
    }catch(e){return;}
    await new Promise(resolve=>setTimeout(resolve,350));
  }
  setStatus('Model available on first request','busy');
}
async function waitForApi(method, timeout=1400){
  const immediate=desktopApi||captureBridge();
  if(immediate&&typeof immediate[method]==='function')return immediate;
  const bridge=await Promise.race([
    bridgeReady,
    new Promise(resolve=>setTimeout(()=>resolve(null),timeout)),
  ]);
  return bridge&&typeof bridge[method]==='function'?bridge:null;
}
function bridgeFailure(){
  return {ok:'false',answer:'The Jarvis desktop bridge is still connecting. Please wait a moment and try again.'};
}
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
async function copyText(text,button){
  text=text.replace(/^```[a-z0-9_+.-]*\s*$/gmi,'').replace(/^```\s*$/gm,'').trim();
  let copied=false;
  try{if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(text);copied=true;}}catch(e){}
  if(!copied){
    const area=document.createElement('textarea');area.value=text;area.setAttribute('readonly','');area.style.cssText='position:fixed;opacity:0;pointer-events:none';document.body.append(area);area.select();
    try{copied=document.execCommand('copy');}catch(e){}area.remove();
  }
  button.textContent=copied?'COPIED':'COPY FAILED';button.classList.toggle('copied',copied);
  setTimeout(()=>{button.textContent='COPY';button.classList.remove('copied')},1400);
}
function addCopyButton(article,text){
  const meta=article.querySelector('.message-meta');if(!meta||meta.querySelector('.copy-message'))return;
  const button=document.createElement('button');button.className='copy-message';button.type='button';button.textContent='COPY';button.title='Copy Jarvis response';
  button.addEventListener('click',event=>{event.stopPropagation();copyText(text,button)});meta.append(button);
}
function addMessage(role,text,loading=false){
  const article=document.createElement('article'); article.className=`message ${role}`;
  article.innerHTML=`<div class="message-meta"><span class="message-mark"></span>${role==='user'?'KARAN':'JARVIS'} <time>${stamp()}</time></div><p>${loading?'<span class="loading-dots"><i></i><i></i><i></i></span>':escapeHtml(text)}</p>`;
  if(role==='jarvis'&&!loading)addCopyButton(article,text);
  $('#transcript').append(article); $('#transcript').scrollTop=$('#transcript').scrollHeight; return article;
}
function escapeHtml(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML;}
async function submit(command){
  command=(command||$('#prompt').value).trim(); if(!command||state.busy)return;
  state.busy=true; $('#prompt').value=''; showView('conversation'); addMessage('user',command); const wait=addMessage('jarvis','',true); setStatus('Jarvis is thinking','busy');
  let result;
  try{const bridge=await waitForApi('respond');result=bridge?await bridge.respond(command):bridgeFailure();}
  catch(e){result={ok:'false',answer:'Jarvis could not reach the local assistant core. Please restart the desktop app.'}}
  wait.remove(); addMessage('jarvis',result.answer); setStatus(result.ok==='true'?'Online and ready':'Request failed',result.ok==='true'?'ready':'error'); state.busy=false;
  if($('#speak-answers').checked){const bridge=await waitForApi('speak',800);if(bridge)bridge.speak(result.answer);}
}
async function listen(){
  if(state.busy)return; state.busy=true; state.listening=true; $('#mic').classList.add('active'); $('#hero-orb').classList.add('active'); $('#rail-listen').classList.add('active'); $('#listen-label').textContent='Listening…'; setStatus('Listening');
  let result; try{const bridge=await waitForApi('listen');result=bridge?await bridge.listen():{ok:'false',text:'The voice bridge is still connecting.'};}catch(e){result={ok:'false',text:'Jarvis could not start voice input.'}}
  $('#mic').classList.remove('active'); $('#hero-orb').classList.remove('active'); $('#rail-listen').classList.remove('active'); $('#listen-label').textContent='Tap the orb to speak'; state.busy=false; state.listening=false;
  if(result.ok==='true'&&result.text) submit(result.text); else setStatus(result.text||'I did not catch that','error');
}
async function chooseDataset(){
  const bridge=await waitForApi('choose_dataset');
  if(!bridge){showView('conversation');addMessage('jarvis','The desktop file picker is still connecting. Please try again.');return;}
  const result=await bridge.choose_dataset(); if(result.ok==='true'&&result.path) submit(`analyze "${result.path}"`);
}
async function chooseResume(){
  showView('conversation');
  addMessage('jarvis','Choose your current resume. I will use it as the factual boundary, then ask you for the complete job description.');
  const bridge=await waitForApi('choose_resume');
  if(!bridge){addMessage('jarvis','The desktop file picker is still connecting. Please try again.');return;}
  const result=await bridge.choose_resume(); if(result.ok==='true'&&result.path) submit(`load resume "${result.path}"`);
}
async function setMode(mode){
  $$('.mode-switch button').forEach(b=>b.classList.toggle('selected',b.dataset.mode===mode));
  const bridge=await waitForApi('set_mode',1200);
  if(bridge)await bridge.set_mode(mode);
  setStatus(`${mode} intelligence enabled`);
}
function updateClock(){const d=new Date();$('#clock').textContent=d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',hour12:false});$('#date').textContent=d.toLocaleDateString([],{weekday:'long',month:'long',day:'numeric'});const h=d.getHours();$('#greeting').textContent=h<12?'Good morning,':h<17?'Good afternoon,':'Good evening,';}

$$('[data-view]').forEach(b=>b.addEventListener('click',()=>showView(b.dataset.view)));
$$('[data-command]').forEach(b=>b.addEventListener('click',()=>submit(b.dataset.command)));
$$('[data-mode]').forEach(b=>b.addEventListener('click',()=>setMode(b.dataset.mode)));
$('#send').addEventListener('click',()=>submit()); $('#prompt').addEventListener('keydown',e=>{if(e.key==='Enter')submit()});
$('#mic').addEventListener('click',listen); $('#hero-orb').addEventListener('click',listen); $('#rail-listen').addEventListener('click',listen);
$('#attach').addEventListener('click',chooseDataset); $('#dataset-card').addEventListener('click',chooseDataset);
$('#resume-nav').addEventListener('click',chooseResume); $('#resume-card').addEventListener('click',chooseResume);
window.addEventListener('pywebviewready',()=>{captureBridge();setStatus('Python core connected')});
captureBridge();
$$('.message time').forEach(t=>t.textContent=stamp()); updateClock(); setInterval(updateClock,1000);
$$('.message.jarvis').forEach(message=>addCopyButton(message,message.querySelector('p')?.innerText||''));

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
