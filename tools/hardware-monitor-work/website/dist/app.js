'use strict';
const $ = id => document.getElementById(id);
const icon = name => `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let base = localStorage.getItem('sentinel-service') || (/^(localhost|127\.0\.0\.1)$/.test(location.hostname) ? location.origin : 'http://127.0.0.1:8765');
let connected = false, records = [], hardware = {}, currentId = null, selectedFrame = {}, queue = [], uploading = false, activePage = 'overview', lastResultSignature = '', toastTimer;
const labels = {person:'Person detected', animal:'Animal only', unconfirmed:'Unconfirmed', queued:'Queued', processing:'Processing', failed:'Analysis failed'};
const complete = e => e.status === 'complete';
const state = e => complete(e) ? e.decision : e.status;
const timeLabel = value => new Date(value).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
const mediaUrl = value => `${base}${value}`;
function toast(message, error=false) { clearTimeout(toastTimer); $('toast').textContent=message; $('toast').classList.toggle('error',error); $('toast').hidden=false; toastTimer=setTimeout(()=>$('toast').hidden=true,6500); }
async function api(path, options={}) {
 const controller = new AbortController(), timer = setTimeout(()=>controller.abort(), options.method === 'POST' ? 120000 : 10000);
 try {
  const r = await fetch(base+path,{...options,signal:controller.signal});
  const value = await r.json().catch(()=>({detail:'The service returned an invalid response.'}));
  if(!r.ok) throw Error(typeof value.detail==='string' ? value.detail : `Request failed (${r.status})`);
  return value;
 } finally { clearTimeout(timer); }
}
function go(page) {
 const analyzing=page==='analyze';
 if (!['overview','analyze','events','hardware','about'].includes(page)) page='overview';
 activePage=page;
 document.querySelectorAll('.page').forEach(p=>p.hidden = p.id!==`page-${analyzing?'overview':page}`);
 document.querySelectorAll('nav [data-page]').forEach(a=>a.classList.toggle('active',a.dataset.page===page));
 $('breadcrumb').textContent=({overview:'Overview',analyze:'Analyze media',events:'Event history',hardware:'Hardware',about:'About the project'})[page];
 if(analyzing) setTimeout(()=>$('analysis-panel').scrollIntoView({behavior:'smooth',block:'start'}),40);
 else window.scrollTo({top:0,behavior:'instant'});
}
window.addEventListener('hashchange',()=>go(location.hash.slice(1)||'overview'));
go(location.hash.slice(1)||'overview');
$('new-analysis').onclick=()=>{location.hash='analyze'; if(activePage==='analyze') $('analysis-panel').scrollIntoView({behavior:'smooth'});};
function openConnect(){ $('service-url').value=base; $('connect-error').textContent=''; $('connect-dialog').showModal(); }
$('connect-open').onclick=openConnect;
document.querySelectorAll('dialog .close-dialog').forEach(b=>b.onclick=()=>b.closest('dialog').close());
document.querySelectorAll('dialog').forEach(d=>d.addEventListener('click',e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close();}}));
$('connect-form').onsubmit=async e=>{
 e.preventDefault(); const button=e.target.querySelector('[type=submit]');button.disabled=true;const old=base;
 try {
  const u=new URL($('service-url').value.trim());
  if(!['http:','https:'].includes(u.protocol)||u.username||u.password)throw Error('Use an HTTP or HTTPS address without credentials.');
  base=u.origin;await api('/api/health');localStorage.setItem('sentinel-service',base);$('connect-dialog').close();lastResultSignature='';await refresh();toast('Inference service connected. Ready to analyze.');
 }catch(err){base=old;$('connect-error').textContent=`Could not connect. ${err.message} Check that the service is running, the address is correct, and its allowed origins include this website.`;}
 finally{button.disabled=false;}
};
function updateConnection(ok,health){
 connected=ok; $('connection-badge').classList.toggle('connected',ok);$('connection-badge').innerHTML=`<i></i>${ok?'Inference service connected':'Service disconnected'}`;
 $('connect-open').innerHTML=icon('link')+(ok?'Service settings':'Connect service');
 if(ok&&health&&!health.model_available){$('signal-caption').textContent='MODEL WEIGHTS MISSING';}
}
function emptyMarkup(){return `<div class="empty-state">${icon('clock')}<div><h3>${connected?'Your event timeline starts here.':'Connect the service to see your events.'}</h3><p>${connected?'Upload media or receive a hardware capture to create a real detection event.':'Start START_SENTINEL.bat on your laptop, then connect above.'}</p></div><a href="#analyze">Analyze media ↗</a></div>`;}
function tableMarkup(items){
 if(!items.length)return emptyMarkup();
 return `<div class="table-scroll"><table><thead><tr><th>MEDIA / SOURCE</th><th>RESULT</th><th>TIME</th><th>FRAMES</th><th aria-label="View"></th></tr></thead><tbody>${items.map(e=>`<tr><td><div class="file-cell">${icon(e.kind==='video'?'scan':'camera')}<div><strong title="${esc(e.filename)}">${esc(e.filename)}</strong><small>${e.source==='hardware'?'ESP32-CAM':'Manual upload'} · ${esc(e.kind)}</small></div></div></td><td><span class="pill ${state(e)}">${labels[state(e)]||'Unconfirmed'}</span></td><td>${esc(timeLabel(e.created_at))}</td><td>${e.sampled_frames??(e.frames?.length||'—')}</td><td><button class="row-button" data-event="${esc(e.id)}" aria-label="Review ${esc(e.filename)}">↗</button></td></tr>`).join('')}</tbody></table></div>`;
}
function renderRecords(){
 const done=records.filter(complete);
 $('stat-media').textContent=connected?done.length:'—';$('stat-person').textContent=connected?done.filter(e=>e.decision==='person').length:'—';$('stat-animal').textContent=connected?done.filter(e=>e.decision==='animal').length:'—';
 $('nav-count').textContent=records.length;$('recent-total').textContent=records.length?`(${records.length})`:'';
 const recent=records.slice(0,4);$('recent-events').innerHTML=tableMarkup(recent);
 renderFiltered();
}
function renderFiltered(){
 const query=$('event-search').value.toLowerCase(),filter=$('event-filter').value;
 const filtered=records.filter(e=>e.filename.toLowerCase().includes(query)&&(filter==='all'||state(e)===filter||(filter==='hardware'&&e.source==='hardware')));
 $('all-events').innerHTML=filtered.length?tableMarkup(filtered):(records.length?'<div class="empty-state"><div><h3>No matching events.</h3><p>Try another file name or result filter.</p></div></div>':emptyMarkup());
}
$('event-search').oninput=renderFiltered;$('event-filter').onchange=renderFiltered;
function isHardwareLive(){
 const age=hardware.received_epoch==null?Infinity:Date.now()/1000-hardware.received_epoch;
 const valid=typeof hardware.pir==='boolean'&&(hardware.distance_cm===null||(typeof hardware.distance_cm==='number'&&Number.isFinite(hardware.distance_cm)&&hardware.distance_cm>=0&&hardware.distance_cm<=1000));
 return connected&&hardware.online===true&&valid&&age>=-2&&age<(hardware.stale_after_seconds||15)&&!hardware.disconnected&&(hardware.transport!=='usb'||hardware.serial?.connected===true);
}
function renderHardware(){
 const live=isHardwareLive();
 $('stat-hardware').textContent=live?'Online':'Offline';
 $('hardware-page-status').textContent=live?`${hardware.device_id||'ESP32'} · Online`:'Offline · no fresh sensor samples';
 const source=hardware.device_id||'No connection source reported';
 $('hardware-age').textContent=hardware.received_at?`${hardware.transport==='usb'?'USB':'Wi-Fi'} · ${source} · ${live?'last sample':'last sample, stale'} ${timeLabel(hardware.received_at)}`:'Waiting for device telemetry';
 $('signal-caption').textContent=live?'RECEIVED SENSOR SAMPLES':hardware.received_at?'OFFLINE · LAST SAMPLE IS STALE':'AWAITING SENSOR SAMPLES';
 $('pir-value').textContent=live?(hardware.pir?'MOTION':'CLEAR'):'Not reported';
 $('pir-dot').className='dot'+(live?(hardware.pir?' orange':' green'):'');
 $('distance-value').textContent=live?(hardware.distance_cm==null?'Invalid / no echo':`${hardware.distance_cm.toFixed(1)} cm`):'Not reported';
 $('distance-dot').className='dot'+(live&&hardware.distance_cm!=null?' green':'');
 const camera=live?(hardware.camera_state||(hardware.camera_ready==null?'Not reported':hardware.camera_ready?'Ready':'Not ready')):'Not reported';
 $('camera-value').textContent=camera;$('camera-dot').className='dot'+(live&&hardware.camera_ready===true?' green':'');
 const pairs=[['Connection',live?'Online':'Offline'],['Source',source],['Transport',hardware.transport==='usb'?'USB serial':hardware.transport==='wifi'?'Wi-Fi telemetry':'Not reported'],['PIR motion',live?(hardware.pir?'MOTION':'CLEAR'):'Not reported'],['Distance',live?(hardware.distance_cm==null?'Invalid / no echo':`${hardware.distance_cm.toFixed(1)} cm`):'Not reported'],['Camera readiness',camera],['Buzzer state',live&&typeof hardware.buzzer_active==='boolean'?(hardware.buzzer_active?'Active':'Inactive'):'Not reported'],['Last sample',hardware.received_at?timeLabel(hardware.received_at):'Never']];
 $('telemetry-list').innerHTML=pairs.map(([k,v])=>`<dt>${k}</dt><dd>${esc(v)}</dd>`).join('');
 if(typeof renderLive==='function')renderLive();
}

async function refresh(){
 try{
  const health=await api('/api/health');
  const [events,hw]=await Promise.all([api('/api/events'),api('/api/hardware')]);
  if(!Array.isArray(events))throw Error('Wrong service');
  records=events;hardware=hw;updateConnection(true,health);renderRecords();renderHardware();
  if(currentId){const e=records.find(x=>x.id===currentId);if(e)renderResult(e);}
  if($('event-dialog').open&&$('event-detail').dataset.eventId){const e=records.find(x=>x.id===$('event-detail').dataset.eventId);if(e&&['queued','processing'].includes($('event-detail').dataset.status))renderDetail(e);}
 }catch(err){updateConnection(false);renderRecords();renderHardware();}
}
let refreshBusy=false;async function poll(){if(refreshBusy)return;refreshBusy=true;try{await refresh();}finally{refreshBusy=false;}}poll();setInterval(poll,2500);
function choose(){if(!connected){openConnect();return;}$('file-input').click();}
$('dropzone').onclick=choose;$('dropzone').onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose();}};$('choose-file').onclick=choose;
['dragenter','dragover'].forEach(type=>$('dropzone').addEventListener(type,e=>{e.preventDefault();$('dropzone').classList.add('dragging');}));
['dragleave','drop'].forEach(type=>$('dropzone').addEventListener(type,e=>{e.preventDefault();$('dropzone').classList.remove('dragging');}));
$('dropzone').addEventListener('drop',e=>addFiles([...e.dataTransfer.files]));
$('file-input').onchange=e=>{addFiles([...e.target.files]);e.target.value='';};
document.querySelectorAll('[data-kind]').forEach(b=>b.onclick=()=>{
 document.querySelectorAll('[data-kind]').forEach(x=>x.classList.toggle('active',x===b));
 const types={all:'image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/x-msvideo,video/webm,.mkv',image:'image/jpeg,image/png,image/webp',video:'video/mp4,video/quicktime,video/x-msvideo,video/webm,.mkv'};
 $('file-input').accept=types[b.dataset.kind];
});
$('threshold').oninput=e=>$('threshold-value').textContent=e.target.value+'%';
function addFiles(files){
 if(!connected){openConnect();return;}
 if(!files.length)return;
 const accepted=[];
 for(const file of files){
  const isVideo=/\.(mp4|mov|avi|webm|mkv)$/i.test(file.name),isImage=/\.(jpe?g|png|webp)$/i.test(file.name);
  if(!isVideo&&!isImage){toast(`Unsupported file: ${file.name}`,true);continue;}
  if(file.size>(isVideo?200:20)*1024*1024){toast(`${file.name} exceeds the ${isVideo?200:20} MB limit.`,true);continue;}
  if(file.size===0){toast(`${file.name} is empty.`,true);continue;}
  accepted.push({file,threshold:Number($('threshold').value)/100});
 }
 queue.push(...accepted);if(accepted.length)runQueue();
}
async function runQueue(){
 if(uploading)return;uploading=true;
 while(queue.length){
  const {file,threshold}=queue.shift();
  $('analysis-result').hidden=false;$('analysis-result').innerHTML=`<div class="result-banner">${icon('upload')}<div><h3>Uploading ${esc(file.name)}</h3><p>${queue.length?`${queue.length} more file(s) waiting. `:''}Sending to your inference service…</p></div></div>`;
  const data=new FormData();data.append('file',file);data.append('threshold',threshold);
  try{const item=await api('/api/analyze',{method:'POST',body:data});currentId=item.id;lastResultSignature='';renderResult(item);
   // Respect the server's bounded queue; do not discard later files on a busy response.
   let finished=false;
   while(!finished){await new Promise(r=>setTimeout(r,1500));const result=await api(`/api/events/${item.id}`);renderResult(result);finished=['complete','failed'].includes(result.status);if(result.status==='failed')toast(`${file.name}: ${result.error}`,true);}
   await refresh();
  }catch(err){toast(`Upload or analysis interrupted: ${err.message}. Event history may contain a submitted job.`,true);$('analysis-result').innerHTML=`<div class="result-banner failed"><div><h3>Could not complete this request</h3><p>${esc(err.message)}</p><p>Check Event history before resubmitting.</p></div></div>`;lastResultSignature='';}
 }
 uploading=false;
}
function summaryMarkup(e){
 const st=state(e),pending=['queued','processing'].includes(st),hasPerson=e.decision==='person';
 const text=st==='failed'?e.error:pending?`${e.progress||0}% · ${e.frames?.length||0} frame(s) analyzed. Model loading can take a moment on the first run.`:hasPerson?'Person presence detected. Identity and authorization have not been verified.':e.decision==='animal'?'Supported animal detected. No person met the selected confidence threshold.':'No supported person or animal met the threshold. This is not proof of an empty scene.';
 return `<div class="result-banner ${st}">${icon(st==='person'?'person':st==='animal'?'paw':'scan')}<div><h3>${esc(labels[st])}</h3><p>${esc(text)}</p></div></div>${pending?`<div class="progress-track"><span style="width:${Math.max(4,e.progress||0)}%"></span></div>`:''}`;
}
function evidenceMarkup(e,scope){
 if(!e.frames?.length)return '';
 const index=selectedFrame[e.id]??Math.max(0,e.frames.findIndex(f=>f.preview===e.preview));const f=e.frames[Math.min(index,e.frames.length-1)];
 return `<img class="result-image" id="${scope}-image" src="${esc(mediaUrl(f.preview))}" alt="Annotated ${esc(e.filename)} at ${f.second} seconds"><div class="frame-strip">${e.kind==='video'?e.frames.map((fr,i)=>`<button class="frame-button ${i===index?'selected':''}" data-frame="${i}" data-record="${esc(e.id)}" data-scope="${scope}" aria-label="Inspect sampled frame at ${fr.second} seconds"><img src="${esc(mediaUrl(fr.preview))}" alt="" loading="lazy"><span>${fr.second.toFixed(1)}s</span></button>`).join(''):''}</div><div class="result-metrics"><span><strong>${e.peak_people??f.people}</strong>${e.kind==='video'?'peak people / frame':'people'}</span><span><strong>${e.peak_animals??f.animals}</strong>${e.kind==='video'?'peak animals / frame':'animals'}</span><span><strong>${e.sampled_frames??e.frames.length}</strong>frames analyzed</span><span><strong>${Math.round((e.threshold||.7)*100)}%</strong>threshold</span></div>${e.kind==='video'?`<p class="result-note">Sampled analysis of ${e.duration??'…'} seconds. ${e.sample_interval?`Approximately one frame every ${e.sample_interval.toFixed(1)} seconds.`:''} Activity between samples can be missed. Counts are not unique tracked individuals.</p>`:''}<div class="detection-list">${f.detections.length?f.detections.map(d=>`<span><strong>${esc(d.label)}</strong> ${(d.confidence*100).toFixed(1)}%</span>`).join(' &nbsp; · &nbsp; '):'No qualifying detections in this frame.'}</div>`;
}
function renderResult(e){
 const sig=[e.id,e.status,e.progress,e.frames?.length,selectedFrame[e.id]].join('|');if(sig===lastResultSignature)return;lastResultSignature=sig;
 $('analysis-result').hidden=false;$('analysis-result').innerHTML=summaryMarkup(e)+evidenceMarkup(e,'main')+(complete(e)?`<button class="button text" data-event="${esc(e.id)}">Review event details ↗</button>`:'');
}
function renderDetail(e){
 $('event-detail').dataset.eventId=e.id;$('event-detail').dataset.status=e.status;
 $('event-detail').innerHTML=`<span class="section-kicker">${e.source==='hardware'?'HARDWARE CAPTURE':'MEDIA ANALYSIS'} · ${esc(timeLabel(e.created_at))}</span><h2>${esc(e.filename)}</h2>${summaryMarkup(e)}${evidenceMarkup(e,'detail')}<p class="result-note">Authorization: not verified. ${e.inference_ms?`Total measured inference time: ${(e.inference_ms/1000).toFixed(2)} s (includes first model prediction overhead).`:''}</p>${e.telemetry?.device_id?`<p class="result-note">Device: ${esc(e.telemetry.device_id)} · PIR: ${esc(e.telemetry.pir)} · distance: ${esc(e.telemetry.distance_cm??'no echo')} cm. Telemetry is the last reported snapshot, not guaranteed to be synchronized to this frame.</p>`:''}<button class="button" data-download="${esc(e.id)}">${icon('download')}Export event JSON</button>`;
}
document.addEventListener('click',e=>{
 const review=e.target.closest('[data-event]');if(review){const item=records.find(x=>x.id===review.dataset.event);if(item){renderDetail(item);if(!$('event-dialog').open)$('event-dialog').showModal();}}
 const frame=e.target.closest('[data-frame]');if(frame){const item=records.find(x=>x.id===frame.dataset.record);if(item){selectedFrame[item.id]=Number(frame.dataset.frame);if(frame.dataset.scope==='detail')renderDetail(item);else{lastResultSignature='';renderResult(item);}}}
 const download=e.target.closest('[data-download]');if(download){const item=records.find(x=>x.id===download.dataset.download);if(item)exportJson(item,`sentinel-${item.id}.json`);}
});
function exportJson(value,name){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
$('export-events').onclick=()=>{if(!connected){toast('Connect the service to export event records.',true);return;}exportJson(records,'sentinel-events.json');};
