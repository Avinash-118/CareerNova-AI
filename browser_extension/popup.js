const status=document.getElementById('status');
const fill=document.getElementById('fill');
const auto=document.getElementById('auto');
let activeTab;let connectedProfile;
async function currentProfile(){
  const {applications={}}=await chrome.storage.session.get('applications');
  const session=applications[activeTab?.id];
  if(session?.expires>Date.now())return session.profile;
  return (await chrome.storage.local.get('profile')).profile;
}
(async()=>{
  [activeTab]=await chrome.tabs.query({active:true,currentWindow:true});
  connectedProfile=await currentProfile();fill.disabled=!connectedProfile;
  const {applications={}}=await chrome.storage.session.get('applications');
  auto.disabled=!(applications[activeTab?.id]?.expires>Date.now())||!activeTab?.url?.startsWith('https://');
  status.textContent=connectedProfile?'Profile connected. Enable automatic filling to continue across pages on this employer site.':'On CareerNova, choose Start automatic application filling. No profile file is needed.';
})().catch(e=>status.textContent=e.message);
auto.addEventListener('click',()=>{
  const origins=[new URL(activeTab.url).origin+'/*'];
  // Must run directly in the user gesture; request only this employer origin.
  chrome.permissions.request({origins}).then(async granted=>{
    if(!granted){status.textContent='Site access was not granted. Use Fill this page instead.';return;}
    const result=await chrome.runtime.sendMessage({type:'ENABLE',tabId:activeTab.id});
    if(result.error)throw new Error(result.error);
    status.textContent='Automatic filling enabled for this application tab. New pages on this approved site fill automatically. For a different employer domain, enable it there too.';
  }).catch(e=>status.textContent=e.message);
});
document.getElementById('profile').addEventListener('change',async e=>{
  try{
    const file=e.target.files[0];if(!file||file.size>100000)throw new Error('Choose a CareerNova profile JSON file under 100 KB.');
    const data=JSON.parse(await file.text());
    if(!data.profile||typeof data.profile!=='object'||typeof data.profile.email!=='string')throw new Error('Invalid profile export.');
    const allowed=['first_name','last_name','email','phone','location','linkedin_url','github_url','portfolio_url','university','degree','experience_years','skills','education'];
    const profile=Object.fromEntries(allowed.filter(k=>typeof data.profile[k]==='string').map(k=>[k,data.profile[k].slice(0,10000)]));
    await chrome.storage.local.set({profile});fill.disabled=false;status.textContent='Profile imported. Open the application, then click Fill this page.';
  }catch(err){status.textContent=err.message;}
});
document.getElementById('clear').addEventListener('click',async()=>{
  await chrome.storage.local.remove('profile');
  const {applications={}}=await chrome.storage.session.get('applications');delete applications[activeTab?.id];await chrome.storage.session.set({applications});
  try{await chrome.scripting.executeScript({target:{tabId:activeTab.id},func:()=>window.careerNovaAutofillStop?.()});}catch{}
  fill.disabled=true;auto.disabled=true;status.textContent='Profile disconnected and automatic filling stopped on this tab.';
});
fill.addEventListener('click',async()=>{
  fill.disabled=true;
  try{
    const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
    if(!/^https?:\/\//.test(tab.url||''))throw new Error('Open an employer application page first.');
    const profile=await currentProfile();if(!profile)throw new Error('Connect from CareerNova first, or import a profile file.');
    await chrome.scripting.executeScript({target:{tabId:tab.id},files:['fill.js']});
    const result=await chrome.scripting.executeScript({target:{tabId:tab.id},func:p=>watchProfile(p),args:[profile]});
    const summary=result[0]?.result;status.textContent=`${summary?.filled||0} fields filled. Watching this page for new fields for 10 minutes. After a redirect to a new page, click Fill this page again. Select menus, embedded frames, uploads and submission remain manual.`;
  }catch(err){status.textContent='Could not fill this page: '+err.message;}finally{fill.disabled=false;}
});
