'use strict';

window.addEventListener('DOMContentLoaded', () => {
  initGamification();
  initDragDrop();
  refreshAll();
});

function setBusy(){document.body&&document.body.classList.add('loading')}
function clearBusy(){document.body&&document.body.classList.remove('loading')}

function addLog(text){const el=document.getElementById('logs');if(!el)return;const li=document.createElement('li');li.textContent=text;const f=el.firstElementChild;if(f)el.insertBefore(li,f);else el.appendChild(li);while(el.children.length>30){el.firstElementChild.remove()}}

function setStatus(id,label,ok){const el=document.getElementById(id);if(!el)return;el.textContent=label;el.dataset.ok=!!ok?'1':'0'}
async function check(id,url,label){try{const r=await fetch(url);const ok=r.ok;setStatus(id,label,ok);addLog('Checked '+label+' -> '+(ok?'ok':'failed')+' '+r.status)}catch(e){setStatus(id,label,false);addLog('Checked '+label+' -> error: '+e.message)}}

async function refreshAll(){setBusy();try{await Promise.all([check('llm-status','/health','LLM API'),check('comfy-status','http://localhost:8188/system_stats','ComfyUI'),check('openwebui-status','http://localhost:3002/api/version','Open WebUI'),check('redis-status','http://localhost:6380/','Redis'),check('qdrant-status','http://localhost:6333/healthz','Qdrant'),check('postgres-status','http://localhost:5433/','Postgres'),check('n8n-status','http://localhost:5678/healthz','n8n')])}finally{clearBusy()}}

async function refreshGPUs(){try{const r=await fetch('/gpu-status');const data=await r.json();const c=document.getElementById('gpu-cards');if(!c)return;c.innerHTML='';(data.gpus||[]).forEach(g=>{const d=document.createElement('div');d.className='card';d.innerHTML='<div class=\"pill '+(g.utilization<55?'ok':'warn')+'\">'+g.name+'</div><div>VRAM '+g.memory+'</div><div>Util '+g.utilization+'%</div>';c.appendChild(d)});addLog('GPU status refreshed')}catch(e){addLog('GPU status failed: '+e.message)}}
async function refreshOllama(){try{const r=await fetch('/ollama-status');const data=await r.json();const c=document.getElementById('ollama-grid');if(!c)return;c.innerHTML='';(data.instances||[]).forEach(x=>{const d=document.createElement('div');d.className='card';d.innerHTML='<div class=\"pill '+(x.healthy?'ok':'err')+'\">'+x.name+'</div><div>Port '+x.port+'</div><div>VRAM '+x.memory+'</div><div>Models '+x.models+'</div>';c.appendChild(d)});addLog('Ollama refreshed')}catch(e){addLog('Ollama failed: '+e.message)}}

function initGamification(){const state=loadState();renderProfile(state);document.querySelectorAll('.btn').forEach(b=>b.addEventListener('click',()=>{const text=(b.textContent||'').toLowerCase();if(text.includes('optimize')||text.includes('improve')) awardXP(state,'tool');else if(text.includes('refresh')||text.includes('refresh')) awardXP(state,'ritual');renderProfile(state)}))}
function loadState(){try{const raw=localStorage.getItem('ai-lab-state');return raw?JSON.parse(raw):{xp:0,level:1,badges:['starter']}}catch{return{xp:0,level:1,badges:['starter']}}}
function saveState(s){localStorage.setItem('ai-lab-state',JSON.stringify(s))}
function renderProfile(s){const next=100+(s.level-1)*140;document.getElementById('level').textContent=s.level;document.getElementById('xp').textContent=s.xp;document.getElementById('next').textContent=next;const pill=document.getElementById('xp-pill');if(pill)pill.textContent=s.xp+' XP';renderBadges(s.badges)}
function renderBadges(badges){const c=document.getElementById('badges');if(!c)return;c.innerHTML='';('starter,optimizer,uploader,operator').split(',').forEach(key=>{const owned=badges.includes(key);const el=document.createElement('div');el.className='badge';el.textContent=(owned?'[x] ':'[ ] ')+key;el.style.opacity=owned?1:.55;c.appendChild(el)})}
function awardXP(state,bucket){const bonus=(localStorage.getItem('ai-lab-streak')||'0');const delta={prompt:15,improve:10,tool:12,ritual:5,batch:18,admin:20}[bucket]||5;state.xp+=Math.max(5,Math.floor(delta*(1+(parseInt(bonus,10)||0)*0.02)));const threshold=100+(state.level-1)*140;if(state.xp>=threshold){state.xp-=threshold;state.level+=1;addLog('Level up! Now '+state.level)}['starter','optimizer','uploader','operator'].forEach(k=>{if(state.xp>=(k==='starter'?5:k==='optimizer'?25:k==='uploader'?55:120)&&!state.badges.includes(k)){state.badges.push(k);addLog('Unlocked badge: '+k)}});saveState(state)}

