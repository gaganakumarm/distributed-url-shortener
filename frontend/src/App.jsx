import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity, ArrowRight, BarChart3, Check, Clipboard, Copy, ExternalLink,
  Gauge, Link2, LogOut, Menu, Plus, RefreshCw, ShieldCheck, Sparkles,
  Trash2, X, Zap,
} from "lucide-react";
import { api, auth } from "./api";

const route = () => window.location.hash.replace("#/", "") || (auth.get() ? "dashboard" : "home");

function App() {
  const [page, setPage] = useState(route());
  const [token, setToken] = useState(auth.get());
  useEffect(() => {
    const change = () => setPage(route());
    addEventListener("hashchange", change);
    return () => removeEventListener("hashchange", change);
  }, []);
  const navigate = (next) => { window.location.hash = `/${next}`; setPage(next); };
  const logout = () => { auth.clear(); setToken(null); navigate("home"); };
  const login = (value) => { auth.set(value); setToken(value); navigate("dashboard"); };

  if (page === "login" || page === "register") return <AuthPage mode={page} onSuccess={login} navigate={navigate} />;
  if (page === "dashboard" && token) return <Dashboard navigate={navigate} logout={logout} />;
  if (page === "status") return <StatusPage navigate={navigate} token={token} logout={logout} />;
  return <Landing navigate={navigate} token={token} />;
}

function Brand() {
  return <div className="brand"><span className="brand-mark"><Zap size={19} fill="currentColor" /></span><span>LinkFlux</span></div>;
}

function Landing({ navigate, token }) {
  return <main className="landing">
    <nav className="nav shell"><Brand /><div className="nav-links"><button onClick={() => navigate("status")}>System status</button>{token ? <button className="btn small" onClick={() => navigate("dashboard")}>Dashboard <ArrowRight size={16}/></button> : <><button onClick={() => navigate("login")}>Sign in</button><button className="btn small" onClick={() => navigate("register")}>Get started <ArrowRight size={16}/></button></>}</div></nav>
    <section className="hero shell">
      <div className="eyebrow"><Sparkles size={15}/> Distributed by design</div>
      <h1>Small links.<br/><em>Serious infrastructure.</em></h1>
      <p>Create memorable short links, watch every click, and keep moving—even when a cache node doesn’t.</p>
      <div className="hero-actions"><button className="btn primary" onClick={() => navigate(token ? "dashboard" : "register")}>Shorten your first link <ArrowRight size={18}/></button><button className="btn ghost" onClick={() => navigate("status")}><Activity size={18}/> View live status</button></div>
      <div className="signal-card">
        <div className="signal-top"><span><span className="pulse"/> All systems operational</span><span className="mono">2 API nodes</span></div>
        <div className="flow"><div><strong>Client</strong><span>Your request</span></div><ArrowRight/><div><strong>Nginx</strong><span>Load balancer</span></div><ArrowRight/><div className="nodes"><strong>FastAPI</strong><span>api1 · api2</span></div><ArrowRight/><div><strong>Data</strong><span>Redis · Postgres</span></div></div>
      </div>
    </section>
    <section className="features shell"><article><Link2/><h3>Shorten instantly</h3><p>Turn long, unwieldy URLs into clean links ready to share anywhere.</p></article><article><BarChart3/><h3>Measure every click</h3><p>See engagement at a glance with accurate click analytics per link.</p></article><article><ShieldCheck/><h3>Built to stay up</h3><p>Traffic is balanced across replicas with graceful database fallback.</p></article></section>
  </main>;
}

function AuthPage({ mode, onSuccess, navigate }) {
  const register = mode === "register";
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError("");
    try { const data = await api(`/api/auth/${register ? "register" : "login"}`, { method: "POST", body: JSON.stringify(form) }); onSuccess(data.access_token); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  };
  return <main className="auth-page"><button className="back-brand" onClick={() => navigate("home")}><Brand/></button><section className="auth-card"><div className="eyebrow"><Zap size={14}/> {register ? "Join LinkFlux" : "Welcome back"}</div><h1>{register ? "Create your account" : "Sign in to your links"}</h1><p>{register ? "Start creating measurable links in seconds." : "Your links and analytics are waiting."}</p><form onSubmit={submit}><label>Email address<input type="email" required autoFocus value={form.email} onChange={(e) => setForm({...form, email:e.target.value})} placeholder="you@example.com"/></label><label>Password<input type="password" required minLength={register ? 8 : undefined} value={form.password} onChange={(e) => setForm({...form, password:e.target.value})} placeholder="At least 8 characters"/></label>{error && <div className="error">{error}</div>}<button className="btn primary full" disabled={busy}>{busy ? "Please wait…" : register ? "Create account" : "Sign in"}<ArrowRight size={18}/></button></form><div className="auth-switch">{register ? "Already have an account?" : "New to LinkFlux?"} <button onClick={() => navigate(register ? "login" : "register")}>{register ? "Sign in" : "Create account"}</button></div></section></main>;
}

