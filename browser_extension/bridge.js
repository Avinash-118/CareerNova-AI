// Only installed on CareerNova's production origin. No credentials cross this bridge.
window.addEventListener('message',async event=>{
  if(event.source!==window||event.origin!==location.origin)return;
  const data=event.data;
  if(data?.channel!=='careernova-extension'||!['PING','START'].includes(data.type))return;
  try {
    const result=data.type==='PING'?{ready:true}:await chrome.runtime.sendMessage({type:'START',profile:data.profile,url:data.url});
    window.postMessage({channel:'careernova-extension-result',id:data.id,...result},location.origin);
  }catch{window.postMessage({channel:'careernova-extension-result',id:data.id,error:'Reload the CareerNova tab after updating the extension.'},location.origin);}
});
