import {applicationJob} from './resumeApplication.mjs';
import JobPreparation from './JobPreparation';
import NovaChatbot from "./NovaChatbot";
import {SavedSearchControls,SavedSearchPage,ApplicationTimeline} from "./SearchTimeline";
import {CareerTools,ApplicationBoard,ResumeLibrary,InterviewStudio,RemindersPage,JobComparison,TrustCenter,PrivacyPage,VerifyEmail,AdminPage,JobTrustActions,ProviderButtons} from "./CareerTools";
import { API_URL, apiFetch, request } from "./api";
import { AccountRecovery, AlertCenter, SettingsPage, WorkspaceNav } from "./PlatformPages";
import "./Platform.css";
import "./App.css";
import "./CareerNovaMission.css";
import "./CareerNovaDiscovery.css";
import "./Responsive.css";
import ApplicationVoiceAssistant from "./ApplicationVoiceAssistant";
import CandidateProfilePage from "./CandidateProfilePage";
import VoiceInput from "./VoiceInput";
import { createContext, useContext, useEffect, useRef, useState } from "react";
import {
  Link,
  Navigate,
  Outlet,
  useLocation,
  NavLink,
  Route,
  Routes,
  useNavigate,
} from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  Bell,
  BriefcaseBusiness,
  ChartNoAxesCombined,
  Bookmark, Trash2, RefreshCw,
  CheckCircle2,
  FileText,
  MapPin,
  Menu,
  Search,
  Sparkles,
  X,
  Zap,
  Bot, Send, SlidersHorizontal, Compass, MessageCircle, Sun, Moon, Orbit, Target, Network, Rocket,
} from "lucide-react";

// Session credentials live only in an HttpOnly cookie; React stores account display state.
const AuthContext = createContext(null);
function useAuth() { return useContext(AuthContext); }
function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  async function refresh() {
    const response = await apiFetch(`${API_URL}/api/auth/me`);
    if (!response.ok) { setUser(null); return; }
    setUser(await response.json());
  }
  useEffect(() => {
    sessionStorage.removeItem("careernova-access-token");
    sessionStorage.removeItem("careernova-account-name");
    refresh().catch(() => setUser(null)).finally(() => setLoading(false));
    const expired = () => setUser(null);
    window.addEventListener("careernova-session-expired", expired);
    return () => window.removeEventListener("careernova-session-expired", expired);
  }, []);
  async function signOut() {
    const response = await apiFetch(`${API_URL}/api/auth/logout`, { method: "POST" });
    if (!response.ok) throw new Error("Could not sign out. Please try again.");
    setUser(null);
  }
  return <AuthContext.Provider value={{ token: !!user, user, loading, accountName: user?.full_name || "", signIn: refresh, signOut }}>{children}</AuthContext.Provider>;
}
function ProtectedWorkspace() {
  const {token, loading} = useAuth();
  const location = useLocation();
  if (loading) return <section className="platform-page" role="status">Loading your workspace...</section>;
  if (!token) return <Navigate to="/login" state={{from: location.pathname}} replace />;
  return <><WorkspaceNav/><Outlet/></>;
}

