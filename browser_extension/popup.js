const status=document.getElementById('status');
const fill=document.getElementById('fill');
chrome.storage.local.get('profile').then(({profile})=>{fill.disabled=!profile;if(profile)status.textContent='Profile ready on this device.';});
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
document.getElementById('clear').addEventListener('click',async()=>{await chrome.storage.local.remove('profile');fill.disabled=true;status.textContent='Imported profile removed from this device.';});
fill.addEventListener('click',async()=>{
  fill.disabled=true;
  try{
    const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
    if(!/^https?:\/\//.test(tab.url||''))throw new Error('Open an employer application page first.');
    const {profile}=await chrome.storage.local.get('profile');if(!profile)throw new Error('Import your profile first.');
    await chrome.scripting.executeScript({target:{tabId:tab.id},files:['fill.js']});
    const result=await chrome.scripting.executeScript({target:{tabId:tab.id},func:p=>fillProfile(p),args:[profile]});
    const summary=result[0]?.result;status.textContent=`${summary?.filled||0} fields filled. ${summary?.failed||0} could not be verified. Review the page; select menus, embedded frames, resume uploads and submission remain manual.`;
  }catch(err){status.textContent='Could not fill this page: '+err.message;}finally{fill.disabled=false;}
});
