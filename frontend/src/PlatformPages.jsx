import {DeliveryPreferences} from "./CareerTools";
import { useEffect, useState } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { Bell, Bookmark, BriefcaseBusiness, ChartNoAxesCombined, FileText, Settings, UserRound, ArrowUpRight } from 'lucide-react';
import { request } from './api';

export function WorkspaceNav() {
  const items = [['/dashboard','Overview',ChartNoAxesCombined],['/jobs','Find jobs',BriefcaseBusiness],['/resume','Resume match',FileText],['/saved','Saved jobs',Bookmark],['/alerts','Job alerts',Bell],['/profile','Profile',UserRound],['/applications','Applications',BriefcaseBusiness],['/timeline','Timeline',ChartNoAxesCombined],['/interview','Interview prep',UserRound],['/tools','Career tools',FileText],['/settings','Settings',Settings]];
  return <nav className="workspace-nav" aria-label="Your workspace">{items.map(([to,label,Icon]) => <NavLink key={to} to={to}><Icon size={17}/>{label}</NavLink>)}</nav>;
}
function Page({eyebrow, title, description, children}) {
  return <section className="platform-page"><span className="platform-eyebrow">{eyebrow || 'YOUR CAREER, IN MOTION'}</span><h1>{title}</h1><p className="platform-intro">{description}</p>{children}</section>;
}
export function AccountRecovery({reset = false}) {
  const [email,setEmail] = useState(''); const [password,setPassword] = useState('');
  const [confirmation,setConfirmation] = useState('');
  const token = new URLSearchParams(window.location.search).get('token') || '';
  const missingToken = reset && token.length < 20;
  const [message,setMessage] = useState(''); const [error,setError] = useState(''); const [busy,setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault();
    if (reset && password !== confirmation) { setError('The passwords do not match. Please re-enter them.'); return; }
    setBusy(true);setError('');setMessage('');
    try {const result=await request(`/api/auth/${reset?'reset-password':'forgot-password'}`, {method:'POST',body:reset?{token,password}:{email}});setMessage(result.message);setPassword('');setConfirmation('');if(reset){const url=new URL(window.location.href);url.searchParams.delete('token');window.history.replaceState({},'',url);}}
    catch(err){setError(err.message);}finally{setBusy(false);}
  }
  return <Page title={reset?'Choose a new password':'Forgot your password?'} description={reset?'Use a unique password with at least 12 characters.':'Enter your account email to request a secure recovery link.'}>
    <form className="platform-card platform-form" onSubmit={submit}>
      {missingToken&&!message&&<p role="alert">This page needs a valid password-reset link. Request a new link below.</p>}
      {reset?<label>New password<input required type="password" minLength={12} maxLength={128} autoComplete="new-password" value={password} onChange={e=>setPassword(e.target.value)}/></label>:<label>Email address<input required type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)}/></label>}
      {reset&&!message&&<label>Confirm new password<input required type="password" minLength={12} maxLength={128} autoComplete="new-password" value={confirmation} onChange={e=>setConfirmation(e.target.value)}/></label>}
      {error&&<p role="alert">{error}</p>}{message&&<p role="status">{message}</p>}
      {reset&&<Link to="/forgot-password">Request a new recovery link</Link>}
      <button className="primary-button" disabled={busy||missingToken||(reset&&Boolean(message))}>{busy?'Please wait...':reset?'Update password':'Send recovery link'}</button><Link to="/login">Back to sign in</Link>
    </form>
  </Page>;
}
export function AlertCenter() {
  const [data,setData]=useState({rules:[],notifications:[]});const [query,setQuery]=useState('');const [location,setLocation]=useState('');const [error,setError]=useState('');const [message,setMessage]=useState('');const [busy,setBusy]=useState(false);const [loading,setLoading]=useState(true);
  async function load(){setData(await request('/api/alerts'));}
  useEffect(()=>{load().catch(e=>setError(e.message)).finally(()=>setLoading(false));},[]);
  async function action(path,method,body){setBusy(true);setError('');setMessage('');try{const result=await request(path,{method,body});await load();setMessage(result.message || 'Alert created');return true;}catch(e){setError(e.message);return false;}finally{setBusy(false);}}
  return <Page title="Good opportunities. On your radar." description="Create free in-app alerts for the roles and places that matter to you. Check matches whenever you visit.">
    <DeliveryPreferences/>
    {error&&<p role="alert" className="platform-feedback">{error}</p>}{message&&<p role="status" className="platform-feedback">{message}</p>}
    <div className="platform-columns"><div><form className="platform-card platform-form" onSubmit={async e=>{e.preventDefault();if(await action('/api/alerts','POST',{query,location})){setQuery('');setLocation('');}}}>
      <span className="platform-eyebrow">STAY A STEP AHEAD</span><h2>Create a job alert</h2><label>Role or keywords<input required minLength={2} maxLength={160} placeholder="e.g. Python developer" value={query} onChange={e=>setQuery(e.target.value)}/></label><label>Location (optional)<input maxLength={160} placeholder="e.g. Chicago or Remote" value={location} onChange={e=>setLocation(e.target.value)}/></label><button className="primary-button" disabled={busy}>Create free alert <Bell size={17}/></button><small>In-app delivery · Up to 20 alerts · No subscription</small>
    </form><div className="platform-card"><h2>Your alerts</h2>{loading?<p role="status">Loading alerts...</p>:!data.rules.length?<p>Create your first alert above.</p>:data.rules.map(rule=><div className="platform-rule" key={rule.id}><div><strong>{rule.query}</strong><small>{rule.location || 'Everywhere'} · {rule.enabled?'Active':'Paused'}</small></div><button disabled={busy} onClick={()=>action(`/api/alerts/${rule.id}`,'PATCH',{enabled:!rule.enabled})}>{rule.enabled?'Pause':'Resume'}</button><button disabled={busy} onClick={()=>action(`/api/alerts/${rule.id}`,'DELETE')}>Delete</button></div>)}</div></div>
    <div className="platform-card"><div className="platform-card-heading"><div><span className="platform-eyebrow">YOUR INBOX</span><h2>Matching opportunities</h2></div><Bell size={24}/></div><div className="platform-actions"><button className="primary-button" disabled={busy} onClick={()=>action('/api/alerts/check','POST')}>{busy?'Checking...':'Check new matches'}</button><button disabled={busy} onClick={()=>action('/api/notifications/read','POST')}>Mark all read</button></div><p className="platform-muted">Checks current live feeds. Matches appear here and are deduplicated per alert. Background checks run when the alert worker is active. Manage email digests and verification in your notification preferences.</p>
      {!loading&&!data.notifications.length&&<div className="platform-empty"><Bell size={36}/><h3>Your next opportunity starts here</h3><p>Create an alert, then check for matching roles.</p><Link to="/jobs">Explore jobs <ArrowUpRight size={15}/></Link></div>}
      {data.notifications.map(n=><article className="platform-notification" key={n.id}><span className="platform-eyebrow">{n.read?'MATCH':'NEW MATCH'}</span><h3>{n.title}</h3><p>{n.company}</p>{/^https?:\/\//i.test(n.url||'')&&<a href={n.url} target="_blank" rel="noopener noreferrer">View opportunity <ArrowUpRight size={15}/></a>}</article>)}
    </div></div>
  </Page>;
}
export function SettingsPage(){
  const [user,setUser]=useState(null);const [name,setName]=useState('');const [message,setMessage]=useState('');const [error,setError]=useState('');const [busy,setBusy]=useState(false);
  useEffect(()=>{request('/api/auth/me').then(u=>{setUser(u);setName(u.full_name);}).catch(e=>setError(e.message));},[]);
  return <Page title="Make yourself at home." description="Manage your account and keep your career workspace up to date."><div className="platform-columns"><form className="platform-card platform-form" onSubmit={async e=>{e.preventDefault();setBusy(true);setError('');try{await request('/api/auth/me',{method:'PATCH',body:{full_name:name}});setMessage('Account updated.');}catch(err){setError(err.message);}finally{setBusy(false);}}}><h2>Account details</h2><label>Full name<input required minLength={2} maxLength={200} value={name} onChange={e=>setName(e.target.value)}/></label><label>Email<input readOnly value={user?.email || ''}/></label>{message&&<p role="status">{message}</p>}{error&&<p role="alert">{error}</p>}<button className="primary-button" disabled={busy||!user}>{busy?'Saving...':'Save changes'}</button></form><div className="platform-card"><h2>Security & preferences</h2><Link className="secondary-button" to="/privacy">Privacy, sessions & provider sign-in</Link><p>Your session expires after eight hours. Signing out revokes this session immediately.</p><Link className="secondary-button" to="/forgot-password">Change password securely</Link><hr/><h3>Job notifications</h3><p>Manage your free in-app alert rules, pause them, or clear alerts you no longer need.</p><Link className="secondary-button" to="/alerts">Manage alerts</Link><hr/><h3>Candidate information</h3><p>Keep your skills and application details current for resume matching and Nova.</p><Link className="secondary-button" to="/profile">Edit candidate profile</Link></div></div></Page>;
}