function AuthPage({ mode }) {
  const navigate = useNavigate();
  const { token, signIn } = useAuth();
  const location = useLocation();
  const registering = mode === "register";
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event) {
    event.preventDefault();
    setError("");
    if (registering && password.length < 12) { setError("Password must be at least 12 characters."); return; }
    setBusy(true);
    try {
      const response = await apiFetch(`${API_URL}/api/auth/${registering ? "register" : "login"}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(registering ? { full_name: fullName.trim(), email: email.trim(), password } : { email: email.trim(), password }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof data.detail === "string" ? data.detail : Array.isArray(data.detail) ? data.detail.map(d => d.msg).join("; ") : `Request failed (HTTP ${response.status})`;
        throw new Error(detail);
      }
      await signIn();
      setPassword("");
      navigate(location.state?.from || "/dashboard");
    } catch (err) { setError(err.message || "Unable to connect to the server."); }
    finally { setBusy(false); }
  }
  if (token) return <section className="section-padding" style={{maxWidth:600,margin:"auto",paddingTop:120,minHeight:"70vh"}}><h1>You are signed in</h1><p>Continue to your candidate profile or explore jobs.</p><Link className="primary-button" to="/profile">My Profile <ArrowRight size={18}/></Link></section>;
  return <section className="section-padding" style={{maxWidth:570,margin:"auto",paddingTop:120,minHeight:"75vh"}}>
    <div className="section-heading"><span className="section-kicker">CAREERNOVA / ACCOUNT</span><h1>{registering ? "Create your account" : "Welcome back"}</h1><p>{registering ? "Register to get started with CareerNova AI." : "Sign in to continue your career journey."}</p></div>
    <ProviderButtons />
    {new URLSearchParams(location.search).get("oauth_error") && <p role="alert">Provider sign-in could not be completed. If you already have an account, sign in with your password and link the provider in Privacy & security.</p>}
    <form onSubmit={submit} className="search-panel cn-search-panel" style={{display:"grid",gap:16,padding:28}}>
      {registering && <label>Full name<input required autoComplete="name" value={fullName} onChange={e=>setFullName(e.target.value)} placeholder="Your full name" style={{display:"block",width:"100%",padding:12,marginTop:6}}/></label>}
      <label>Email<input required type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@example.com" style={{display:"block",width:"100%",padding:12,marginTop:6}}/></label>
      <label>Password<input required type="password" autoComplete={registering ? "new-password" : "current-password"} minLength={registering ? 12 : undefined} value={password} onChange={e=>setPassword(e.target.value)} placeholder={registering ? "At least 12 characters" : "Your password"} style={{display:"block",width:"100%",padding:12,marginTop:6}}/></label>
      {error && <p role="alert" style={{color:"#ff9aa8"}}>{error}</p>}
      <button className="primary-button" type="submit" disabled={busy}>{busy ? "Please wait..." : registering ? "Create Account" : "Login"} <ArrowRight size={18}/></button>
      <p>{registering ? "Already registered?" : "New to CareerNova?"} <Link to={registering ? "/login" : "/register"}>{registering ? "Login" : "Create an account"}</Link></p>
      {!registering && <Link to="/forgot-password">Forgot your password?</Link>}
    </form>
  </section>;
}

const features = [
  {
    icon: Search,
    number: "01",
    title: "AI Job Search",
    description:
      "Find relevant opportunities using semantic search powered by machine learning.",
    path: "/jobs",
  },
  {
    icon: FileText,
    number: "02",
    title: "Resume Matching",
    description:
      "Upload your resume and discover positions aligned with your experience and skills.",
    path: "/resume",
  },
  {
    icon: Bell,
    number: "03",
    title: "Smart Job Alerts",
    description:
      "Get notified when new opportunities match your career preferences.",
    path: "/alerts",
  },
  {
    icon: ChartNoAxesCombined,
    number: "04",
    title: "Career Dashboard",
    description:
      "Explore job trends, matching insights, and your application activity.",
    path: "/dashboard",
  },
];
function ThemeSwitch() {
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem("careernova-theme") || (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"); }
    catch { return "dark"; }
  });
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("careernova-theme", theme); } catch { /* storage disabled */ }
  }, [theme]);
  return <button type="button" className="mission-theme-switch" aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`} title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`} onClick={() => setTheme(t => t === "dark" ? "light" : "dark")}>{theme === "dark" ? <Sun size={19}/> : <Moon size={19}/>}<span>{theme === "dark" ? "Light" : "Dark"}</span></button>;
}
function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { token, accountName, signOut } = useAuth();
  const navigate = useNavigate();
  return (
    <header className="navbar">
      <Link
        className="brand"
        to="/"
        onClick={() => setMenuOpen(false)}
      >
        <span className="brand-icon">
          <Sparkles size={23} />
        </span>
        Career<span className="brand-accent">Nova</span>
        <span className="brand-ai">AI</span>
      </Link>
      <nav id="main-navigation" aria-label="Main navigation" className={menuOpen ? "nav-links open" : "nav-links"} onKeyDown={event => { if (event.key === 'Escape') setMenuOpen(false); }}>
        <NavLink to="/" onClick={() => setMenuOpen(false)}>
          Home
        </NavLink>
        <NavLink to="/features" onClick={() => setMenuOpen(false)}>
          Features
        </NavLink>
        <NavLink to="/jobs" onClick={() => setMenuOpen(false)}>
          Explore Jobs
        </NavLink>
        <NavLink to="/profile" onClick={() => setMenuOpen(false)}>
          My Profile
        </NavLink>
        <Link to="/#how-it-works" onClick={() => setMenuOpen(false)}>
          How It Works
        </Link>
        {token ? <>
          <Link to="/profile" onClick={() => setMenuOpen(false)} title={accountName}>My Account</Link>
          <button type="button" className="nav-cta" onClick={async () => { try { await signOut(); setMenuOpen(false); navigate("/"); } catch (error) { window.alert(error.message); } }}>Logout</button>
        </> : <>
          <NavLink to="/login" onClick={() => setMenuOpen(false)}>Login</NavLink>
          <Link className="nav-cta" to="/register" onClick={() => setMenuOpen(false)}>Sign Up <ArrowUpRight size={16}/></Link>
        </>}
      </nav>
      <ThemeSwitch />
      <button
        className="mobile-menu"
        aria-label="Toggle navigation"
        aria-expanded={menuOpen}
        aria-controls="main-navigation"
        onClick={() => setMenuOpen(!menuOpen)}
      >
        {menuOpen ? <X /> : <Menu />}
      </button>
    </header>
  );
}
function Footer() {
  return (
    <footer className="footer">
      <div className="footer-top">
        <div>
          <Link className="brand" to="/">
            <span className="brand-icon">
              <Sparkles size={21} />
            </span>
            Career<span className="brand-accent">Nova</span>
            <span className="brand-ai">AI</span>
          </Link>
          <p>Smarter discovery. Brighter careers.</p>
        </div>
        <div className="footer-links">
          <Link to="/features">Features</Link>
          <Link to="/jobs">Explore Jobs</Link>
          <Link to="/#how-it-works">How It Works</Link>
        </div>
      </div>
      <div className="footer-bottom">
        <span>
          © {new Date().getFullYear()} CareerNova AI.
          Built for smarter job discovery.
        </span>
        <span>Made with AI <Sparkles size={15} /></span>
      </div>
    </footer>
  );
}
function HomePage() {
  const navigate = useNavigate();
  const { token } = useAuth();
  const [searchTerm, setSearchTerm] = useState("");
  const [jobs, setJobs] = useState([]);
  useEffect(() => {
    if (!token) { setJobs([]); return; }
    let active = true;
    apiFetch(`${API_URL}/api/live-jobs`)
      .then((res) => res.ok ? res.json() : Promise.reject(new Error("Jobs unavailable")))
      .then((data) => { if (active) setJobs(Array.isArray(data.jobs) ? data.jobs : []); })
      .catch(() => {});
    return () => { active = false; };
  }, [token]);
  function searchJobs(event) {
    event.preventDefault();
    navigate(searchTerm.trim() ? `/jobs?q=${encodeURIComponent(searchTerm.trim())}` : "/jobs");
  }
  return (
    <>
      <section className="mission-home" id="home">
        <div className="mission-stars" aria-hidden="true" />
        <div className="mission-main">
          <div className="mission-copy">
            <div className="mission-eyebrow"><span className="mission-status"/> CAREER INTELLIGENCE SYSTEM <span className="mission-version">/ MISSION 01</span></div>
            <h1>Don't just find a job.<br/><em>Navigate your future.</em></h1>
            <p className="mission-description">Your AI career command center. Explore live opportunities, understand your strengths, and launch your next move with confidence.</p>
            <form className="mission-search" onSubmit={searchJobs}>
              <Search size={21} aria-hidden="true" />
              <input aria-label="Search live jobs" placeholder="Search roles, skills, companies..." value={searchTerm} onChange={e => setSearchTerm(e.target.value)}/>
              <button type="submit">Explore <ArrowRight size={18}/></button>
            </form>
            <div className="mission-chips"><span>QUICK LAUNCH</span><Link to="/jobs"><Compass size={15}/> Live Jobs</Link><Link to="/resume"><Target size={15}/> Resume Match</Link><Link to="/profile"><Rocket size={15}/> My Profile</Link></div>
            <div className="mission-trust"><span><span className="mission-status"/> Live opportunities</span><span>AI-powered matching</span><span>Human-approved applications</span></div>
          </div>
          <div className="galaxy-panel" aria-label="Interactive Career Galaxy navigation">
            <div className="galaxy-top"><span><Orbit size={16}/> CAREER GALAXY</span><span className="galaxy-coordinate">EXPLORE YOUR UNIVERSE ↗</span></div>
            <div className="galaxy-space">
              <svg className="galaxy-orbits" viewBox="0 0 500 440" aria-hidden="true"><circle cx="250" cy="220" r="96"/><circle cx="250" cy="220" r="166"/><circle cx="250" cy="220" r="214"/><path d="M250 220L125 105M250 220L390 126M250 220L375 342M250 220L103 330"/></svg>
              <div className="galaxy-core"><span className="galaxy-core-icon"><Sparkles size={32}/></span><strong>YOU</strong><small>Career center</small></div>
              <Link className="galaxy-node galaxy-node-jobs" to="/jobs"><BriefcaseBusiness size={20}/><strong>Discover</strong><small>Live Jobs</small></Link>
              <Link className="galaxy-node galaxy-node-resume" to="/resume"><FileText size={20}/><strong>Analyze</strong><small>Resume Match</small></Link>
              <Link className="galaxy-node galaxy-node-profile" to="/profile"><Target size={20}/><strong>Prepare</strong><small>Candidate Profile</small></Link>
              <Link className="galaxy-node galaxy-node-dashboard" to="/dashboard"><ChartNoAxesCombined size={20}/><strong>Grow</strong><small>Dashboard</small></Link>
              <span className="galaxy-star galaxy-star-one"/><span className="galaxy-star galaxy-star-two"/><span className="galaxy-star galaxy-star-three"/>
            </div>
            <div className="galaxy-bottom"><span><span className="mission-status"/> SYSTEM ONLINE</span><span>SELECT A PLANET TO BEGIN</span></div>
          </div>
        </div>
        <div className="mission-launchpad"><Link to="/jobs"><span className="launch-icon"><Compass size={22}/></span><span><strong>Explore opportunities</strong><small>One unified live job feed</small></span><ArrowUpRight size={19}/></Link><Link to="/resume"><span className="launch-icon"><Network size={22}/></span><span><strong>Decode your strengths</strong><small>Match your resume with roles</small></span><ArrowUpRight size={19}/></Link><Link to="/profile"><span className="launch-icon"><Bot size={22}/></span><span><strong>Prepare with Nova</strong><small>Build your candidate profile</small></span><ArrowUpRight size={19}/></Link></div>
      </section>
      <section className="nova-discover section-padding cn-discover">
        <div className="nova-discover-heading"><div><span className="section-kicker">DISCOVER OPPORTUNITIES</span><h2>Fresh opportunities, one place</h2><p>Explore live remote postings from our connected job source.</p></div><Link to="/jobs" className="secondary-button">View all jobs <ArrowRight size={17}/></Link></div>
        <div className="nova-job-grid cn-preview-grid">
          {jobs.length ? jobs.slice(0,3).map((job, index) => (
            <Link to="/jobs" className="nova-job-card cn-preview-card" key={job.id || index}>
              <div className="nova-job-symbol"><BriefcaseBusiness size={22}/></div>
              <h3>{job.title || "Job opportunity"}</h3><p>{job.company || "Company not listed"}</p>
              <span><MapPin size={14}/>{job.location || "Location not listed"}</span>
              <div className="nova-job-card-bottom">View opportunity <ArrowUpRight size={17}/></div>
            </Link>
          )) : <div className="nova-no-jobs">{token ? "No opportunities to preview yet. Check the latest listings in your workspace." : "Your next opportunity is waiting. Create a free account to explore jobs and find your match."} <Link to={token ? "/jobs" : "/register"}>{token ? "Explore Jobs" : "Get started"} <ArrowRight size={14}/></Link></div>}
        </div>
      </section>
      <section className="trust-strip">
        <span>BUILT WITH MODERN AI TECHNOLOGY</span>
        <div className="tech-list">
          <span>React</span>
          <span>Python</span>
          <span>FAISS</span>
          <span>Sentence Transformers</span>
          <span>Machine Learning</span>
        </div>
      </section>
      <section className="features-section section-padding" id="features">
        <div className="section-heading">
          <span className="section-kicker">WHY CAREERNOVA</span>
          <h2>
            Everything you need to{" "}
            <span className="gradient-text">move forward.</span>
          </h2>
          <p>
            One intelligent platform designed to make job discovery
            simpler, faster, and more relevant.
          </p>
        </div>
        <div className="features-grid">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <Link
                className="feature-card"
                to={feature.path}
                key={feature.number}
                style={{ textDecoration: "none", color: "inherit" }}
              >
                <div className="feature-top">
                  <span className="feature-icon">
                    <Icon size={25} />
                  </span>
                  <span className="feature-number">
                    {feature.number}
                  </span>
                </div>
                <h3>{feature.title}</h3>
                <p>{feature.description}</p>
                <div className="feature-bottom">
                  <span>
                    {feature.upcoming
                      ? "Coming soon"
                      : "Explore feature"}
                  </span>
                  <ArrowUpRight size={18} />
                </div>
              </Link>
            );
          })}
        </div>
      </section>
      <section className="steps-section section-padding" id="how-it-works">
        <div className="section-heading">
          <span className="section-kicker">SIMPLE BY DESIGN</span>
          <h2>
            Three steps to your{" "}
            <span className="gradient-text">next opportunity.</span>
          </h2>
        </div>
        <div className="steps-grid">
          <div className="step">
            <span>01</span>
            <FileText size={28} />
            <h3>Upload your resume</h3>
            <p>Share your skills, qualifications, and experience.</p>
          </div>
          <div className="step">
            <span>02</span>
            <Sparkles size={28} />
            <h3>Let AI find matches</h3>
            <p>Our semantic search compares your profile with jobs.</p>
          </div>
          <div className="step">
            <span>03</span>
            <BriefcaseBusiness size={28} />
            <h3>Explore and apply</h3>
            <p>Review opportunities and visit application pages.</p>
          </div>
        </div>
      </section>
      <section className="final-cta section-padding">
        <div className="cta-panel">
          <div className="eyebrow">
            <Sparkles size={15} /> YOUR FUTURE STARTS HERE
          </div>
          <h2>
            Don't just search for a job.
            <br />
            <span className="gradient-text">
              Discover your potential.
            </span>
          </h2>
          <p>
            Let intelligent matching bring your next career
            opportunity into focus.
          </p>
          <button
            className="primary-button"
            onClick={() => navigate("/jobs")}
          >
            Start Exploring <ArrowRight size={19} />
          </button>
        </div>
      </section>
    </>
  );
}

async function dashboardRequest(path, options = {}) {
  const response = await apiFetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : `Request failed (HTTP ${response.status})`);
  }
  return data;
}
function SaveJobButton({ job }) {
  const [tracked,setTracked] = useState(null);
  const trackedStatus = tracked?.status || job.tracked_status;
  const trackerId = tracked?.id || job.tracker_id;
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function save() {
    setBusy(true);
    setMessage("");
    try {
      const result = await dashboardRequest("/api/dashboard/save", {
        method: "POST",
        body: JSON.stringify({
          job_id: String(job.id ?? ""),
          job_title: job.title || "Untitled position",
          company: job.company || "Unknown company",
          location: job.location || "Not specified",
          apply_url: job.apply_url || job.url || null,
          match_percentage: job.match_percentage == null ? null : Number(job.match_percentage),
        }),
      });
      setTracked(result);
      setMessage(result.message);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div style={{ marginTop: 12 }}>
      <JobTrustActions job={job} />
      {trackedStatus && <p className="job-tracking-badge">Already tracked · {trackedStatus}</p>}
      <button type="button" className="secondary-button" disabled={busy || !!trackedStatus} onClick={save}>
        <Bookmark size={16} /> {busy ? "Saving..." : trackedStatus ? "In your board" : "Save Job"}
      </button>
      {trackerId && <Link className="timeline-link" to={`/timeline?application=${trackerId}`}>View application activity →</Link>}
      {message && <p role="status" style={{ fontSize: 13 }}>{message}</p>}
    </div>
  );
}

function FeaturesPage() {
  const extraFeatures = [
    ...features,
    { icon: BriefcaseBusiness, number: "05", title: "AI Application Assistant",
      description: "Autofill supported job application fields, then review before submitting.", path: "/jobs" },
    { icon: CheckCircle2, number: "06", title: "Candidate Profile",
      description: "Manage the information used to suggest answers on application forms.", path: "/profile" },
  ];
  return (
    <section className="features-page section-padding">
      <div className="section-heading">
        <span className="section-kicker">EXPLORE THE PLATFORM</span>
        <h2>Tools for every step of <span className="gradient-text">your career journey.</span></h2>
        <p>Choose a feature below to open the working tool. Your existing profile, saved jobs, and application assistant remain available.</p>
      </div>
      <div className="features-grid">
        {extraFeatures.map((feature) => {
          const Icon = feature.icon;
          return (
            <Link className="feature-card" to={feature.path} key={feature.number}>
              <div className="feature-top"><span className="feature-icon"><Icon size={25}/></span><span className="feature-number">{feature.number}</span></div>
              <h3>{feature.title}</h3><p>{feature.description}</p>
              <div className="feature-bottom"><span>Open feature</span><ArrowUpRight size={18}/></div>
            </Link>
          );
        })}
      </div>
      <div className="features-page-cta">
        <h3>Ready to discover opportunities?</h3>
        <p>Browse recommended roles, or use AI search for a specific position.</p>
        <Link to="/jobs" className="primary-button">Explore Jobs <ArrowRight size={18}/></Link>
      </div>
    </section>
  );
}

function JobsPage() {
  const navigate = useNavigate();
  const searchPageLocation = useLocation();
  const savedSearchId = new URLSearchParams(searchPageLocation.search).get("saved_search");
  const [query, setQuery] = useState(() => new URLSearchParams(window.location.search).get("q") || "");
  const [searchTerm, setSearchTerm] = useState(() => new URLSearchParams(window.location.search).get("q") || "");
  const [jobs, setJobs] = useState([]);
  const [jobSource, setJobSource] = useState(import.meta.env.VITE_DEFAULT_JOB_SOURCE === "live" ? "live" : "historical");
  const [total, setTotal] = useState(0);
  const [availableTotal, setAvailableTotal] = useState(0);
  const [sources, setSources] = useState({});
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const advancedDefaults = {company:'',skills:'',exclude:'',seniority:'',posted_days:0,sort:'relevance'};
  const [advanced, setAdvanced] = useState(advancedDefaults);
  function updateAdvanced(patch) {
    const next = {...advanced, ...patch};
    setAdvanced(next);
    loadJobs({advancedFilters: next});
  }
  const [employmentType, setEmploymentType] = useState("");
  const [workArrangement, setWorkArrangement] = useState("");
  const [location, setLocation] = useState("");
  const [role, setRole] = useState("");
  const [selectedJob, setSelectedJob] = useState(null);
  const [assistantJob, setAssistantJob] = useState(null);
  const [profileMode, setProfileMode] = useState(false);
  const [voiceActive, setVoiceActive] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState("Press Start Nova, then say 'Hey Nova'.");
  const [voiceConversation, setVoiceConversation] = useState([]);
  const recognitionRef = useRef(null);
  const voiceActiveRef = useRef(false);
  const listeningRef = useRef(false);
  const speakingRef = useRef(false);
  const jobsRef = useRef([]);
  const selectedJobRef = useRef(null);
  const searchRef = useRef(null);
  const resultsRef = useRef(null);
  const voiceSearchRef = useRef(false);
  const voiceHandlerRef = useRef(null);
  const novaAwakeRef = useRef(false);
  const speechUtteranceRef = useRef(null);
  const speechGenerationRef = useRef(0);
  const restartTimerRef = useRef(null);
  const recognitionStartingRef = useRef(false);
  const recognitionReadyRef = useRef(false);

  const [manualNovaCommand, setManualNovaCommand] = useState("");
  const latestRequest = useRef(0);
  const limit = 24;
  const employmentOptions = ["", "full-time", "part-time", "internship", "contract", "temporary", "research"];
  const roleOptions = ["", "Data Analyst", "Data Engineer", "Data Scientist", "Software Engineer", "AI Engineer", "Research", "Business Analyst", "Healthcare", "Marketing", "Finance"];

  function normalizeJob(job) {
    const place = String(job.location || "Not specified");
    const statedMode = String(job.work_mode || "");
    const mode = statedMode || (/hybrid/i.test(place) ? "Hybrid" : /remote|worldwide/i.test(place) ? "Remote" : /on.site|onsite|office/i.test(place) ? "On-site" : "Not specified");
    const url = job.apply_url || job.url || "";
    return {
      ...job,
      id: String(job.id || url || ""),
      apply_url: url,
      source_slug: job.source_slug || job.source || "Dataset",
      work_mode: mode,
      description: job.description || job.job_description || "",
      listing_status: job.listing_status || "historical_unverified",
    };
  }

  async function loadJobs({ requestedPage = 1, append = false, refresh = false, term = searchTerm, type = employmentType, mode = workArrangement, city = location, field = role, source = jobSource, advancedFilters = advanced } = {}) {
    const requestId = ++latestRequest.current;
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ page: String(requestedPage), limit: String(limit) });
      const combined = [term, field].map(s => String(s || "").trim()).filter(Boolean).join(" ");
      Object.entries(advancedFilters).forEach(([key,value]) => { if(value) params.set(key,String(value)); });
      if (combined) params.set("query", combined);
      if (type) params.set("employment_type", type);
      if (mode) params.set(source === "historical" ? "work_mode" : "work_arrangement", mode);
      if (city.trim()) params.set("location", city.trim());
      if (refresh && source === "live") params.set("refresh", "true");
      const endpoint = source === "historical" ? "/api/historical-jobs" : "/api/jobs/discover";
      const response = await apiFetch(`${API_URL}${endpoint}?${params}`);
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : `Job search failed (HTTP ${response.status}). Check the backend.`);
      if (requestId !== latestRequest.current) return;
      const incoming = (Array.isArray(data.jobs) ? data.jobs : []).map(normalizeJob);
      setJobs(previous => append ? [...previous, ...incoming] : incoming);
      setTotal(Number(data.total || 0));
      setAvailableTotal(source === "historical" ? Number(data.available_total ?? data.total ?? 0) : Number(data.available_total || 0));
      setSources(source === "historical" ? { Dataset: true } : (data.sources || {}));
      setPage(requestedPage);
      setProfileMode(false);
      if (voiceSearchRef.current && !append) {
        voiceSearchRef.current = false;
        window.requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
        const count = Number(data.total || 0);
        if (count === 0) say("I couldn't find matching jobs. Try a different job title or employment type.");
        else {
          const examples = incoming.slice(0, 3).map((job, i) => `Number ${i + 1}, ${job.title} at ${job.company}`).join(". ");
          say(`I found ${count} ${source === "historical" ? "stored job records" : "live job matches"}. ${examples}. Which job would you like to explore?`);
        }
      }
    } catch (err) {
      if (requestId === latestRequest.current) {
        setError(err.message || "Could not load jobs.");
        if (voiceSearchRef.current) { voiceSearchRef.current = false; say("The job search failed. Please check your backend connection."); }
      }
    } finally {
      if (requestId === latestRequest.current) setLoading(false);
    }
  }

  function changeJobSource(nextSource) {
    if (nextSource === jobSource) return;
    setJobSource(nextSource);
    setJobs([]);
    setTotal(0);
    setPage(1);
    loadJobs({ source: nextSource, requestedPage: 1 });
  }

  function applySavedFilters(filters) {
    setJobSource(filters.source);setQuery(filters.term);setSearchTerm(filters.term);
    setEmploymentType(filters.type);setWorkArrangement(filters.mode);setLocation(filters.city);setRole(filters.field);
    const restored = Object.fromEntries(Object.keys(advancedDefaults).map(key => [key, filters[key] ?? advancedDefaults[key]]));
    setAdvanced(restored);
    loadJobs({...filters,advancedFilters:restored,requestedPage:1});
  }
  useEffect(() => {
    let active=true;
    if(savedSearchId){
      setLoading(true);setError("");
      request(`/api/saved-searches/${encodeURIComponent(savedSearchId)}`)
        .then(saved=>{if(active)applySavedFilters(saved.filters);})
        .catch(error=>{if(active){setError(error.message);setLoading(false);}});
    }else loadJobs();
    return()=>{active=false;};
  }, [savedSearchId]);
  useEffect(() => { jobsRef.current = jobs; }, [jobs]);
  useEffect(() => { selectedJobRef.current = selectedJob; }, [selectedJob]);
  useEffect(() => { searchRef.current = loadJobs; });

  function updateFilters(patch) {
    const next = { term: searchTerm, type: employmentType, mode: workArrangement, city: location, field: role, ...patch };
    if ("term" in patch) { setSearchTerm(next.term); setQuery(next.term); }
    if ("type" in patch) setEmploymentType(next.type);
    if ("mode" in patch) setWorkArrangement(next.mode);
    if ("city" in patch) setLocation(next.city);
    if ("field" in patch) setRole(next.field);
    loadJobs(next);
  }

  async function personalizeJobs() {
    setLoading(true);
    setError("");
    try {
      const response = await apiFetch(`${API_URL}/api/profile/me`);
      if (!response.ok) throw new Error("Save your Candidate Profile before matching jobs.");
      const profile = await response.json();
      const skills = String(profile.skills || "").toLowerCase().split(/[,;\n]+/).map(x => x.trim()).filter(x => x.length > 2);
      if (!skills.length) throw new Error("Add skills to your Candidate Profile first.");
      const responseJobs = await apiFetch(`${API_URL}/api/live-jobs`);
      if (!responseJobs.ok) throw new Error("Live jobs are unavailable.");
      const data = await responseJobs.json();
      const matches = (data.jobs || []).map(normalizeJob).filter(job => skills.some(skill => `${job.title} ${job.description}`.toLowerCase().includes(skill)));
      setJobs(matches.slice(0, 100));
      setTotal(matches.length);
      setAvailableTotal(Number(data.total || 0));
      setPage(1);
      setProfileMode(true);
      setJobSource("live");
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  // Stop the microphone before speaking so Nova does not transcribe its own voice.
  function say(text) {
    const message = String(text || "").trim();
    if (!message) return;
    setVoiceStatus(message);
    setVoiceConversation(previous => [...previous.slice(-7), { who: "Nova", text: message }]);
    if (!("speechSynthesis" in window)) {
      setVoiceStatus(`${message} (Audio output is not supported by this browser.)`);
      return;
    }

    const generation = ++speechGenerationRef.current;
    speakingRef.current = true;
    if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
    try { recognitionRef.current?.abort(); } catch { /* already stopped */ }
    try { window.speechSynthesis.cancel(); } catch { /* ignore */ }

    const utterance = new SpeechSynthesisUtterance(message);
    speechUtteranceRef.current = utterance; // Keep the utterance alive in Chrome.
    utterance.lang = "en-US";
    utterance.rate = 0.97;
    utterance.pitch = 1;
    utterance.volume = 1;
    const voices = window.speechSynthesis.getVoices();
    utterance.voice = voices.find(v => v.lang?.toLowerCase().startsWith("en") && /google|microsoft/i.test(v.name))
      || voices.find(v => v.lang?.toLowerCase().startsWith("en")) || null;

    const finish = () => {
      if (generation !== speechGenerationRef.current) return;
      speakingRef.current = false;
      speechUtteranceRef.current = null;
      if (voiceActiveRef.current) scheduleListening(500);
    };
    utterance.onend = finish;
    utterance.onerror = (event) => {
      if (event.error !== "canceled" && event.error !== "interrupted") {
        setVoiceStatus(`Speech playback failed (${event.error}). ${message}`);
      }
      finish();
    };
    // Some Chromium versions need a brief delay after stopping recognition.
    setTimeout(() => {
      if (generation !== speechGenerationRef.current) return;
      try { window.speechSynthesis.speak(utterance); }
      catch { finish(); }
    }, 120);
  }

  function scheduleListening(delay = 350) {
    if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
    restartTimerRef.current = setTimeout(() => restartListening(), delay);
  }

  function restartListening() {
    if (!voiceActiveRef.current || speakingRef.current || listeningRef.current || recognitionStartingRef.current) return;
    const recognition = recognitionRef.current;
    if (!recognition) return;
    recognitionStartingRef.current = true;
    try { recognition.start(); }
    catch {
      recognitionStartingRef.current = false;
      if (voiceActiveRef.current && !speakingRef.current) scheduleListening(850);
    }
  }

  // Check reusable candidate details before opening a third-party application.
  async function beginNovaApplication(job) {
    if (!job) { say("Please choose a job first."); return; }
    selectedJobRef.current = job;
    setSelectedJob(job);
    if (!/^https?:\/\//i.test(job.apply_url || job.url || "")) {
      say("This posting has no valid application link. Please select another job."); return;
    }
    say(`You selected ${job.title} at ${job.company}. I will check your candidate profile before applying.`);
    try {
      let response = await apiFetch(`${API_URL}/api/profile/me`);
      if (!response.ok) throw new Error("Profile service unavailable");
      const profile = await response.json();
      const required = [
        ["first name", profile.first_name || profile.full_name?.trim().split(/\s+/)[0]],
        ["last name", profile.last_name || (profile.full_name?.trim().split(/\s+/).slice(1).join(" "))],
        ["email", profile.email],
        ["phone", profile.phone],
        ["location", profile.location],
      ];
      const missing = required.filter(([, value]) => !String(value || "").trim()).map(([label]) => label);
      if (missing.length) {
        sessionStorage.setItem("careernova-pending-application", JSON.stringify(job));
        say(`Before applying, please fill in your Candidate Profile. Missing details: ${missing.join(", ")}. I am opening your profile now. Save it, then return to Explore Jobs and say continue application.`);
        // Delay navigation so Nova can speak the instructions before unmounting.
        setTimeout(() => navigate("/profile"), 6500);
        return;
      }
      sessionStorage.removeItem("careernova-pending-application");
      setAssistantJob(job);
      setSelectedJob(null);
      say("Your essential profile details are saved. Opening the application assistant now. I will reuse your saved details where supported, ask for missing answers, and let you review before submitting.");
    } catch {
      say("I could not check your Candidate Profile. Please check the backend and your profile before starting an application.");
    }
  }

  function handleNovaCommand(transcript) {
    const text = transcript.trim();
    let command = text.toLowerCase().replace(/[.!?]/g, "").trim();
    setVoiceConversation(previous => [...previous.slice(-7), { who: "You", text }]);
    if (/^(stop nova|goodbye nova|nova stop|stop listening)$/.test(command)) { stopNova(); return; }
    const greeted = /^(?:(?:hey|hi|hello|okay|ok)\s+)?(?:nova|noah|novah)\b/.test(command);
    if (greeted) {
      novaAwakeRef.current = true;
      command = command.replace(/^(?:(?:hey|hi|hello|okay|ok)\s+)?(?:nova|noah|novah)[ ,]*/, "").trim();
      if (!command) { say("Hi! What can I help you with today?"); return; }
    }
    if (!novaAwakeRef.current) { setVoiceStatus("Say Hey Nova to wake me up."); return; }
    if (/^(help|what can you do|show commands)$/.test(command)) {
      say("I can find and filter live jobs, read the top results, match your profile, save a selected job, open your dashboard and resume matching, and help start applications. What would you like to do?");
      return;
    }
    if (/^(show|open|go to|navigate to) (my |the )?(dashboard|saved jobs)$/.test(command)) {
      say("Opening your career dashboard."); navigate("/dashboard"); return;
    }
    if (/^(show|open|go to|navigate to) (my |the )?(profile|candidate profile)$/.test(command)) {
      say("Opening your candidate profile."); navigate("/profile"); return;
    }
    if (/^(show|open|go to|navigate to) (my |the )?(resume|resume matching|resume match)$/.test(command)) {
      say("Opening resume matching."); navigate("/resume"); return;
    }
    if (/^(go home|open home|home page)$/.test(command)) {
      say("Opening CareerNova home."); navigate("/"); return;
    }
    if (/^(match my profile|find jobs for my profile|personalize jobs)$/.test(command)) {
      say("Matching your saved skills against the live job feed."); personalizeJobs(); return;
    }
    if (/^(read|list|tell me|show) (the )?(first|top|next)?\s*(three|3)?\s*(jobs|results|suggestions)$/.test(command)) {
      if (!jobsRef.current.length) { say("No jobs are displayed. Ask me to find a role first."); return; }
      say(jobsRef.current.slice(0, 3).map((job,i)=>`Job ${i+1}: ${job.title} at ${job.company}`).join(". ") + ". Which one interests you?");
      return;
    }
    const detailsMatch = command.match(/^(?:tell me about|details (?:for|of)|describe|what about) (?:the )?(first|second|third|[1-3])(?: job| one)?$/);
    if (detailsMatch) {
      const positions = { first: 0, second: 1, third: 2, "1": 0, "2": 1, "3": 2 };
      const chosen = jobsRef.current[positions[detailsMatch[1]]];
      if (!chosen) { say("That job is not in the current results. Search for jobs first."); return; }
      selectedJobRef.current = chosen;
      setSelectedJob(chosen);
      const summary = String(chosen.description || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 380);
      say(`${chosen.title} at ${chosen.company}. Location: ${chosen.location || "not specified"}. ${summary || "Open the job posting for the full description."} Say start application when you're ready.`);
      return;
    }
    if (/^(save|bookmark) (this|the|selected|current) job$/.test(command)) {
      const job = selectedJobRef.current;
      if (!job) { say("Select a job first, for example, apply for the first job."); return; }
      dashboardRequest("/api/dashboard/save", {method:"POST",body: JSON.stringify({user_id:DASHBOARD_USER,job_id:String(job.id),job_title:job.title,company:job.company,location:job.location,apply_url:job.apply_url || null,match_percentage:null})})
        .then(()=>say(`Saved ${job.title} to your dashboard.`))
        .catch(()=>say("I could not save that job. Check your backend connection."));
      return;
    }
    if (/^(cancel|close|never mind|never mind nova)$/.test(command)) { setSelectedJob(null); selectedJobRef.current=null; say("Okay, I closed the job selection."); return; }

    if (/^(start application|launch assistant|continue application|yes start application|apply now)$/.test(command)) {
      const pending = sessionStorage.getItem("careernova-pending-application");
      let chosen = selectedJobRef.current;
      if (!chosen && pending) { try { chosen = JSON.parse(pending); } catch { /* invalid stored job */ } }
      beginNovaApplication(chosen);
      return;
    }
    if (/refresh (?:the )?jobs/.test(command)) {
      voiceSearchRef.current = true;
      searchRef.current?.({ refresh: true });
      setVoiceStatus("Refreshing job listings...");
      return;
    }
    // Only treat an explicit job number, ordinal, or selected job title as an application choice.
    // "I want to apply for full-time data analyst jobs" is a SEARCH, not a selection.
    const selection = command.match(/(?:apply (?:for|to)|select|choose|open)\s+(?:the\s+)?(.+)/);
    const selectionTarget = selection?.[1]?.replace(/\s+(?:job|position)$/i, "").trim() || "";
    const ordinals = { first: 1, second: 2, third: 3, fourth: 4, fifth: 5, sixth: 6, seventh: 7, eighth: 8, ninth: 9, tenth: 10 };
    const ordinal = Object.entries(ordinals).find(([word]) => new RegExp(`\\b${word}\\b`).test(selectionTarget));
    const number = selectionTarget.match(/(?:number|job)\s*(\d+)/) || selectionTarget.match(/^(\d+)$/);
    const isGeneralSearch = /\b(jobs|internships|positions|opportunities)\b/.test(selectionTarget);
    if (selection && (ordinal || number || (!isGeneralSearch && selectionTarget.length >= 3 && jobsRef.current.some(job => job.title.toLowerCase().includes(selectionTarget))))) {
      const index = ordinal ? ordinal[1] - 1 : number ? Number(number[1]) - 1 : -1;
      const found = index >= 0 ? jobsRef.current[index] : jobsRef.current.find(job => job.title.toLowerCase().includes(selectionTarget));
      if (!found) { say("That job is not among the currently displayed results. Try another job number."); return; }
      selectedJobRef.current = found;
      setSelectedJob(found);
      if (/\bapply\b/.test(command)) beginNovaApplication(found);
      else say(`You selected ${found.title} at ${found.company}. Say start application when ready.`);
      return;
    }
    if (/\b(open youtube|open chrome|shutdown|delete files|send email|send message|whatsapp|play music|weather|turn off computer)\b/.test(command)) {
      say("That action isn't connected to CareerNova yet. I can operate job search, profile navigation, saved jobs, and supported applications.");
      return;
    }
    let cleaned = command
      .replace(/^(?:i want to|i would like to|can you|could you|please|i am looking for|i'm looking for)\s+/i, "")
      .replace(/^(?:apply for|find me|find|search for|search|show me|look for|looking for)\s+/i, "")
      .replace(/^(?:a|an|the)\s+/i, "")
      .replace(/\b(jobs|job openings|positions|opportunities)\s*$/i, "")
      .trim();
    let type = "";
    if (/\b(full[ -]?time)\b/i.test(cleaned)) type = "full-time";
    else if (/\b(part[ -]?time)\b/i.test(cleaned)) type = "part-time";
    else if (/\b(internships?|interns?)\b/i.test(cleaned)) type = "internship";
    else if (/\b(contract|contractor)\b/i.test(cleaned)) type = "contract";
    else if (/\btemporary\b/i.test(cleaned)) type = "temporary";
    cleaned = cleaned.replace(/\b(full[ -]?time|part[ -]?time|internships?|interns?|contractor?|temporary)\b/gi, " ").replace(/\s+/g, " ").trim();
    let mode = "";
    if (/\bremote\b/i.test(cleaned)) mode = "remote";
    else if (/\bhybrid\b/i.test(cleaned)) mode = "hybrid";
    else if (/\b(on[ -]?site|in office)\b/i.test(cleaned)) mode = "on-site";
    cleaned = cleaned.replace(/\b(remote|hybrid|on[ -]?site|in office)\b/gi, " ").replace(/\s+/g, " ").trim();
    if (!cleaned && !type && !mode) { say("Tell me which jobs you'd like to find."); return; }
    setQuery(cleaned);
    setSearchTerm(cleaned);
    setEmploymentType(type);
    setWorkArrangement(mode);
    setRole("");
    setLocation("");
    voiceSearchRef.current = true;
    setVoiceStatus(`Searching for ${[type, mode, cleaned].filter(Boolean).join(" ")} jobs...`);
    searchRef.current?.({ term: cleaned, type, mode, city: "", field: "", requestedPage: 1 });
  }
  voiceHandlerRef.current = handleNovaCommand;

  function startNova() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) { setVoiceStatus("Speech recognition is not supported here. Try the latest Chrome or Edge on localhost."); return; }
    // Starting is a user gesture: prime the voice engine and request microphone permission.
    try { window.speechSynthesis.getVoices(); window.speechSynthesis.resume(); } catch { /* ignore */ }
    const recognition = new Recognition();
    recognition.lang = "en-US";
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.maxAlternatives = 3;
    recognition.onstart = () => {
      recognitionStartingRef.current = false;
      listeningRef.current = true;
      recognitionReadyRef.current = true;
      setVoiceStatus("Listening... say Hey Nova.");
    };
    recognition.onend = () => {
      listeningRef.current = false;
      recognitionStartingRef.current = false;
      if (voiceActiveRef.current && !speakingRef.current) scheduleListening(600);
    };
    recognition.onerror = event => {
      recognitionStartingRef.current = false;
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        voiceActiveRef.current = false;
        setVoiceActive(false);
        setVoiceStatus("Microphone permission denied. Click the site controls beside localhost:5173 and allow microphone access.");
      } else if (event.error === "network") {
        setVoiceStatus("Speech recognition network service is unavailable. You can still type Nova commands.");
        voiceActiveRef.current = false;
        setVoiceActive(false);
      }
    };
    recognition.onresult = event => {
      if (speakingRef.current) return;
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (!event.results[i].isFinal) continue;
        const alternatives = Array.from(event.results[i]).map(item => item.transcript.trim()).filter(Boolean);
        const transcript = alternatives.find(item => /\b(?:nova|noah|novah)\b/i.test(item)) || alternatives[0];
        if (transcript) voiceHandlerRef.current?.(transcript);
      }
    };
    recognitionRef.current = recognition;
    voiceActiveRef.current = true;
    novaAwakeRef.current = false;
    setVoiceActive(true);
    restartListening();
  }
  function stopNova() {
    voiceActiveRef.current = false;
    novaAwakeRef.current = false;
    setVoiceActive(false);
    if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
    ++speechGenerationRef.current;
    try { recognitionRef.current?.abort(); } catch { /* ignore */ }
    try { window.speechSynthesis?.cancel(); } catch { /* ignore */ }
    listeningRef.current = false;
    recognitionStartingRef.current = false;
    speakingRef.current = false;
    speechUtteranceRef.current = null;
    setVoiceStatus("Nova stopped. Press Start Nova to activate again.");
  }
  useEffect(() => () => { voiceActiveRef.current = false; if (restartTimerRef.current) clearTimeout(restartTimerRef.current); ++speechGenerationRef.current; try { recognitionRef.current?.abort(); } catch {} try { window.speechSynthesis?.cancel(); } catch {} }, []);

  return (
    <section className="jobs-section section-padding cn-jobs cn-discovery">
      <div className="cn-discovery-hero">
        <div><span className="section-kicker">CAREERNOVA / JOB DISCOVERY</span>
          <h1>Find your next <span className="gradient-text">opportunity.</span></h1>
          <p>Search 99,999 stored job records or switch to connected live feeds. Review employer listings before applying.</p>
          <div className="cn-discovery-metrics"><span><strong>{availableTotal.toLocaleString()}</strong> {jobSource === "historical" ? "stored records" : "jobs indexed"}</span><span><strong>{Object.keys(sources).length}</strong> {jobSource === "historical" ? "dataset" : "connected feeds"}</span><span><strong>{total.toLocaleString()}</strong> matches</span></div>
        </div>
        <div className="cn-nova-panel">
          <div className="cn-nova-title"><Bot size={24}/> <div><strong>Hey Nova</strong><small>Hands-free career assistant</small></div><span className={voiceActive ? "cn-nova-indicator active" : "cn-nova-indicator"}/></div>
          <p className="cn-nova-voice-status" role="status">{voiceStatus}</p>
          <div className="cn-nova-actions"><button type="button" className="primary-button" onClick={voiceActive ? stopNova : startNova}>{voiceActive ? "Stop Nova" : "Start Nova"}</button></div>
          <small>Say “Hey Nova” to activate. Try “Find data analyst internships”, “Read the top jobs”, “Apply for the first job”, “Save this job”, or “Open dashboard”.</small>
          <form onSubmit={event => { event.preventDefault(); if (!manualNovaCommand.trim()) return; novaAwakeRef.current = true; voiceHandlerRef.current?.(manualNovaCommand); setManualNovaCommand(""); }} style={{display:"flex",gap:8,marginTop:12}}>
            <input aria-label="Type a command for Nova" placeholder="Type a Nova command to test" value={manualNovaCommand} onChange={event=>setManualNovaCommand(event.target.value)} style={{minWidth:0,flex:1,padding:10,borderRadius:10,background:"#151428",color:"white",border:"1px solid #554b70"}} />
            <button className="secondary-button" type="submit">Send</button>
          </form>
          {voiceConversation.length > 0 && <div className="cn-nova-transcript" aria-live="polite">{voiceConversation.slice(-4).map((line, index) => <p key={index}><strong>{line.who}:</strong> {line.text}</p>)}</div>}
        </div>
      </div>
      <div role="group" aria-label="Job source" style={{display:"flex",gap:10,flexWrap:"wrap",margin:"18px 0"}}>
        <button type="button" className={jobSource === "historical" ? "primary-button" : "secondary-button"} aria-pressed={jobSource === "historical"} onClick={() => changeJobSource("historical")}>99,999 Dataset Jobs</button>
        <button type="button" className={jobSource === "live" ? "primary-button" : "secondary-button"} aria-pressed={jobSource === "live"} onClick={() => changeJobSource("live")}>Live Jobs</button>
      </div>
      {jobSource === "historical" && <p style={{marginBottom:16,opacity:0.8}}>Dataset records are historical and have not been checked for current availability. Always verify the posting on the employer website.</p>}
      <form className="cn-discovery-search" onSubmit={event => { event.preventDefault(); updateFilters({ term: query }); }}>
        <Search size={20}/><input aria-label="Search job title, skills or company" placeholder="Job title, skills, or company" value={query} onChange={event => setQuery(event.target.value)}/>
        <button type="submit" className="primary-button">Search Jobs <ArrowRight size={17}/></button>
      </form>
      <div className="cn-discovery-toolbar"><div><strong>{jobSource === "historical" ? "Stored job dataset" : "Live opportunities"}</strong><p>Use the filters to narrow the results.</p></div><div className="cn-discovery-actions">
        <button type="button" className="secondary-button" disabled={loading} onClick={() => loadJobs({ refresh: true })}><RefreshCw size={17}/> {jobSource === "historical" ? "Reload records" : "Refresh jobs"}</button>
        <button type="button" className="secondary-button" disabled={loading} onClick={personalizeJobs}><Sparkles size={17}/> Match my profile</button>
      </div></div>
      <div className="cn-discovery-filters">
        <label>Employment type<select value={employmentType} onChange={event => updateFilters({ type: event.target.value })}>{employmentOptions.map(type => <option key={type} value={type}>{type ? type.charAt(0).toUpperCase() + type.slice(1) : "All employment types"}</option>)}</select></label>
        <label>Work arrangement<select value={workArrangement} onChange={event => updateFilters({ mode: event.target.value })}><option value="">Any arrangement</option><option value="remote">Remote</option><option value="hybrid">Hybrid</option><option value="on-site">On-site</option></select></label>
        <label>Career field<select value={role} onChange={event => updateFilters({ field: event.target.value })}>{roleOptions.map(field => <option key={field} value={field}>{field || "All career fields"}</option>)}</select></label>
        <label>Location<input value={location} placeholder="e.g. Houston" onChange={event => setLocation(event.target.value)} onKeyDown={event => { if (event.key === "Enter") { event.preventDefault(); updateFilters({ city: location }); } }}/></label>
        <button type="button" className="secondary-button" onClick={() => { setAdvanced(advancedDefaults); updateFilters({ term: "", type: "", mode: "", field: "", city: "", advancedFilters:advancedDefaults }); }}>Clear filters</button>
      </div>
      <details className="cn-advanced-filters" open>
        <summary>More filters & sorting</summary>
        <div className="cn-discovery-filters">
          <label>Company<input maxLength={200} value={advanced.company} placeholder="Company name" onChange={e=>setAdvanced({...advanced,company:e.target.value})}/></label>
          <label>Required keywords<input maxLength={500} value={advanced.skills} placeholder="Python, SQL (all required)" onChange={e=>setAdvanced({...advanced,skills:e.target.value})}/></label>
          <label>Exclude keywords<input maxLength={500} value={advanced.exclude} placeholder="Unwanted terms, comma separated" onChange={e=>setAdvanced({...advanced,exclude:e.target.value})}/></label>
          <label>Seniority in job title<select value={advanced.seniority} onChange={e=>updateAdvanced({seniority:e.target.value})}><option value="">Any seniority</option><option value="entry">Entry / junior / internship</option><option value="senior">Senior</option><option value="lead">Lead / staff / management</option></select></label>
          <label>Posting age<select value={advanced.posted_days} onChange={e=>updateAdvanced({posted_days:Number(e.target.value)})}><option value={0}>Any date</option><option value={1}>Last 24 hours</option><option value={3}>Last 3 days</option><option value={7}>Last 7 days</option><option value={30}>Last 30 days</option></select></label>
          <label>Sort by<select value={advanced.sort} onChange={e=>updateAdvanced({sort:e.target.value})}><option value="relevance">Default order</option><option value="newest">Newest first</option><option value="title">Job title A–Z</option><option value="company">Company A–Z</option></select></label>
          <button type="button" className="primary-button" disabled={loading} onClick={()=>loadJobs()}>Apply filters</button>
        </div>
        <p>Required and excluded keywords search listing text. Seniority uses title keywords. Date filters exclude listings without a published date; historical records may have none.</p>
      </details>
      <SavedSearchControls activeSearchId={savedSearchId || ""} filters={{source:jobSource,term:searchTerm,type:employmentType,mode:workArrangement,city:location,field:role,...advanced}} onApply={applySavedFilters}/>
      <div ref={resultsRef} className="cn-discovery-count" style={{ scrollMarginTop: 110 }}><strong>{total.toLocaleString()} matching jobs</strong>{profileMode && <span>Based on your profile skills (first 100 shown)</span>}{loading && <span>Loading…</span>}</div>
      {error && <p role="alert" className="cn-discovery-error">{error}</p>}
      {!loading && jobs.length === 0 && !error && <p>No jobs matched. Try clearing some filters. Some employers do not publish employment type or work arrangement.</p>}
      <div className="cn-discovery-grid">
        {jobs.map((job, index) => <article className="cn-discovery-card" key={`${job.id}-${index}`}>
          <div className="cn-job-top"><span className="cn-company-avatar">{String(job.company || "?").slice(0,1).toUpperCase()}</span><span className="cn-source">{jobSource === "historical" ? "Historical · Unverified" : job.source_slug}</span></div>
          {job.duplicate_count>1 && <p className="job-duplicate-hint">Combined {job.duplicate_count} source listings for this posting.</p>}
          {job.possible_duplicate_count>0 && <p className="job-duplicate-hint">Similar roles appear in this feed. Check each posting’s requirements.</p>}
          <h3>{job.title || "Untitled position"}</h3><p className="cn-discovery-company">{job.company || "Company not listed"}</p>
          <div className="cn-discovery-tags"><span><MapPin size={14}/> {job.location || "Not specified"}</span><span>{job.employment_type || "Type not specified"}</span>{job.work_mode !== "Not specified" && <span>{job.work_mode}</span>}</div>
          <div className="cn-discovery-card-actions"><button type="button" className="primary-button" onClick={() => setSelectedJob(job)}>Apply with Nova <ArrowRight size={16}/></button><SaveJobButton job={job}/></div>
        </article>)}
      </div>
      {!profileMode && jobs.length < total && <div className="cn-load-more"><button type="button" className="secondary-button" disabled={loading} onClick={() => loadJobs({ requestedPage: page + 1, append: true })}>{loading ? "Loading…" : `Load more (${jobs.length} of ${total})`}</button></div>}
      {sessionStorage.getItem("careernova-pending-application") && !assistantJob && <div style={{margin:"16px 0",padding:16,border:"1px solid #7465b7",borderRadius:12}}><strong>Application waiting for your profile</strong><p>After saving your Candidate Profile, continue the selected application here.</p><button type="button" className="primary-button" onClick={() => { try { beginNovaApplication(JSON.parse(sessionStorage.getItem("careernova-pending-application"))); } catch { say("Please select a job again."); } }}>Continue application</button></div>}
      {assistantJob && <ApplicationVoiceAssistant job={assistantJob} onClose={() => setAssistantJob(null)}/>}
      {selectedJob && <div className="cn-apply-overlay" role="dialog" aria-modal="true" aria-label="Apply for selected job"><div className="cn-apply-dialog">
        <button type="button" className="cn-close-dialog" onClick={() => setSelectedJob(null)} aria-label="Close"><X size={20}/></button>
        <h2>{selectedJob.title}</h2><p>{selectedJob.company} · {selectedJob.location}</p><JobPreparation key={selectedJob.id} job={selectedJob}/><p>Nova can assist with supported application forms. Review and confirm before final submission.</p>
        <div className="cn-discovery-actions"><button type="button" className="primary-button" onClick={() => { setAssistantJob(selectedJob); setSelectedJob(null); }}>Start application assistant</button><Link className="secondary-button" to="/resumes" state={{job_title:selectedJob.title,job_description:selectedJob.description||''}}>Prepare resume for this job</Link><Link className="secondary-button" to="/interview" state={{job_title:selectedJob.title,job_description:selectedJob.description||''}}>Practise an interview</Link>
        {/^https?:\/\//i.test(selectedJob.apply_url || "") && <a className="secondary-button" href={selectedJob.apply_url} target="_blank" rel="noopener noreferrer">Open job posting <ArrowUpRight size={16}/></a>}</div>
      </div></div>}
    </section>
  );
}

