import ApplicationVoiceAssistant from "./ApplicationVoiceAssistant";
import CandidateProfilePage from "./CandidateProfilePage";
import VoiceInput from "./VoiceInput";
import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Link,
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
} from "lucide-react";
import "./App.css";
const API_URL = "http://127.0.0.1:8000";
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
function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
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
      <nav className={menuOpen ? "nav-links open" : "nav-links"}>
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
        <Link
          className="nav-cta"
          to="/jobs"
          onClick={() => setMenuOpen(false)}
        >
          Get Started <ArrowUpRight size={16} />
        </Link>
      </nav>
      <button
        className="mobile-menu"
        aria-label="Toggle navigation"
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
  const [searchTerm, setSearchTerm] = useState("");
  const [jobs, setJobs] = useState([]);
  useEffect(() => {
    let active = true;
    fetch(`${API_URL}/api/jobs?limit=3`)
      .then((res) => res.ok ? res.json() : Promise.reject(new Error("Jobs unavailable")))
      .then((data) => { if (active) setJobs(Array.isArray(data.jobs) ? data.jobs : []); })
      .catch(() => {});
    return () => { active = false; };
  }, []);
  function searchJobs(event) {
    event.preventDefault();
    navigate(searchTerm.trim() ? `/jobs?q=${encodeURIComponent(searchTerm.trim())}` : "/jobs");
  }
  return (
    <>
      <section className="nova-landing" id="home">
        <div className="nova-ambient nova-ambient-left" />
        <div className="nova-ambient nova-ambient-right" />
        <div className="nova-landing-inner">
          <div className="nova-kicker"><Sparkles size={14}/> AI-POWERED CAREER PLATFORM</div>
          <h1>Find your next opportunity.<br/><span>Let AI do the work.</span></h1>
          <p className="nova-lead">Discover matching jobs, understand your opportunities, and complete applications faster — all in one place.</p>
          <form className="nova-search" onSubmit={searchJobs}>
            <Search size={23} aria-hidden="true" />
            <input aria-label="Search jobs or skills" placeholder="Search jobs, skills, companies..." value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} />
            <button type="submit" aria-label="Explore matching jobs"><span>Find Jobs</span><ArrowRight size={20}/></button>
          </form>
          <div className="nova-quick-links">
            <Link to="/jobs"><span><Search size={24}/></span><strong>AI Job Matching</strong><small>Discover relevant roles</small><ArrowUpRight size={17}/></Link>
            <Link to="/resume"><span><FileText size={24}/></span><strong>Resume Analysis</strong><small>Match your experience</small><ArrowUpRight size={17}/></Link>
            <Link to="/jobs"><span><Sparkles size={24}/></span><strong>Smart Autofill</strong><small>Apply with AI assistance</small><ArrowUpRight size={17}/></Link>
          </div>
          <div className="nova-landing-bottom"><span><CheckCircle2 size={16}/> Powered by semantic search</span><span><CheckCircle2 size={16}/> Your review before submission</span></div>
        </div>
      </section>
      <section className="nova-discover section-padding">
        <div className="nova-discover-heading"><div><span className="section-kicker">DISCOVER OPPORTUNITIES</span><h2>Explore jobs picked from our listings</h2><p>Browse recently available postings, or search by your skills.</p></div><Link to="/jobs" className="secondary-button">View all jobs <ArrowRight size={17}/></Link></div>
        <div className="nova-job-grid">
          {jobs.length ? jobs.slice(0,3).map((job, index) => (
            <Link to="/jobs" className="nova-job-card" key={job.id || index}>
              <div className="nova-job-symbol"><BriefcaseBusiness size={22}/></div>
              <h3>{job.title || "Job opportunity"}</h3><p>{job.company || "Company not listed"}</p>
              <span><MapPin size={14}/>{job.location || "Location not listed"}</span>
              <div className="nova-job-card-bottom">View opportunity <ArrowUpRight size={17}/></div>
            </Link>
          )) : <div className="nova-no-jobs">Job previews will appear here when your backend returns listings. <Link to="/jobs">Explore Jobs <ArrowRight size={14}/></Link></div>}
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
const DASHBOARD_USER = "local-careernova-user";
async function dashboardRequest(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
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
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function save() {
    setBusy(true);
    setMessage("");
    try {
      await dashboardRequest("/api/dashboard/save", {
        method: "POST",
        body: JSON.stringify({
          user_id: DASHBOARD_USER,
          job_id: String(job.id ?? ""),
          job_title: job.title || "Untitled position",
          company: job.company || "Unknown company",
          location: job.location || "Not specified",
          apply_url: job.apply_url || null,
          match_percentage: job.match_percentage == null ? null : Number(job.match_percentage),
        }),
      });
      setMessage("Saved!");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div style={{ marginTop: 12 }}>
      <button type="button" className="secondary-button" disabled={busy} onClick={save}>
        <Bookmark size={16} /> {busy ? "Saving..." : "Save Job"}
      </button>
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
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  const [voiceMessage, setVoiceMessage] = useState("");
  const [agentLoading, setAgentLoading] = useState(false);
  const [assistantJob, setAssistantJob] = useState(null);
  const [agentMessage, setAgentMessage] = useState("");

  const [recommendationMode, setRecommendationMode] = useState("latest");
  const [jobCategory, setJobCategory] = useState("All Jobs");
  const [recommendedLoading, setRecommendedLoading] = useState(true);
  const [recommendedError, setRecommendedError] = useState("");

  useEffect(() => {
    let active = true;
    async function loadRecommendations() {
      setRecommendedLoading(true);
      setRecommendedError("");
      try {
        const response = await fetch(`${API_URL}/api/jobs?limit=24`);
        if (!response.ok) throw new Error(`Unable to load recommendations (HTTP ${response.status})`);
        const data = await response.json();
        if (active) {
          setResults(Array.isArray(data.jobs) ? data.jobs : []);
          setSearched(true);
          setRecommendationMode("latest");
        }
      } catch (error) {
        if (active) setRecommendedError(error.message);
      } finally {
        if (active) setRecommendedLoading(false);
      }
    }
    loadRecommendations();
    return () => { active = false; };
  }, []);

  async function personalizeJobs() {
    setLoading(true);
    setError("");
    try {
      const profileResponse = await fetch(`${API_URL}/api/profile/local-candidate`);
      if (!profileResponse.ok) throw new Error("Save your Candidate Profile to get personalized recommendations.");
      const profile = await profileResponse.json();
      const skills = String(profile.skills || "").trim();
      if (!skills) throw new Error("Add your skills in My Profile to personalize recommendations.");
      const url = new URL(`${API_URL}/api/ai-search`);
      url.searchParams.set("q", skills.slice(0, 400));
      url.searchParams.set("limit", "20");
      const response = await fetch(url.toString());
      if (!response.ok) throw new Error(`AI recommendations unavailable (HTTP ${response.status})`);
      const data = await response.json();
      setResults(Array.isArray(data.jobs) ? data.jobs : []);
      setSearched(true);
      setRecommendationMode("personalized");
      setSelectedJob(null);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  }

  const categories = ["All Jobs", "Data Analyst", "Data Engineer", "Data Scientist", "Internships"];
  const visibleJobs = results.filter((job) => {
    const title = String(job.title || "").toLowerCase();
    const type = String(job.employment_type || "").toLowerCase();
    if (jobCategory === "All Jobs") return true;
    if (jobCategory === "Internships") return title.includes("intern") || type.includes("intern");
    return title.includes(jobCategory.toLowerCase());
  });

  async function searchJobs(searchText) {
    const term = searchText.trim();
    if (!term) {
      setError("Please enter a job title or skill.");
      return;
    }
    setLoading(true);
    setError("");
    setSearched(true);
    setResults([]);
    setSelectedJob(null);
    setVoiceMessage("");
    try {
      const url = new URL(`${API_URL}/api/ai-search`);
      url.searchParams.set("q", term);
      url.searchParams.set("limit", "20");
      const response = await fetch(url.toString());
      if (!response.ok) {
        throw new Error(`Search failed (HTTP ${response.status})`);
      }
      const data = await response.json();
      setResults(Array.isArray(data.jobs) ? data.jobs : []);
      setRecommendationMode("search");
      setJobCategory("All Jobs");
    } catch (err) {
      setError(err.message || "Unable to search jobs.");
    } finally {
      setLoading(false);
    }
  }
  function handleSearch(event) {
    event.preventDefault();
    searchJobs(query);
  }
  function selectJob(job) {
    setSelectedJob(job);
    setAgentMessage("");
    setVoiceMessage(`Selected: ${job.title || "Untitled position"}`);
  }
  function launchApplicationAssistant() {
    if (!selectedJob || agentLoading) return;
    const applyUrl = selectedJob.apply_url;
    if (typeof applyUrl !== "string" || !/^https?:\/\//i.test(applyUrl)) {
      setAgentMessage("This job has no valid application URL.");
      return;
    }
    // The assistant owns the Playwright session. Do not also open a separate browser.
    setAssistantJob(selectedJob);
    setSelectedJob(null);
  }
  function handleVoiceTranscript(spokenText) {
    const speech = spokenText.trim();
    const command = speech.toLowerCase().replace(/[.!?]+$/g, "").trim();
    const action = /^(?:please\s+)?(?:select|choose|open|show(?:\s+me)?|apply\s+(?:for|to))\s+(.+)$/i.exec(command);
    if (action && results.length) {
      const target = action[1].replace(/^(?:the|job|position)\s+/i, "").trim();
      const ordinals = { first: 1, second: 2, third: 3, fourth: 4, fifth: 5,
        sixth: 6, seventh: 7, eighth: 8, ninth: 9, tenth: 10 };
      const numberMatch = /^(?:(?:job|position|number)\s+)?(\d+)(?:st|nd|rd|th)?(?:\s+(?:job|position))?$/i.exec(target);
      const ordinalMatch = /^(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)(?:\s+(?:job|position))?$/i.exec(target);
      const position = numberMatch ? Number(numberMatch[1]) : ordinalMatch ? ordinals[ordinalMatch[1]] : null;
      let found = null;
      if (position !== null) {
        found = results[position - 1] || null;
      } else {
        const normalized = target.replace(/^(?:the|for)\s+/i, "").replace(/\s+(?:job|position)$/i, "");
        found = results.find((job) => (job.title || "").toLowerCase().includes(normalized));
      }
      if (found) {
        selectJob(found);
      } else {
        setVoiceMessage("I couldn't identify that job. Try 'select the first job' or use a job's Select Job button.");
      }
      return;
    }
    if (action && !results.length) {
      setVoiceMessage("Search for jobs first, then say which one to select.");
      return;
    }
    const cleaned = speech.replace(/^(please\s+)?(find|search for|show me|look for)\s+/i, "").replace(/\s+jobs?\s*$/i, " jobs");
    setQuery(cleaned);
    searchJobs(cleaned);
  }
  return (
    <section className="jobs-section section-padding">
      <div className="jobs-layout">
        <div className="jobs-intro">
          <span className="section-kicker">DISCOVER YOUR FUTURE</span>
          <h2>
            Great opportunities{" "}
            <span className="gradient-text">start here.</span>
          </h2>
          <p>
            Search by role, technology, or skills. Our AI search
            engine understands what you're looking for.
          </p>
          <div className="jobs-benefits">
            <span>
              <CheckCircle2 size={17} /> Skill-based job discovery
            </span>
            <span>
              <CheckCircle2 size={17} /> AI semantic matching
            </span>
            <span>
              <CheckCircle2 size={17} /> Relevant application links
            </span>
          </div>
        </div>
        <form className="search-panel" onSubmit={handleSearch}>
          <div className="panel-heading">
            <Sparkles size={22} /> AI Career Search
          </div>
          <label htmlFor="job-query">
            What kind of role are you looking for?
          </label>
          <div className="search-input-wrap">
            <Search size={19} />
            <input
              id="job-query"
              placeholder="e.g. Data Analyst with Python and SQL"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
          <VoiceInput onTranscript={handleVoiceTranscript} disabled={loading} />
          <p className="panel-note">After searching, say “select the first job” or “apply for the second job”.</p>
          {voiceMessage && <p role="status" style={{ color: "#b79aff" }}>{voiceMessage}</p>}
          <button
            className="primary-button search-button"
            type="submit"
            disabled={loading}
          >
            {loading ? "Searching..." : "Find Matching Jobs"}
            <ArrowRight size={18} />
          </button>
          <p className="panel-note">
            Search job postings using FAISS semantic matching.
          </p>
          {error && (
            <p role="alert" style={{ color: "#ff9aa8" }}>
              {error}
            </p>
          )}
          {searched && !loading && !error && (
            <p className="panel-note">
              {results.length} result(s) shown
            </p>
          )}
        </form>
      </div>
      {assistantJob && (
        <ApplicationVoiceAssistant
          job={assistantJob}
          onClose={() => setAssistantJob(null)}
        />
      )}
      {selectedJob && (
        <div role="dialog" aria-modal="true" aria-label="Selected job application options"
          onKeyDown={(event) => { if (event.key === "Escape") setSelectedJob(null); }}
          style={{ position: "fixed", inset: 0, zIndex: 1000, background: "#000b",
            display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
          <div style={{ background: "#191726", border: "1px solid #54496b", borderRadius: 18,
            padding: 28, maxWidth: 560, width: "100%", maxHeight: "90vh", overflowY: "auto" }}>
            <button type="button" className="secondary-button" style={{ float: "right" }}
              onClick={() => setSelectedJob(null)} aria-label="Close selected job">✕</button>
            <h2 style={{ marginTop: 8 }}>{selectedJob.title || "Untitled position"}</h2>
            <p>{selectedJob.company || "Company not listed"} • {selectedJob.location || "Location not listed"}</p>
            <p>Choose how you want to continue your application.</p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 20 }}>
              {typeof selectedJob.apply_url === "string" && /^https?:\/\//i.test(selectedJob.apply_url) ? (
                <a className="primary-button" href={selectedJob.apply_url} target="_blank"
                  rel="noopener noreferrer" style={{ textDecoration: "none" }}>
                  Apply Manually <ArrowUpRight size={16} />
                </a>
              ) : <p>No valid application URL is available for this job.</p>}
              <button type="button" className="secondary-button"
                disabled={agentLoading || !/^https?:\/\//i.test(selectedJob.apply_url || "")}
                onClick={launchApplicationAssistant}>
                {agentLoading ? "Launching Assistant..." : "Apply with AI Assistant"}
              </button>
            </div>
            {agentMessage && <p role="status" style={{ marginTop: 14, color: "#c4b5fd", overflowWrap: "anywhere" }}>{agentMessage}</p>}
            <p style={{ fontSize: 13, color: "#b8b2ca", marginTop: 16 }}>
              AI assistance will require your review and confirmation before submission.
            </p>
          </div>
        </div>
      )}
      <div className="recommendation-toolbar" aria-label="Job recommendation filters">
        <div>
          <span className="section-kicker">YOUR JOB DISCOVERY</span>
          <h2>{recommendationMode === "personalized" ? "Recommended for your skills" : "Explore recommended opportunities"}</h2>
          <p>Browse available postings or personalize suggestions using your saved profile.</p>
        </div>
        <button type="button" className="secondary-button" disabled={loading} onClick={personalizeJobs}>
          <Sparkles size={17}/> {loading ? "Matching..." : "Match My Profile"}
        </button>
      </div>
      <div className="job-category-filters" aria-label="Filter by job category">
        {categories.map((category) => (
          <button key={category} type="button" className={jobCategory === category ? "job-category active" : "job-category"}
            aria-pressed={jobCategory === category} onClick={() => setJobCategory(category)}>{category}</button>
        ))}
      </div>
      {recommendedLoading && <p className="recommendation-status">Loading recommended jobs...</p>}
      {recommendedError && <p role="alert" className="recommendation-status">{recommendedError}</p>}
      {searched && (
        <div
          className="search-results"
          style={{ maxWidth: 1200, margin: "40px auto 0" }}
        >
          <h3 style={{ marginBottom: 20 }}>{recommendationMode === "personalized" ? "Personalized Matches" : "Available Jobs"} ({visibleJobs.length})</h3>
          {loading && <p>Finding your best AI matches...</p>}
          {!loading && !error && results.length === 0 && (
            <p>No matching jobs found. Try another search.</p>
          )}
          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit, minmax(min(100%, 300px), 1fr))",
              gap: 18,
            }}
          >
            {visibleJobs.map((job, index) => {
              const score = Number(job.faiss_score);
              const validScore = Number.isFinite(score);
              const validUrl =
                typeof job.apply_url === "string" &&
                /^https?:\/\//i.test(job.apply_url);
              return (
                <article
                  key={job.id || index}
                  style={{
                    padding: 24,
                    border: "1px solid #39354d",
                    borderRadius: 16,
                    background: "#141320",
                  }}
                >
                  <h3>{job.title || "Untitled position"}</h3>
                  <p>{job.company || "Company not listed"}</p>
                  <p>
                    <MapPin
                      size={15}
                      style={{ verticalAlign: "middle" }}
                    />{" "}
                    {job.location || "Location not listed"}
                  </p>
                  <p>
                    {job.work_mode || ""}
                    {job.employment_type
                      ? ` • ${job.employment_type}`
                      : ""}
                  </p>
                  {validScore && (
                    <p style={{ color: "#b79aff" }}>
                      Similarity score: {score.toFixed(3)}
                    </p>
                  )}
                  {validUrl && (
                    <a
                      href={job.apply_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="primary-button"
                      style={{
                        display: "inline-flex",
                        marginTop: 12,
                        textDecoration: "none",
                      }}
                    >
                      Apply Now <ArrowUpRight size={16} />
                    </a>
                  )}
                  <button type="button" className="secondary-button"
                    style={{ marginTop: 12, marginLeft: 8 }} onClick={() => selectJob(job)}>
                    Select Job
                  </button>
                  <SaveJobButton job={job} />
                </article>
              );
            })}
          </div>
        </div>
      )}
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
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState([]);
  const [searched, setSearched] = useState(false);
  async function handleResumeMatch(event) {
    event.preventDefault();
    if (!file) {
      setError("Please select a PDF or DOCX resume.");
      return;
    }
    if (!/\.(pdf|docx)$/i.test(file.name)) {
      setError("Only PDF and DOCX files are supported.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError("Your resume must be 5 MB or smaller.");
      return;
    }
    setLoading(true);
    setError("");
    setResults([]);
    setSearched(false);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API_URL}/api/resume-match?limit=20`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : `Resume matching failed (HTTP ${response.status})`);
      }
      setResults(Array.isArray(data.jobs) ? data.jobs : []);
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
      <form className="search-panel" onSubmit={handleResumeMatch} style={{ maxWidth: 650, margin: "auto" }}>
        <div className="panel-heading"><FileText size={22} /> Upload Your Resume</div>
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
        {file && <p>Selected: {file.name}</p>}
        <button className="primary-button search-button" type="submit" disabled={loading}>
          {loading ? "Analyzing Resume..." : "Find Matching Jobs"}
          <ArrowRight size={18} />
        </button>
        {error && <p role="alert" style={{ color: "#ff9aa8", marginTop: 12 }}>{error}</p>}
        <p className="panel-note">Your resume is analyzed to search for semantically relevant job postings.</p>
      </form>
      {searched && (
        <div id="resume-results" className="search-results" style={{ maxWidth: 1200, margin: "40px auto 0", scrollMarginTop: 100 }}>
          <h3 style={{ marginBottom: 20 }}>Resume Matches ({results.length})</h3>
          {results.length === 0 && <p>No matching jobs found. Try another resume.</p>}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 300px), 1fr))", gap: 18 }}>
            {results.map((job, index) => {
              const score = Number(job.faiss_score);
              const validScore = job.faiss_score != null && Number.isFinite(score);
              const validUrl = typeof job.apply_url === "string" && /^https?:\/\//i.test(job.apply_url);
              const percentage = job.match_percentage == null ? null : Number(job.match_percentage);
              const hasPercentage = percentage !== null && Number.isFinite(percentage);
              const safePercentage = hasPercentage ? Math.max(0, Math.min(100, percentage)) : null;
              const skillPercentage = job.skill_match_percentage == null ? null : Number(job.skill_match_percentage);
              const hasSkillPercentage = skillPercentage !== null && Number.isFinite(skillPercentage);
              const matchedSkills = Array.isArray(job.matched_skills) ? job.matched_skills : [];
              const missingSkills = Array.isArray(job.missing_skills) ? job.missing_skills : [];
              return (
                <article key={job.id || index} style={{ padding: 24, border: "1px solid #39354d", borderRadius: 16, background: "#141320" }}>
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
                  {validUrl && (
                    <a href={job.apply_url} target="_blank" rel="noopener noreferrer" className="primary-button" style={{ display: "inline-flex", marginTop: 12, textDecoration: "none" }}>
                      Apply Now <ArrowUpRight size={16} />
                    </a>
                  )}
                  <SaveJobButton job={job} />
                </article>
              );
            })}
          </div>
        </div>
      )}
    </FeaturePage>
  );
}
function AlertsPage() {
  const initialForm = {
    full_name: "",
    email: "",
    phone: "",
    desired_job_role: "",
    preferred_location: "",
    employment_type: "Full-time",
    notification_channel: "email",
    consent_given: false,
  };
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  function updateField(event) {
    const { name, value, type, checked } = event.target;
    setForm((previous) => ({
      ...previous,
      [name]: type === "checkbox" ? checked : value,
    }));
  }
  async function handleSubmit(event) {
    event.preventDefault();
    if (loading) return;
    setMessage("");
    setError("");
    if (!form.consent_given) {
      setError("Please agree to receive job notifications.");
      return;
    }
    if (["sms", "both"].includes(form.notification_channel) && !form.phone.trim()) {
      setError("A phone number is required for SMS notifications.");
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/job-alerts/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          full_name: form.full_name.trim(),
          email: form.email.trim(),
          phone: form.phone.trim() || null,
          desired_job_role: form.desired_job_role.trim(),
          preferred_location: form.preferred_location.trim(),
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        const details = Array.isArray(data.detail)
          ? data.detail.map((item) => item.msg).join("; ")
          : data.detail;
        throw new Error(typeof details === "string" ? details : `Registration failed (HTTP ${response.status})`);
      }
      setMessage(`Your preferences were saved! Subscription ID: ${data.subscription_id}. Notifications are not active yet; contact verification and delivery will be added next.`);
      setForm({ ...initialForm });
    } catch (err) {
      setError(err.message || "Unable to register. Please try again.");
    } finally {
      setLoading(false);
    }
  }
  const fieldStyle = {
    display: "block",
    width: "100%",
    padding: "14px",
    marginTop: 8,
    marginBottom: 20,
    borderRadius: 10,
    border: "1px solid #39354d",
    background: "#141320",
    color: "#ffffff",
    fontSize: 15,
    boxSizing: "border-box",
  };
  return (
    <FeaturePage
      title="Smart Job Alerts"
      description="Save your job preferences and choose how to receive future matching job notifications."
      icon={Bell}
    >
      <form className="search-panel" style={{ maxWidth: 700, margin: "auto" }} onSubmit={handleSubmit}>
        <div className="panel-heading"><Bell size={22} /> Create Job Alerts</div>
        <label htmlFor="alert-name">Full Name</label>
        <input id="alert-name" name="full_name" value={form.full_name} onChange={updateField}
          placeholder="Your full name" minLength={2} maxLength={150} required style={fieldStyle} />
        <label htmlFor="alert-email">Gmail / Email Address</label>
        <input id="alert-email" name="email" type="email" value={form.email} onChange={updateField}
          placeholder="example\@gmail.com" maxLength={255} required style={fieldStyle} />
        <label htmlFor="alert-phone">Phone Number (required for SMS)</label>
        <input id="alert-phone" name="phone" type="tel" value={form.phone} onChange={updateField}
          placeholder="+1 555 123 4567" maxLength={30}
          required={["sms", "both"].includes(form.notification_channel)} style={fieldStyle} />
        <label htmlFor="alert-role">Type of Job You're Looking For</label>
        <input id="alert-role" name="desired_job_role" value={form.desired_job_role} onChange={updateField}
          placeholder="Data Analyst, Data Engineer, AI Engineer" minLength={2} maxLength={255} required style={fieldStyle} />
        <label htmlFor="alert-location">Preferred Job Location</label>
        <input id="alert-location" name="preferred_location" value={form.preferred_location} onChange={updateField}
          placeholder="Houston, TX / Remote" minLength={2} maxLength={255} required style={fieldStyle} />
        <label htmlFor="alert-employment">Employment Type</label>
        <select id="alert-employment" name="employment_type" value={form.employment_type}
          onChange={updateField} style={fieldStyle}>
          <option value="Full-time">Full-time</option>
          <option value="Part-time">Part-time</option>
          <option value="Internship">Internship</option>
          <option value="Contract">Contract</option>
        </select>
        <label htmlFor="alert-channel">Notification Method</label>
        <select id="alert-channel" name="notification_channel" value={form.notification_channel}
          onChange={updateField} style={fieldStyle}>
          <option value="email">Email</option>
          <option value="sms">SMS Text Message</option>
          <option value="both">Email and SMS</option>
        </select>
        <label style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 24, lineHeight: 1.6 }}>
          <input type="checkbox" name="consent_given" checked={form.consent_given}
            onChange={updateField} required style={{ marginTop: 6 }} />
          <span>I agree to receive CareerNova AI job alerts through my selected channels. I understand I can unsubscribe from future notifications.</span>
        </label>
        <button className="primary-button search-button" type="submit" disabled={loading}>
          {loading ? "Registering..." : "Create Job Alert"} <ArrowRight size={18} />
        </button>
        {message && <p role="status" style={{ color: "#7ee7b0", marginTop: 20 }}>
          <CheckCircle2 size={17} style={{ verticalAlign: "middle" }} /> {message}
        </p>}
        {error && <p role="alert" style={{ color: "#ff9aa8", marginTop: 20 }}>{error}</p>}
        <p className="panel-note">Registration saves your preferences. Email/SMS verification and automatic notification delivery are not active yet.</p>
      </form>
    </FeaturePage>
  );
}
function DashboardPage() {
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
        dashboardRequest(`/api/dashboard/jobs?user_id=${encodeURIComponent(DASHBOARD_USER)}`),
        dashboardRequest(`/api/dashboard/stats?user_id=${encodeURIComponent(DASHBOARD_USER)}`),
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
      await dashboardRequest(`/api/dashboard/jobs/${job.id}?user_id=${encodeURIComponent(DASHBOARD_USER)}`, {
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
      await dashboardRequest(`/api/dashboard/jobs/${job.id}?user_id=${encodeURIComponent(DASHBOARD_USER)}`, { method: "DELETE" });
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
    <FeaturePage title="Career Dashboard" description="Track saved jobs, applications, interviews, and your AI match insights." icon={ChartNoAxesCombined}>
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
        {jobs.map((job) => (
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
function ScrollManager() {
  const { pathname, hash } = window.location;
  const [currentPath, setCurrentPath] = useState(pathname);
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
  }, [pathname, hash, currentPath]);
  return null;
}
function App() {
  return (
    <div className="website">
      <Header />
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/features" element={<FeaturesPage />} />
          <Route path="/resume" element={<ResumePage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/profile" element={<CandidateProfilePage />} />
          <Route path="*" element={<HomePage />} />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}
export default App;
