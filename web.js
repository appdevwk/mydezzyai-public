const el=id=>document.getElementById(id);
const storageKey='mydezzyai-web-jobs-v1';
let jobs=[],spoken='',running=false,urls=[];
let livekitRoom=null;
try{const saved=JSON.parse(localStorage.getItem(storageKey)||'[]');if(Array.isArray(saved))jobs=saved.filter(x=>x&&x.job&&typeof x.job.task==='string'&&Array.isArray(x.job.steps)).slice(0,30);}catch(e){el('status').textContent='Browser history is unavailable; downloads still work.';}
function save(){try{localStorage.setItem(storageKey,JSON.stringify(jobs.slice(0,30)));}catch(e){el('status').textContent+=' · History could not be saved; download your result.';}}
function history(){el('history').replaceChildren();jobs.forEach(item=>{const b=document.createElement('button');b.textContent=item.job.task.slice(0,65)+' · '+(item.job.status==='running'&&!running?'interrupted':item.job.status);b.disabled=running;b.onclick=()=>render(item.job);el('history').append(b);});}
function link(parent,label,path){const a=document.createElement('a');a.textContent=label;a.href=path;a.rel='noopener noreferrer';parent.append(a,document.createElement('br'));return a;}
function download(label,text,name){const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));urls.push(url);link(el('downloads'),label,url).download=name;}
function render(j){
 el('status').textContent=j.status+' · '+j.calls+'/7 requests'+(j.error?' · '+j.error:'');
 el('steps').replaceChildren();j.steps.forEach(s=>{const li=document.createElement('li');li.textContent=s.role+': '+s.status;el('steps').append(li);});
 spoken=j.result?.report||'';el('result').textContent=j.result?j.result.report+'\n\n'+j.result.validation:(j.steps.filter(s=>s.text).at(-1)?.text||'Working…');
 el('sources').replaceChildren();Object.entries(j.sources||{}).forEach(([url,title])=>{try{const u=new URL(url);if(!['https:','http:'].includes(u.protocol))return;const li=document.createElement('li');link(li,title,url);el('sources').append(li);}catch(e){}});
 urls.forEach(url=>URL.revokeObjectURL(url));urls=[];el('downloads').replaceChildren();
 if(j.result){download('Download report',j.result.report,'report.md');if(j.result.python_code)download('Download Python code',j.result.python_code,'generated_app.py');}
}
el('run').onclick=async()=>{
 if(running)return;const task=el('task').value.trim(),mode=el('mode').value;
 if(!task||task.length>8000){el('status').textContent='Enter a task between 1 and 8,000 characters.';return;}
 running=true;el('run').disabled=true;history();let item=null;
 try{
  for(let step=0;step<7;step++){
   el('status').textContent='Running step '+(step+1)+' of 7. Keep this page open.';
   const response=await fetch('/api/step',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Dezzy-Request':'1'},body:JSON.stringify(item?{state:item.state}:{task,mode})});
   const data=await response.json();if(!response.ok)throw Error(data.error||'Request failed.');
   item=data;const index=jobs.findIndex(x=>x.job.id===item.job.id);if(index<0)jobs.unshift(item);else jobs[index]=item;
   jobs=jobs.slice(0,30);render(item.job);save();if(item.job.status!=='running')break;
  }
 }catch(e){
  if(item){item.job.status='interrupted';item.job.error='The connection ended. No automatic retry was made; starting again may duplicate paid work.';save();render(item.job);}
  el('status').textContent=e.message+' Saved steps are retained. No automatic retry was made.';
 }finally{running=false;el('run').disabled=false;history();}
};
el('read').onclick=()=>{if(!('speechSynthesis' in window)){el('status').textContent='This browser does not support speech.';return;}speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(spoken.slice(0,12000));u.lang='en-US';speechSynthesis.speak(u);};
el('stop').onclick=()=>{if('speechSynthesis' in window)speechSynthesis.cancel();};
window.addEventListener('beforeunload',event=>{if(running){event.preventDefault();event.returnValue='';}});
history();

async function connectLiveKit(){
 const status=el('livekit-status'), connect=el('livekit-connect'), disconnect=el('livekit-disconnect'), avatar=el('livekit-avatar');
 if(!window.LivekitClient){status.textContent='LiveKit client could not load.';return;}
 connect.disabled=true;status.textContent='Requesting a secure LiveKit token…';
 try{
  const response=await fetch('/api/livekit/token',{credentials:'same-origin'}), data=await response.json();
  if(!response.ok)throw Error(data.error||'LiveKit is not configured.');
  const {Room,RoomEvent}=window.LivekitClient; livekitRoom=new Room({adaptiveStream:true,dynacast:true});
  livekitRoom.on(RoomEvent.TrackSubscribed,(track)=>{const element=track.attach();if(track.kind==='video'){avatar.replaceChildren(element);element.autoplay=true;element.playsInline=true;}else document.body.append(element);});
  livekitRoom.on(RoomEvent.TrackUnsubscribed,(track)=>track.detach().forEach(node=>node.remove()));
  livekitRoom.on(RoomEvent.Disconnected,()=>{status.textContent='Disconnected from DEZZY.';connect.disabled=false;disconnect.disabled=true;});
  await livekitRoom.connect(data.url,data.token); await livekitRoom.localParticipant.setMicrophoneEnabled(true); status.textContent='Connected to DEZZY. Waiting for her voice/avatar track…';disconnect.disabled=false;
 }catch(error){status.textContent=error.message;connect.disabled=false;disconnect.disabled=true;}
}
async function disconnectLiveKit(){if(livekitRoom){await livekitRoom.disconnect();livekitRoom=null;}const avatar=el('livekit-avatar');avatar.replaceChildren();el('livekit-connect').disabled=false;el('livekit-disconnect').disabled=true;el('livekit-status').textContent='Disconnected.';}
el('livekit-connect').onclick=connectLiveKit;el('livekit-disconnect').onclick=disconnectLiveKit;