function FeaturePage({ title, description, icon: Icon, children }) {
  return (
    <section
      className="section-padding"
      style={{
        minHeight: "75vh",
        maxWidth: 1100,
        margin: "0 auto",
        paddingTop: 110,
      }}
    >
      <div className="section-heading">
        <span className="section-kicker">
          <Icon size={20} /> CAREERNOVA AI
        </span>
        <h2>
          <span className="gradient-text">{title}</span>
        </h2>
        <p>{description}</p>
      </div>
      {children}
    </section>
  );
}
function ResumePage() {
  const location = useLocation();
  const savedResumeId = new URLSearchParams(location.search).get("resume_id");
  const [file, setFile] = useState(null);
  const [assistantJob, setAssistantJob] = useState(null);
  const [matchedResumeFile, setMatchedResumeFile] = useState(null);
  const [matchedResumeId, setMatchedResumeId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState([]);
  const [searched, setSearched] = useState(false);
  async function handleResumeMatch(event) {
    event.preventDefault();
    if (!file && !savedResumeId) {
      setError("Please select a PDF or DOCX resume.");
      return;
    }
    if (file && !/\.(pdf|docx)$/i.test(file.name)) {
      setError("Only PDF and DOCX files are supported.");
      return;
    }
    if (file && file.size > 5 * 1024 * 1024) {
      setError("Your resume must be 5 MB or smaller.");
      return;
    }
    setLoading(true);
    setError("");
    setResults([]);
    setSearched(false);
    try {
      const formData = new FormData();
      if (file) formData.append("file", file);
      const response = await apiFetch(file ? `${API_URL}/api/resume-match?limit=20` : `${API_URL}/api/resumes/${encodeURIComponent(savedResumeId)}/matches`, {
        method: "POST",
        body: file ? formData : undefined,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : `Resume matching failed (HTTP ${response.status})`);
      }
      setResults(Array.isArray(data.jobs) ? data.jobs : []);
      setMatchedResumeFile(file);
      setMatchedResumeId(file ? '' : savedResumeId || '');
      setSearched(true);
      requestAnimationFrame(() => {
        document.getElementById("resume-results")?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    } catch (err) {
      setError(err.message || "Unable to match your resume.");
    } finally {
      setLoading(false);
    }
  }
  return (
    <FeaturePage
      title="AI Resume Matching"
      description="Upload your resume and discover jobs that match your skills and experience."
      icon={FileText}
    >
      <p className="resume-library-link"><Link className="secondary-button" to="/resumes">Manage resume versions, coaching & match explanations →</Link></p>
      <form className="search-panel cn-search-panel" onSubmit={handleResumeMatch} style={{ maxWidth: 650, margin: "auto" }}>
        <div className="panel-heading cn-panel-heading"><FileText size={22} /> Upload Your Resume</div>
        <label htmlFor="resume-file">Select a PDF or DOCX file (maximum 5 MB)</label>
        <input
          id="resume-file"
          type="file"
          accept=".pdf,.docx"
          onChange={(event) => {
            setFile(event.target.files?.[0] || null);
            setError("");
          }}
          style={{ margin: "20px 0" }}
        />
        {savedResumeId && !file && <p>Using saved resume version #{savedResumeId}. Select a file to use a different resume.</p>}
        {file && <p>Selected: {file.name}</p>}
        <button className="primary-button search-button cn-search-button" type="submit" disabled={loading}>
          {loading ? "Analyzing Resume..." : "Find Resume Matches"}
          <ArrowRight size={18} />
        </button>
        {error && <p role="alert" style={{ color: "#ff9aa8", marginTop: 12 }}>{error}</p>}
        <p className="panel-note">Match against the indexed job collection when available, or live listings using skill and keyword overlap. Scores describe listing overlap, not hiring probability.</p>
      </form>
      {searched && (
        <div id="resume-results" className="search-results cn-results" style={{ maxWidth: 1200, margin: "40px auto 0", scrollMarginTop: 100 }}>
          <h3 style={{ marginBottom: 20 }}>Resume Matches ({results.length})</h3>
          <p>Choose Apply with AI to fill supported saved Candidate Profile details, then answer missing questions by voice or typing. Keep the employer browser open. Review each voice answer before confirming; final submission is yours.</p>
          {results.length === 0 && <p>No matching jobs found. Try another resume.</p>}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 300px), 1fr))", gap: 18 }}>
            {results.map((job, index) => {
              const score = Number(job.faiss_score);
              const validScore = job.faiss_score != null && Number.isFinite(score);
              const assistedJob = applicationJob(job);
              const validUrl = Boolean(assistedJob);
              const percentage = job.match_percentage == null ? null : Number(job.match_percentage);
              const hasPercentage = percentage !== null && Number.isFinite(percentage);
              const safePercentage = hasPercentage ? Math.max(0, Math.min(100, percentage)) : null;
              const skillPercentage = job.skill_match_percentage == null ? null : Number(job.skill_match_percentage);
              const hasSkillPercentage = skillPercentage !== null && Number.isFinite(skillPercentage);
              const matchedSkills = Array.isArray(job.matched_skills) ? job.matched_skills : [];
              const missingSkills = Array.isArray(job.missing_skills) ? job.missing_skills : [];
              return (
                <article key={job.id || index} style={{ padding: 24, border: "1px solid #39354d", borderRadius: 16, background: "#141320" }}>
                  <div className="cn-job-top"><div className="cn-company-avatar">{String(job.company || "?").slice(0,1).toUpperCase()}</div><span className="cn-source"><span className="cn-live-dot"/> {job.matching_method === 'live_keywords' ? `Live listing · ${job.source || 'Connected feed'}` : `Historical dataset · ${job.source_slug || 'Dataset'}`}</span></div>
                  {job.matching_method === 'live_keywords' && <p>Skill and keyword match · semantic index unavailable</p>}
                  <h3>{job.title || "Untitled position"}</h3>
                  <p>{job.company || "Company not listed"}</p>
                  <p><MapPin size={15} style={{ verticalAlign: "middle" }} /> {job.location || "Location not listed"}</p>
                  <p>{job.work_mode || ""}{job.employment_type ? ` • ${job.employment_type}` : ""}</p>
                  {hasPercentage && (
                    <div style={{ marginTop: 18, marginBottom: 18 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 10 }}>
                        <strong style={{ color: "#eee8ff" }}>AI Resume Match</strong>
                        <strong style={{ color: "#b79aff", fontSize: 23 }}>{safePercentage.toFixed(1)}%</strong>
                      </div>
                      <div role="progressbar" aria-label="AI resume match" aria-valuenow={safePercentage} aria-valuemin={0} aria-valuemax={100}
                        style={{ width: "100%", height: 11, background: "#39354d", borderRadius: 999, overflow: "hidden" }}>
                        <div style={{ width: `${safePercentage}%`, height: "100%", background: "linear-gradient(90deg, #8b5cf6, #4778ff)", borderRadius: 999 }} />
                      </div>
                    </div>
                  )}
                  {hasSkillPercentage && <p style={{ color: "#c4b5fd" }}>Skill match: {Math.max(0, Math.min(100, skillPercentage)).toFixed(1)}%</p>}
                  {matchedSkills.length > 0 && (
                    <div style={{ marginTop: 14 }}>
                      <strong style={{ color: "#7ee7b0" }}>Matched skills</strong>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 9 }}>
                        {matchedSkills.map((skill, skillIndex) => (
                          <span key={`${skill}-${skillIndex}`} style={{ background: "#17372f", color: "#9bf2c6", padding: "6px 10px", borderRadius: 999, fontSize: 12 }}>{skill}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {missingSkills.length > 0 && (
                    <div style={{ marginTop: 14 }}>
                      <strong style={{ color: "#ffb5b5" }}>Skills to develop</strong>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 9 }}>
                        {missingSkills.map((skill, skillIndex) => (
                          <span key={`${skill}-${skillIndex}`} style={{ background: "#38242c", color: "#ffd1d1", padding: "6px 10px", borderRadius: 999, fontSize: 12 }}>{skill}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {!hasPercentage && <p style={{ color: "#a6a0b8", fontSize: 13 }}>Match percentage unavailable for this job.</p>}
                  {validScore && <p style={{ color: "#b79aff", fontSize: 13 }}>FAISS similarity: {score.toFixed(3)}</p>}
                  {validUrl ? <div style={{display:'flex',gap:10,flexWrap:'wrap',marginTop:16}}>
                    <button type="button" className="primary-button" onClick={()=>setAssistantJob(assistedJob)}>Apply with AI <Bot size={16}/></button>
                    <a href={assistedJob.apply_url} target="_blank" rel="noopener noreferrer" className="secondary-button" style={{display:'inline-flex',alignItems:'center',gap:8}}>Open job posting <ArrowUpRight size={16}/></a>
                  </div> : <p>Application link unavailable for this record. Search for the opening on the employer’s website.</p>}
                  <SaveJobButton job={job} />
                </article>
              );
            })}
          </div>
        </div>
      )}
      {assistantJob&&<ApplicationVoiceAssistant job={assistantJob} initialResumeFile={matchedResumeFile} initialResumeId={matchedResumeId} onClose={()=>setAssistantJob(null)}/>}
    </FeaturePage>
  );
}
function DashboardPage({ savedOnly = false }) {
  const { accountName } = useAuth();
  const [jobs, setJobs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notes, setNotes] = useState({});
  const [busyId, setBusyId] = useState(null);
  async function refresh() {
    setLoading(true);
    setError("");
    try {
      const [jobData, statData] = await Promise.all([
        dashboardRequest(`/api/dashboard/jobs`),
        dashboardRequest(`/api/dashboard/stats`),
      ]);
      setJobs(Array.isArray(jobData) ? jobData : Array.isArray(jobData.jobs) ? jobData.jobs : []);
      setStats(statData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { refresh(); }, []);
  async function updateJob(job, status) {
    setBusyId(job.id);
    setError("");
    try {
      await dashboardRequest(`/api/dashboard/jobs/${job.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status, notes: notes[job.id] ?? job.notes ?? "" }),
      });
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally { setBusyId(null); }
  }
  async function removeJob(job) {
    if (!window.confirm(`Remove ${job.job_title || "this job"} from your dashboard?`)) return;
    setBusyId(job.id);
    setError("");
    try {
      await dashboardRequest(`/api/dashboard/jobs/${job.id}`, { method: "DELETE" });
      await refresh();
    } catch (err) { setError(err.message); }
    finally { setBusyId(null); }
  }
  const cards = [
    ["Total Jobs", stats?.total_jobs ?? 0],
    ["Saved", stats?.saved ?? 0],
    ["Applied", stats?.applied ?? 0],
    ["Interviews", stats?.interviews ?? 0],
    ["Offers", stats?.offers ?? 0],
    ["Rejected", stats?.rejected ?? 0],
    ["Average Match", stats?.average_match == null ? "—" : `${Number(stats.average_match).toFixed(1)}%`],
  ];
  const inputStyle = { padding: 12, borderRadius: 10, border: "1px solid #39354d", background: "#141320", color: "white", width: "100%" };
  return (
    <FeaturePage title={savedOnly ? "Saved Jobs" : "Career Dashboard"} description="Track saved jobs, applications, interviews, and your AI match insights." icon={ChartNoAxesCombined}>
      <div className="platform-dashboard-banner"><div><span className="platform-eyebrow">YOUR NEXT CHAPTER</span><h2>Welcome back{accountName ? `, ${accountName.split(" ")[0]}` : ""}.</h2><p>Small steps today. A brighter career tomorrow.</p></div><div className="platform-actions"><Link to="/applications" className="secondary-button">Application board</Link><Link to="/tools" className="primary-button">Open career tools <ArrowUpRight size={18}/></Link></div></div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 20 }}>
        <button className="secondary-button" type="button" onClick={refresh} disabled={loading}><RefreshCw size={16} /> Refresh</button>
      </div>
      {error && <p role="alert" style={{ color: "#ff9aa8" }}>{error}</p>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 14, marginBottom: 30 }}>
        {cards.map(([label, value]) => (
          <div key={label} style={{ background: "#141320", border: "1px solid #39354d", borderRadius: 16, padding: 20 }}>
            <p style={{ color: "#b8b2ca", margin: "0 0 10px" }}>{label}</p>
            <strong style={{ fontSize: 28, color: "#b79aff" }}>{value}</strong>
          </div>
        ))}
      </div>
      <h3 style={{ marginBottom: 18 }}>Tracked Opportunities</h3>
      {loading && <p>Loading dashboard...</p>}
      {!loading && jobs.length === 0 && <p>No saved jobs yet. Visit AI Job Search or Resume Matching and click Save Job.</p>}
      <div style={{ display: "grid", gap: 18 }}>
        {jobs.filter(job => !savedOnly || job.status === "Saved").map((job) => (
          <article key={job.id} style={{ background: "#141320", border: "1px solid #39354d", borderRadius: 16, padding: 24 }}>
            <h3>{job.job_title || "Untitled position"}</h3>
            <p>{job.company || "Unknown company"} • {job.location || "Location not specified"}</p>
            {job.match_percentage != null && <p style={{ color: "#b79aff" }}>AI Match: {Number(job.match_percentage).toFixed(1)}%</p>}
            {job.apply_url && /^https?:\/\//i.test(job.apply_url) && <a href={job.apply_url} target="_blank" rel="noopener noreferrer">Open application <ArrowUpRight size={14} /></a>}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginTop: 16 }}>
              <label>Status
                <select style={inputStyle} value={job.status || "Saved"} disabled={busyId === job.id} onChange={(e) => updateJob(job, e.target.value)}>
                  {["Saved", "Applied", "Interview", "Offer", "Rejected"].map((status) => <option key={status}>{status}</option>)}
                </select>
              </label>
              <label>Notes
                <textarea style={inputStyle} rows={2} placeholder="Application notes..." value={notes[job.id] ?? job.notes ?? ""} onChange={(e) => setNotes((old) => ({ ...old, [job.id]: e.target.value }))} />
              </label>
            </div>
            <div style={{ display: "flex", gap: 12, marginTop: 16, flexWrap: "wrap" }}>
              <button className="secondary-button" type="button" disabled={busyId === job.id} onClick={() => updateJob(job, job.status || "Saved")}>Save Changes</button>
              <button className="secondary-button" type="button" disabled={busyId === job.id} onClick={() => removeJob(job)}><Trash2 size={16} /> Remove</button>
            </div>
          </article>
        ))}
      </div>
    </FeaturePage>
  );
}
function CareerGuideBot() {
  const {user} = useAuth();
  return <NovaChatbot key={user?.id || "guest"}/>;
}
function ScrollManager() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    if (hash) {
      const id = hash.substring(1);
      requestAnimationFrame(() => {
        document.getElementById(id)?.scrollIntoView({
          behavior: "smooth",
        });
      });
    } else {
      window.scrollTo(0, 0);
    }
  }, [pathname, hash]);
  return null;
}
function App() {
  return (
    <AuthProvider>
    <div className="website">
      <ScrollManager />
      <Header />
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route element={<ProtectedWorkspace/>}>
          <Route path="/jobs" element={<JobsPage />} />

          <Route path="/resume" element={<ResumePage />} />
          <Route path="/alerts" element={<AlertCenter />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/profile" element={<CandidateProfilePage />} />
          <Route path="/saved" element={<DashboardPage savedOnly />} />
          <Route path="/searches" element={<SavedSearchPage />} />
          <Route path="/timeline" element={<ApplicationTimeline />} />
          <Route path="/tools" element={<CareerTools />} />
          <Route path="/applications" element={<ApplicationBoard />} />
          <Route path="/resumes" element={<ResumeLibrary />} />
          <Route path="/interview" element={<InterviewStudio />} />
          <Route path="/reminders" element={<RemindersPage />} />
          <Route path="/compare" element={<JobComparison />} />
          <Route path="/trust" element={<TrustCenter />} />
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          </Route>
          <Route path="/features" element={<FeaturesPage />} />
          <Route path="/forgot-password" element={<AccountRecovery />} />
          <Route path="/reset-password" element={<AccountRecovery reset />} />
          <Route path="/login" element={<AuthPage mode="login" />} />
          <Route path="/register" element={<AuthPage mode="register" />} />
          <Route path="*" element={<HomePage />} />
        </Routes>
      </main>
      <Footer />
      <CareerGuideBot />
    </div>
    </AuthProvider>
  );
}
export default App;
