const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm');
function setup(denyMic) {
 const nodes = new Map();
 function node(){return {value:'',textContent:'',disabled:false,children:[],append(...x){this.children.push(...x)},replaceChildren(...x){this.children=[...x]}};}
 const document={getElementById(id){if(!nodes.has(id))nodes.set(id,node());return nodes.get(id)},createElement:node,body:node()};
 let disconnected=0, handlers={};
 class Room {
  constructor(){this.localParticipant={setMicrophoneEnabled:async()=>{if(denyMic)throw Error('Microphone permission denied')}};}
  on(event,fn){handlers[event]=fn;}
  async connect(){}
  async disconnect(){disconnected++;handlers.disconnected?.();}
 }
 const ctx={document,localStorage:{getItem:()=>null},window:{addEventListener(){},LivekitClient:{Room,RoomEvent:{TrackSubscribed:'track',TrackUnsubscribed:'untrack',Disconnected:'disconnected'}}},URL,Blob,console,fetch:async()=>({ok:true,json:async()=>({url:'wss://test.livekit.cloud',token:'fake'})})};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync('web.js','utf8'),ctx);
 return {ctx,nodes,handlers,get disconnected(){return disconnected}};
}
(async()=>{
 const denied=setup(true);await denied.nodes.get('livekit-connect').onclick();assert.equal(denied.disconnected,1,'microphone rejection must close the connected room');assert.equal(denied.nodes.get('livekit-connect').disabled,false);assert.equal(denied.nodes.get('livekit-disconnect').disabled,true);assert.match(denied.nodes.get('livekit-status').textContent,/permission denied/);
 const ok=setup(false);await ok.nodes.get('livekit-connect').onclick();const video={};ok.handlers.track({kind:'video',attach:()=>video});assert.equal(ok.nodes.get('livekit-avatar').children[0],video);assert.equal(video.autoplay,true);assert.equal(video.playsInline,true);await ok.nodes.get('livekit-disconnect').onclick();assert.equal(ok.disconnected,1);assert.equal(ok.nodes.get('livekit-avatar').children.length,0);
 const html=fs.readFileSync('core.py','utf8');assert.match(html,/<div id="livekit-avatar"/,'video tracks require a container, not a nested video fallback');assert.doesNotMatch(html,/<video id="livekit-avatar"/);
 console.log('LiveKit regression checks passed: microphone-denial room cleanup, video track container and disconnect cleanup.');
})().catch(e=>{console.error(e);process.exitCode=1});
