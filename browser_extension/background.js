const trusted='https://career-nova-ai-one.vercel.app';
const allowed=['first_name','last_name','email','phone','location','linkedin_url','github_url','portfolio_url','university','degree','experience_years','skills','education'];
function cleanProfile(profile){
  if(!profile||typeof profile.email!=='string')throw new Error('Save your Candidate Profile first.');
  return Object.fromEntries(allowed.filter(k=>['string','number'].includes(typeof profile[k])).map(k=>[k,String(profile[k]).slice(0,10000)]));
}
async function fillTab(tabId){
  const {applications={}}=await chrome.storage.session.get('applications');
  const session=applications[tabId];
  if(!session||session.expires<Date.now())return;
  await chrome.action.setBadgeText({tabId,text:'GO'});
  const tab=await chrome.tabs.get(tabId);
  if(!tab.url?.startsWith('https://'))return;
  const pattern=new URL(tab.url).origin+'/*';
  if(!await chrome.permissions.contains({origins:[pattern]})){
    await chrome.action.setBadgeText({tabId,text:'GO'});return;
  }
  await chrome.scripting.executeScript({target:{tabId},files:['fill.js']});
  await chrome.scripting.executeScript({target:{tabId},func:p=>watchProfile(p),args:[session.profile]});
  await chrome.action.setBadgeText({tabId,text:'ON'});
}
chrome.runtime.onMessage.addListener((data,sender,reply)=>{
  (async()=>{
    if(data?.type==='START'){
      if(!sender.tab||new URL(sender.url).origin!==trusted)throw new Error('Untrusted profile source.');
      const url=new URL(data.url);if(url.protocol!=='https:'||url.username||url.password)throw new Error('Use an HTTPS employer application link.');
      const profile=cleanProfile(data.profile);
      const tab=await chrome.tabs.create({url:url.href});
      const {applications={}}=await chrome.storage.session.get('applications');
      // Browser-session storage, scoped to the application tab, expires after 15 minutes.
      for(const key of Object.keys(applications))if(applications[key].expires<Date.now())delete applications[key];
      applications[tab.id]={profile,expires:Date.now()+15*60*1000};
      await chrome.storage.session.set({applications});
      await chrome.action.setBadgeText({tabId:tab.id,text:'GO'});
      await fillTab(tab.id);
      return {started:true};
    }
    if(data?.type==='ENABLE'){
      if(sender.tab||sender.id!==chrome.runtime.id)throw new Error('Use the extension popup.');
      await fillTab(data.tabId);return {ready:true};
    }
    throw new Error('Unknown request.');
  })().then(reply,error=>reply({error:error.message}));
  return true;
});
chrome.tabs.onUpdated.addListener((tabId,change)=>{if(change.status==='complete')fillTab(tabId).catch(()=>{});});
chrome.tabs.onRemoved.addListener(async tabId=>{
  const {applications={}}=await chrome.storage.session.get('applications');delete applications[tabId];await chrome.storage.session.set({applications});
});
