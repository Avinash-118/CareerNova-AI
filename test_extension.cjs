const {readFileSync}=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
class Input {
  constructor(label,type='text',value=''){this.labels=[{textContent:label}];this.type=type;this.tagName='INPUT';this._value=value;this.events=[];}
  get value(){return this._value;} set value(v){this._value=v;}
  getClientRects(){return [{}];}
  getAttribute(){return null;}
  dispatchEvent(event){this.events.push(event.type);}
}
class Textarea extends Input {}
const fields=[new Input('First name'),new Input('Email','email'),new Input('Phone','tel','keep-existing'),new Input('Sponsorship required'),new Input('Agree','checkbox'),new Input('Password','password'),new Input('Resume','file'),new Input('Full name')];
const context={document:{querySelectorAll:()=>fields},HTMLInputElement:Input,HTMLTextAreaElement:Textarea,Event:class{constructor(type){this.type=type;}}};
vm.createContext(context);vm.runInContext(readFileSync('browser_extension/fill.js','utf8'),context);
const result=context.fillProfile({first_name:'Test',last_name:'Candidate',email:'test@example.com',phone:'123',sponsorship_required:'yes'});
assert.equal(result.filled,3);assert.equal(fields[0].value,'Test');assert.equal(fields[1].value,'test@example.com');assert.equal(fields[2].value,'keep-existing');assert.equal(fields[3].value,'');assert.equal(fields[4].value,'');assert.equal(fields[5].value,'');assert.equal(fields[6].value,'');assert.equal(fields[7].value,'Test Candidate');assert.deepEqual(fields[0].events,['input','change']);
assert.equal(context.fillProfile({first_name:'Replacement'}).filled,0);
console.log('Extension fill checks passed: explicit labels, existing values, excluded choices/secrets/files, input events, repeat fill.');
const placeholders=[new Input(''),new Input(''),new Input('','email')];
placeholders[0].getAttribute=k=>k==='placeholder'?'Enter your first name':null;
placeholders[1].getAttribute=k=>k==='placeholder'?'Enter your last name':null;
context.document.querySelectorAll=()=>placeholders;
assert.equal(context.fillProfile({first_name:'Test',last_name:'Candidate',email:'test@example.com'}).filled,3);
assert.equal(placeholders[0].value,'Test');assert.equal(placeholders[1].value,'Candidate');
let mutation;let queued;let disconnected=false;
context.window={};context.document.documentElement={};
context.MutationObserver=class{constructor(cb){mutation=cb;}observe(){}disconnect(){disconnected=true;}};
context.setTimeout=(cb,ms)=>{if(ms===250)queued=cb;return ms;};context.clearTimeout=()=>{};
context.watchProfile({first_name:'Test'});
const late=new Input('First name');placeholders.push(late);mutation();queued();assert.equal(late.value,'Test');
context.window.careerNovaAutofillStop();assert.equal(disconnected,true);
console.log('Placeholder, email type and dynamically inserted field checks passed.');
