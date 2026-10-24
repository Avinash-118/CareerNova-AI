/* Executed only after the user clicks Fill this page (activeTab permission). */
function fillProfile(profile) {
  const aliases={
    'first name':'first_name','given name':'first_name','last name':'last_name','family name':'last_name','surname':'last_name',
    'email':'email','email address':'email','phone':'phone','phone number':'phone','mobile number':'phone',
    'location':'location','current location':'location','city':'location',
    'linkedin':'linkedin_url','linkedin url':'linkedin_url','linkedin profile':'linkedin_url',
    'github':'github_url','github url':'github_url','portfolio':'portfolio_url','portfolio url':'portfolio_url',
    'university':'university','university college':'university','degree':'degree','years of experience':'experience_years','skills':'skills','education':'education'
  };
  const normalize=s=>String(s||'').replace(/([a-z])([A-Z])/g,'$1 $2').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim().replace(/^(?:please )?(?:enter|type|provide) (?:your )?/, '').replace(/^(?:your) /,'');
  const autocomplete={'given-name':'first_name','family-name':'last_name','email':'email','tel':'phone','url':'portfolio_url'};
  let filled=0,failed=0;
  for(const el of document.querySelectorAll('input,textarea')) {
    if(el.disabled||el.readOnly||el.value||!el.getClientRects().length)continue;
    if(el.tagName==='INPUT'&&!['text','email','tel','url','number','search'].includes(el.type))continue;
    const labels=[...Array.from(el.labels||[]).map(l=>l.textContent),el.getAttribute('aria-label'),el.getAttribute('placeholder'),el.name,el.id];
    const keys=new Set(labels.map(normalize).map(label=>aliases[label]).filter(Boolean));
    const auto=autocomplete[(el.getAttribute('autocomplete')||'').split(/\s+/).pop()];
    if(auto)keys.add(auto);
    if(el.type==='email')keys.add('email');
    if(el.type==='tel')keys.add('phone');
    if(keys.size>1)continue;
    const key=[...keys][0];
    const fullName=labels.some(l=>['name','full name','legal name'].includes(normalize(l)));
    let value=key?profile[key]:fullName?[profile.first_name,profile.last_name].filter(Boolean).join(' '):'';
    if(!value)continue;
    const prototype=el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
    const setter=Object.getOwnPropertyDescriptor(prototype,'value').set;
    setter.call(el,String(value));
    el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));
    if(el.value===String(value))filled++;else failed++;
  }
  return {filled,failed};
}

function watchProfile(profile) {
  window.careerNovaAutofillStop?.();
  const initial=fillProfile(profile);
  let timer;
  const observer=new MutationObserver(()=>{
    clearTimeout(timer);
    timer=setTimeout(()=>fillProfile(profile),250);
  });
  observer.observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['placeholder','aria-label','disabled','readonly','style','class']});
  const stop=()=>{observer.disconnect();clearTimeout(timer);clearTimeout(expiry);};
  const expiry=setTimeout(stop,10*60*1000);
  window.careerNovaAutofillStop=stop;
  return initial;
}
