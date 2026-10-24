const fs=require('node:fs');const vm=require('node:vm');const assert=require('node:assert/strict');
let listener,updated,removed;let store={};let grants=false;let scripts=[];
const chrome={runtime:{id:'test-extension',onMessage:{addListener:f=>listener=f}},
  storage:{session:{get:async()=>store,set:async data=>Object.assign(store,data)}},
  tabs:{create:async()=>({id:7}),get:async()=>({url:'https://employer.example/application'}),onUpdated:{addListener:f=>updated=f},onRemoved:{addListener:f=>removed=f}},
  action:{setBadgeText:async()=>{}},permissions:{contains:async()=>grants},scripting:{executeScript:async args=>scripts.push(args)}};
vm.runInNewContext(fs.readFileSync('browser_extension/background.js','utf8'),{chrome,URL,Date});
const send=(data,sender)=>new Promise(resolve=>listener(data,sender,resolve));
(async()=>{
  const data={type:'START',url:'https://employer.example/application',profile:{email:'test@example.com',first_name:'Test',password:'excluded'}};
  const blocked=await send(data,{tab:{id:1},url:'https://attacker.example'});assert.match(blocked.error,/Untrusted/);assert.equal(store.applications,undefined);
  const invalid=await send({...data,url:'javascript:alert(1)'},{tab:{id:1},url:'https://career-nova-ai-one.vercel.app/jobs'});assert.match(invalid.error,/HTTPS/);
  const started=await send(data,{tab:{id:1},url:'https://career-nova-ai-one.vercel.app/jobs'});assert.equal(started.started,true);
  assert.equal(store.applications[7].profile.password,undefined);assert.equal(scripts.length,0);
  grants=true;await send({type:'ENABLE',tabId:7},{id:'test-extension'});assert.equal(scripts.length,2);
  await send({type:'ENABLE',tabId:99},{id:'test-extension'});assert.equal(scripts.length,2);
  store.applications[7].expires=0;await send({type:'ENABLE',tabId:7},{id:'test-extension'});assert.equal(scripts.length,2);
  await removed(7);assert.equal(store.applications[7],undefined);
  console.log('Connection tests passed: trusted origin, HTTPS, profile whitelist, permissions, tab scope, expiry and cleanup.');
})().catch(e=>{console.error(e);process.exitCode=1;});