function submitPrompt(mode){const p=document.getElementById('prompt').value;const m=document.getElementById('mode').value;const w=document.getElementById('workflow').value;if(!p.trim()){addLog('Prompt empty');return}addLog(mode + ' prompt queued: '+m+' -> '+w);awardXP(loadState(),mode==='optimize'?'optimize':'prompt');renderProfile(loadState())}
function sendToGenerate(){const p=document.getElementById('prompt').value;const m=document.getElementById('mode').value;const w=document.getElementById('workflow').value;if(!p.trim()){addLog('Prompt empty');return}fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:p,mode:w})}).then(r=>r.text().catch(()=>String(r.status))).then(t=>{addLog('generate response: '+t);awardXP(loadState(),'admin')}).catch(e=>addLog('generate failed: '+e.message))}
function improvePrompt(){const p=document.getElementById('prompt');if(p){p.value=p.value.replace(/\bpicture\b/gi,'photograph').replace(/\bvery\b/gi,'');addLog('Prompt improved');awardXP(loadState(),'improve');renderProfile(loadState())}}

function initDragDrop(){const z=document.getElementById('dropzone'),inp=document.getElementById('fileInput'),q=document.getElementById('queue-count'),last=document.getElementById('last-upload');if(!z||!inp)return;z.addEventListener('dragover',e=>{e.preventDefault();z.style.borderColor='#7c9cff'});z.addEventListener('dragleave',()=>{z.style.borderColor='#2a354a'});z.addEventListener('drop',e=>{e.preventDefault();z.style.borderColor='#2a354a';handleFiles(e.dataTransfer.files)});inp.addEventListener('change',e=>{handleFiles(e.target.files)});function handleFiles(files){const arr=[...files];addLog('Uploaded '+arr.map(x=>x.name).join(', '));if(q)q.textContent=(parseInt(q.textContent||'0',10)+arr.length);if(last&&arr[0])last.textContent=arr[0].name}}

function clearLogs(){const el=document.getElementById('logs');if(el)el.innerHTML=''}
function toggleTheme(){document.body.style.filter=document.body.style.filter?'':'invert(1) hue-rotate(180deg)'}

async function runScan(){const text=document.getElementById('scan-text').value;if(!text.trim()){addLog('Scan input empty');return}setBusy();try{const r=await fetch('/scan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});const data=await r.json();const el=document.getElementById('scan-report');el.style.display='block';el.innerHTML='<div class="pill '+(data.ok?'ok':'err')+'">'+data.status+'</div><div>'+data.message+'</div><pre style="white-space:pre-wrap;color:#9fb3d8;font-size:12px">'+data.details+'</pre>';addLog('Scan complete: '+data.status)}catch(e){addLog('Scan failed: '+e.message)}finally{clearBusy()}}
async function autoPolicy(){const text=document.getElementById('scan-text').value;if(!text.trim()){addLog('Scan input empty');return}await runScan();addLog('Auto-policy applied based on local rules')}

(async()=>{await refreshAll();await refreshGPUs();await refreshOllama()})();
