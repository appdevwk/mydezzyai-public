const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function environment(fail=false){
 const nodes=new Map(),storage=new Map();let calls=0;
 function node(){return {value:'',textContent:'',disabled:false,children:[],append(...x){this.children.push(...x)},replaceChildren(){this.children=[]}};}
 const document={getElementById(id){if(!nodes.has(id))nodes.set(id,node());return nodes.get(id)},createElement:node};
 document.getElementById('task').value='Build an app';document.getElementById('mode').value='code';
 const context={crypto:require('node:crypto').webcrypto,document,localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},window:{addEventListener(){}},URL:Object.assign(class extends URL{},{createObjectURL:()=> 'blob:test',revokeObjectURL(){}}),Blob,console,
  fetch:async(path)=>{if(path==='/api/jobs')return {ok:true,json:async()=>({jobs:[{job:{id:'restored',task:'Server saved task',status:'completed',calls:7,steps:[],sources:{},result:{report:'Saved report',validation:'mock'}}}]})};calls++;if(fail&&calls===2)throw Error('Network failed');return {ok:true,json:async()=>({state:'opaque-state',job:{id:'job',task:'Build an app',calls,status:calls===7?'completed':'running',steps:[{role:'Creator',status:'completed',text:'Saved evidence'}],sources:{'javascript:alert(1)':'Unsafe','https://example.com':'Safe'},result:calls===7?{report:'Report',python_code:'print(1)',validation:'syntax passed'}:null}})}}};
 vm.createContext(context);vm.runInContext(fs.readFileSync('web.js','utf8'),context);
 return {nodes,storage,get calls(){return calls}};
}
(async()=>{
 const ok=environment();await ok.nodes.get('run').onclick();assert.equal(ok.calls,7);assert.equal(ok.nodes.get('run').disabled,false);assert.equal(ok.nodes.get('sources').children.length,1);assert.equal(ok.nodes.get('downloads').children.length,4);assert.equal(ok.storage.size,0,'task data must not be cached unencrypted in localStorage');assert.match(ok.nodes.get('status').textContent,/completed/);await ok.nodes.get('history-refresh').onclick();assert.match(ok.nodes.get('history').children[0].textContent,/Server saved task/);ok.nodes.get('history').children[0].onclick();assert.match(ok.nodes.get('result').textContent,/Saved report/);
 const failed=environment(true);await failed.nodes.get('run').onclick();assert.equal(failed.calls,2);assert.equal(failed.nodes.get('run').disabled,false);assert.equal(failed.storage.size,0);assert.match(failed.nodes.get('status').textContent,/No automatic retry/);
 const empty=environment();empty.nodes.get('task').value=' ';await empty.nodes.get('run').onclick();assert.equal(empty.calls,0);
 console.log('Client checks passed: seven-step flow, downloads, URL filtering, interrupted connection, empty input.');
})().catch(e=>{console.error(e);process.exitCode=1});