function Dashboard({ navigate, logout }) {
  const [links, setLinks] = useState([]); const [stats, setStats] = useState({});
  const [url, setUrl] = useState(""); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const [copied, setCopied] = useState("");
  const load = useCallback(async () => { try { const data = await api("/api/urls"); setLinks(data); await Promise.all(data.map(async item => { const stat = await api(`/api/urls/${item.short_code}/stats`); setStats(prev => ({...prev,[item.short_code]:stat.total_clicks})); })); } catch (err) { setError(err.message); if (!auth.get()) logout(); } }, [logout]);
  useEffect(() => { load(); }, [load]);
  const create = async (event) => { event.preventDefault(); setBusy(true); setError(""); try { const item = await api("/api/urls", {method:"POST",body:JSON.stringify({url})}); setLinks(prev => [item,...prev]); setStats(prev => ({...prev,[item.short_code]:0})); setUrl(""); } catch(err){setError(err.message);} finally{setBusy(false);} };
  const remove = async (code) => { if (!confirm("Delete this short link? This cannot be undone.")) return; await api(`/api/urls/${code}`,{method:"DELETE"}); setLinks(prev => prev.filter(item => item.short_code !== code)); };
  const copy = async (item) => { await navigator.clipboard.writeText(item.short_url); setCopied(item.short_code); setTimeout(()=>setCopied(""),1800); };
  const clicks = useMemo(() => Object.values(stats).reduce((sum,n)=>sum+(n||0),0), [stats]);
  return <main className="app-shell"><AppNav navigate={navigate} logout={logout}/><section className="dashboard shell"><div className="page-head"><div><span className="kicker">LINK CONTROL</span><h1>Your links</h1><p>Create, share, and understand every short link.</p></div><div className="summary"><span><strong>{links.length}</strong> links</span><span><strong>{clicks}</strong> total clicks</span></div></div><form className="create-bar" onSubmit={create}><Link2/><input type="url" required value={url} onChange={e=>setUrl(e.target.value)} placeholder="Paste a long URL to shorten…"/><button className="btn primary" disabled={busy}><Plus size={18}/>{busy ? "Creating…" : "Create link"}</button></form>{error && <div className="error wide">{error}</div>}<div className="list-head"><h2>My Links</h2><button className="icon-text" onClick={load}><RefreshCw size={15}/> Refresh</button></div>{links.length === 0 ? <div className="empty"><div><Link2/></div><h3>No links yet</h3><p>Your first short link will appear here.</p></div> : <div className="link-list">{links.map(item => <article className="link-row" key={item.id}><div className="link-icon"><Link2/></div><div className="link-main"><a href={item.short_url} target="_blank" rel="noreferrer">{item.short_url.replace(/^https?:\/\//,"")} <ExternalLink size={14}/></a><span title={item.original_url}>{item.original_url}</span><small>{new Date(item.created_at).toLocaleDateString(undefined,{month:"short",day:"numeric",year:"numeric"})}</small></div><div className="click-count"><strong>{stats[item.short_code] ?? "—"}</strong><span>clicks</span></div><div className="row-actions"><button title="Copy" onClick={()=>copy(item)}>{copied===item.short_code?<Check size={18}/>:<Copy size={18}/>}</button><button className="danger" title="Delete" onClick={()=>remove(item.short_code)}><Trash2 size={18}/></button></div></article>)}</div>}</section></main>;
}

function AppNav({ navigate, logout, token=true }) { const [open,setOpen]=useState(false); return <nav className="nav app-nav shell"><button onClick={()=>navigate("home")}><Brand/></button><div className={open?"nav-links open":"nav-links"}>{token&&<button onClick={()=>navigate("dashboard")}>My Links</button>}<button onClick={()=>navigate("status")}>System status</button>{token&&<button className="logout" onClick={logout}><LogOut size={16}/> Sign out</button>}</div><button className="mobile-menu" onClick={()=>setOpen(!open)}>{open?<X/>:<Menu/>}</button></nav>; }

function StatusPage({ navigate, token, logout }) {
  const [health,setHealth]=useState(null); const [updated,setUpdated]=useState(null);
  const load=async()=>{try{const data=await api("/health/ready");setHealth(data);setUpdated(new Date());}catch{setHealth({status:"not_ready",postgres:false,redis:false});setUpdated(new Date());}};
  useEffect(()=>{load();const id=setInterval(load,15000);return()=>clearInterval(id);},[]);
  const good=health?.postgres; return <main className="app-shell"><AppNav navigate={navigate} logout={logout} token={token}/><section className="status-page shell"><div className="eyebrow"><Activity size={15}/> Live infrastructure</div><div className="status-title"><div><h1>System status</h1><p>Real-time health across the link delivery stack.</p></div><button className="btn ghost" onClick={load}><RefreshCw size={17}/> Refresh</button></div><div className={`overall ${good?"healthy":"down"}`}><div className="status-orb"><Check/></div><div><span>CURRENT STATUS</span><h2>{!health?"Checking systems…":health.status==="ready"?"All systems operational":health.status==="degraded"?"Operating in degraded mode":"Service disruption"}</h2></div><small>{updated?`Updated ${updated.toLocaleTimeString()}`:"Connecting…"}</small></div><div className="service-grid"><Service name="API Gateway" detail="Nginx load balancer" value={good}/><Service name="API Replicas" detail="api1 + api2" value={good}/><Service name="PostgreSQL" detail="Durable source of truth" value={health?.postgres}/><Service name="Redis" detail="Cache + rate limits" value={health?.redis}/></div><div className="metric-note"><Gauge/><div><h3>Operational telemetry</h3><p>Request rate, p95 latency, and HTTP error metrics are collected continuously through Prometheus and visualized in Grafana.</p></div><a href="http://localhost:3000/d/distributed-url-shortener/distributed-url-shortener" target="_blank" rel="noreferrer">Open Grafana <ExternalLink size={15}/></a></div></section></main>;
}

function Service({name,detail,value}) { return <article className="service"><div className={value?"service-icon ok":"service-icon wait"}>{value?<Check/>:<Activity/>}</div><div><h3>{name}</h3><p>{detail}</p></div><span className={value?"badge ok":"badge wait"}>{value?"Operational":"Unavailable"}</span></article>; }

export default App;
