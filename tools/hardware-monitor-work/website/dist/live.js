'use strict';
let liveBusy=false, portsBusy=false, serialAction=false;
function renderLive(){
 const age=hardware.received_epoch==null?Infinity:Math.max(0,Date.now()/1000-hardware.received_epoch);
 const live=isHardwareLive();
 const usb=hardware.serial||{};
 $('live-badge').className=`pill ${live?'animal':usb.connected?'processing':''}`;
 $('live-badge').textContent=live?`Online · ${hardware.transport==='usb'?'USB':'Wi-Fi'}`:usb.connected?'Offline · USB open, no fresh samples':'Offline · waiting for ESP32';
 $('live-pir').textContent=live?(hardware.pir?'MOTION':'CLEAR'):'—';
 $('live-pir').classList.toggle('motion-on',live&&hardware.pir);
 $('live-distance').innerHTML=live?(hardware.distance_cm==null?'No echo':`${Number(hardware.distance_cm).toFixed(1)} <em>cm</em>`):'— <em>cm</em>';
 $('live-distance-note').textContent=live?(hardware.distance_cm==null?'Invalid distance; not an empty-area indication':hardware.distance_cm<=80?'Within documented trigger zone':'Outside documented trigger zone'):'Waiting for valid echo';
 $('live-agreement').textContent=live&&hardware.agreement!=null?`${hardware.agreement}/${hardware.agreement_required||3}`:'—';
 $('live-controller').textContent=live?(hardware.controller_state||'Not reported'):'—';
 $('live-age').textContent=Number.isFinite(age)?`Last sample ${age<2?'just now':`${Math.floor(age)}s ago`}`:'No sample received';
 if(live)$('hardware-age').textContent=`${hardware.transport==='usb'?'USB':'Wi-Fi'} · updated ${age<2?'just now':`${Math.floor(age)}s ago`}`;
 if(!serialAction){$('usb-connect').disabled=!!usb.connected||!connected||!$('serial-port').value;$('usb-disconnect').disabled=!usb.connected;}
 $('serial-port').disabled=serialAction||!!usb.connected;
 $('serial-baud').disabled=serialAction||!!usb.connected;
 $('refresh-ports').disabled=serialAction||portsBusy;
 $('live-camera').textContent=live?(hardware.camera_state||(hardware.camera_ready==null?'Not reported':hardware.camera_ready?'Ready':'Not ready')):'Not reported';
 $('live-buzzer').textContent=live&&typeof hardware.buzzer_active==='boolean'?(hardware.buzzer_active?'Active':'Inactive'):'Not reported';
 $('live-source').textContent=hardware.device_id||'Not reported';
 $('live-sample-time').textContent=hardware.received_at?`${new Date(hardware.received_at).toLocaleString()}${live?'':' · stale / offline'}`:'No sample received';
 if(usb.error)$('usb-message').textContent=usb.error;
 else if(usb.connected){
  $('usb-message').textContent=usb.samples_received?`${usb.port} · ${usb.baudrate} baud · ${usb.samples_received} sensor samples received. ${live?'Live readings are updating.':'No fresh readings. Check board power and sensor output.'}`:`${usb.port} open at ${usb.baudrate} baud. ${usb.lines_received||0} lines received; waiting for recognized PIR and distance readings. If this stays unchanged, check the baud rate and log format.`;
 }
 const history=(hardware.history||[]).filter(p=>p.received_epoch>=Date.now()/1000-60&&p.transport===hardware.transport&&p.device_id===hardware.device_id&&(hardware.transport!=='usb'||p.session_id===hardware.session_id));
 drawChart($('distance-chart'),history,'distance_cm');drawChart($('motion-chart'),history,'pir');
 // The overview trace now reflects actual distance samples rather than a decorative waveform.
 const mini=document.querySelector('.signal-art svg');
 if(history.some(p=>p.distance_cm!=null)){
  const values=history.filter(p=>p.distance_cm!=null),max=Math.max(100,...values.map(p=>p.distance_cm));
  let path='',last=null;for(const p of history){if(p.distance_cm==null){last=null;continue;}const x=300*(p.received_epoch-(Date.now()/1000-60))/60,y=55-p.distance_cm/max*43;path+=`${last==null||p.received_epoch-last>3?'M':'L'}${x.toFixed(1)},${y.toFixed(1)} `;last=p.received_epoch;}
  mini.innerHTML=`<path d="M0 55H300" stroke="#d4dcd6" stroke-width="1" stroke-dasharray="4 5"/><path d="${path}" stroke="#72975c" stroke-width="2" fill="none"/>`;
  mini.setAttribute('aria-label','Actual ultrasonic distance samples over the last sixty seconds');
 }else{mini.innerHTML='<path d="M0 40H300" stroke="#d4dcd6" stroke-width="1" stroke-dasharray="4 5" fill="none"/>';mini.setAttribute('aria-label','No recent ultrasonic samples');}
}
function drawChart(svg,samples,key){
 const end=Date.now()/1000,start=end-60,isMotion=key==='pir';
 const valid=samples.filter(p=>p[key]!=null&&typeof p[key]===(isMotion?'boolean':'number'));
 const max=isMotion?1:Math.max(100,Math.ceil(Math.max(0,...valid.map(p=>p[key]))/50)*50);
 const x=t=>44+Math.max(0,Math.min(60,t-start))/60*500,y=v=>132-Number(v)/max*105;
 const grid=[0,max/2,max].map(v=>`<path d="M44 ${y(v)}H544" class="chart-grid"/><text x="34" y="${y(v)+4}" text-anchor="end">${isMotion?(v===1?'HIGH':v===0?'LOW':''):Math.round(v)}</text>`).join('');
 let path='',previous=null;
 for(const p of samples){
  if(p[key]==null){previous=null;continue;}
  const px=x(p.received_epoch).toFixed(1),py=y(p[key]).toFixed(1);
  if(!previous||p.received_epoch-previous.received_epoch>3.5)path+=`M${px} ${py} `;
  else if(isMotion)path+=`L${px} ${y(previous[key]).toFixed(1)} L${px} ${py} `;
  else path+=`L${px} ${py} `;
  previous=p;
 }
 const threshold=!isMotion?`<path d="M44 ${y(80)}H544" class="chart-threshold"/><text x="540" y="${y(80)-5}" text-anchor="end">80 cm trigger zone</text>`:'';
 const dot=valid.length?`<circle cx="${x(valid.at(-1).received_epoch)}" cy="${y(valid.at(-1)[key])}" r="3" class="chart-dot"/>`:'';
 svg.innerHTML=`${grid}${threshold}<path d="${path}" class="chart-line"/>${dot}<text x="44" y="157">60s ago</text><text x="544" y="157" text-anchor="end">now</text>${valid.length?'':`<text x="294" y="90" text-anchor="middle">Waiting for ${isMotion?'motion':'valid distance'} samples</text>`}`;
}
async function loadPorts(){
 if(portsBusy)return;portsBusy=true;const button=$('refresh-ports');button.disabled=true;
 try{
  if(!connected){openConnect();return;}
  const data=await api('/api/serial/ports'),selection=$('serial-port').value;
  $('serial-port').innerHTML='<option value="">Select ESP32 port</option>'+data.ports.map(p=>`<option value="${esc(p.port)}">${esc(p.port)} · ${esc(p.description)}</option>`).join('');
  if(data.ports.some(p=>p.port===selection))$('serial-port').value=selection;
  else if(data.status.connected&&data.ports.some(p=>p.port===data.status.port))$('serial-port').value=data.status.port;
  if(!data.status.connected)$('usb-message').textContent=data.ports.length?'Choose the main ESP32 port and close Serial Monitor before connecting.':'No serial ports detected on the laptop. Connect the ESP32 with a USB data cable, then refresh ports.';
 }catch(err){$('usb-message').textContent=`Cannot list USB ports: ${err.message}`;}finally{portsBusy=false;button.disabled=false;renderLive();}
}
$('serial-port').onchange=renderLive;
$('refresh-ports').onclick=loadPorts;
$('usb-connect').onclick=async()=>{
 const port=$('serial-port').value;if(!port){toast('Refresh ports and select your main ESP32 first.',true);return;}
 if(serialAction)return;
 serialAction=true;$('usb-connect').disabled=true;$('usb-disconnect').disabled=true;renderLive();
 try{await api('/api/serial/connect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({port,baudrate:Number($('serial-baud').value)})});toast('USB connected. Waiting for real sensor readings.');await livePoll();}
 catch(err){$('usb-message').textContent=err.message;toast(err.message,true);}
 finally{serialAction=false;renderLive();}
};
$('usb-disconnect').onclick=async()=>{
 if(serialAction)return;
 serialAction=true;$('usb-disconnect').disabled=true;$('usb-connect').disabled=true;renderLive();
 try{await api('/api/serial/disconnect',{method:'POST'});$('usb-message').textContent='USB disconnected. You can now reopen Arduino Serial Monitor.';await livePoll();}
 catch(err){toast(err.message,true);}finally{serialAction=false;renderLive();}
};
async function livePoll(){
 if(liveBusy)return;liveBusy=true;
 try{hardware=await api('/api/hardware');renderHardware();}
 catch{hardware={...hardware,online:false};renderHardware();}
 finally{liveBusy=false;}
}
// Every entry point (including Overview links and a direct #hardware URL) lists
// ports; listing never opens a serial connection.
let lastHardwarePage=false;
function hardwareNavigation(){const here=location.hash==='#hardware'&&connected;if(here&&!lastHardwarePage)loadPorts();lastHardwarePage=here;}
window.addEventListener('hashchange',hardwareNavigation);
setInterval(()=>{renderHardware();hardwareNavigation();if(connected)livePoll();},1000);
renderLive();
