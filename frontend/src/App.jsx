import React, { useEffect, useRef, useState } from 'react';
import { CandidateTable, Empty } from './components/CandidateTable';
import { BriefcaseBusiness, Users, ChartNoAxesCombined, UploadCloud, LogOut, Plus, Trash2, ShieldCheck } from 'lucide-react';
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export default function App() {
  const sessionVersion = useRef(0);
  const [connection, setConnection] = useState('loading');
  const [token, setToken] = useState(sessionStorage.getItem('hs_token') || '');
  const [email, setEmail] = useState(sessionStorage.getItem('hs_email') || '');
  const [password, setPassword] = useState('');
  const [register, setRegister] = useState(false);
  const [jobs, setJobs] = useState([]),
    [candidates, setCandidates] = useState([]),
    [stats, setStats] = useState({}),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  const [tab, setTab] = useState('overview'),
    [title, setTitle] = useState(''),
    [description, setDescription] = useState(''),
    [skills, setSkills] = useState(''),
    [selectedJob, setSelectedJob] = useState(''),
    [file, setFile] = useState(null);
  async function req(path, options = {}) {
    const headers = {
      ...(options.body instanceof FormData ? {} : {
        'Content-Type': 'application/json'
      }),
      ...(token ? {
        Authorization: `Bearer ${token}`
      } : {})
    };
    const requestSession = sessionVersion.current;
    const res = await fetch(API + path, {
      ...options,
      headers: {
        ...headers,
        ...options.headers
      }
    });
    const data = await res.json().catch(() => ({}));
    if (res.status === 401 && token && requestSession === sessionVersion.current) {
      logout();
      setError('Your session has expired. Please sign in again.');
      throw Error('Your session has expired. Please sign in again.');
    }
    if (!res.ok) throw Error(data.detail instanceof Array ? data.detail.map(x => x.msg).join(', ') : data.detail || 'Request failed');
    return data;
  }
  async function refresh() {
    const requestSession = sessionVersion.current;
    setConnection('loading');
    try {
      const [j, c, a] = await Promise.all([req('/jobs'), req('/candidates'), req('/analytics')]);
      if (requestSession !== sessionVersion.current) return;
      setJobs(j);
      setCandidates(c);
      setStats(a);
      setConnection('online');
      setSelectedJob(current => j.some(job => String(job.id) === current) ? current : j.length ? String(j[0].id) : '');
    } catch (e) {
      if (requestSession === sessionVersion.current) {
        setConnection('offline');
        setError(e.message);
      }
    }
  }
  useEffect(() => {
    if (token) refresh();
  }, [token]);
  async function auth(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      if (register) await req('/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          email,
          password
        })
      });
      const r = await req('/auth/login', {
        method: 'POST',
        body: JSON.stringify({
          email,
          password
        })
      });
      sessionVersion.current += 1;
      sessionStorage.setItem('hs_token', r.access_token);
      sessionStorage.setItem('hs_email', email.trim().toLowerCase());
      setEmail(email.trim().toLowerCase());
      setPassword('');
      setToken(r.access_token);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function addJob(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await req('/jobs', {
        method: 'POST',
        body: JSON.stringify({
          title,
          description,
          skills: skills.split(',').map(s => s.trim()).filter(Boolean)
        })
      });
      setTitle('');
      setDescription('');
      setSkills('');
      await refresh();
      setTab('jobs');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function upload(e) {
    e.preventDefault();
    const form = e.currentTarget;
    if (!file || !selectedJob) return;
    setBusy(true);
    setError('');
    try {
      const fd = new FormData();
      fd.append('job_id', selectedJob);
      fd.append('file', file);
      await req('/candidates/upload', {
        method: 'POST',
        body: fd
      });
      setFile(null);
      form.reset();
      await refresh();
      setTab('candidates');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function status(id, value) {
    try {
      await req('/candidates/' + id, {
        method: 'PATCH',
        body: JSON.stringify({
          status: value
        })
      });
      await refresh();
    } catch (e) {
      setError(e.message);
    }
  }
  async function removeJob(id) {
    if (!confirm('Delete this job and its candidates?')) return;
    try {
      await req('/jobs/' + id, {
        method: 'DELETE'
      });
      await refresh();
    } catch (e) {
      setError(e.message);
    }
  }
  function logout() {
    sessionVersion.current += 1;
    sessionStorage.removeItem('hs_token');
    sessionStorage.removeItem('hs_email');
    setToken('');
    setEmail('');
    setPassword('');
    setJobs([]);
    setCandidates([]);
    setStats({});
    setSelectedJob('');
    setFile(null);
    setTab('overview');
    setRegister(false);
    setError('');
    setConnection('loading');
  }
  if (!token) return <div className="auth-screen"><div className="auth-card"><div className="brand"><div className="brand-icon"><ShieldCheck size={25} /></div><span>Hire<span className="accent">Sense</span></span></div><div className="eyebrow">RECRUITMENT INTELLIGENCE</div><h1>{register ? 'Create your account' : 'Welcome back'}</h1><p>Compare resumes against job requirements with transparent skill matching.</p><form onSubmit={auth}><label>Work email<input type="email" required value={email} onChange={e => setEmail(e.target.value)} placeholder="recruiter@company.com" /></label><label>Password<input type="password" minLength="8" maxLength="72" required value={password} onChange={e => setPassword(e.target.value)} placeholder="Minimum 8 characters" /></label>{error && <div className="error">{error}</div>}<button className="primary" disabled={busy}>{busy ? 'Please wait...' : register ? 'Create account' : 'Sign in'}</button></form><button className="text-btn" onClick={() => {
        setRegister(!register);
        setError('');
      }}>{register ? 'Already have an account? Sign in' : 'New here? Create an account'}</button></div></div>;
  const nav = [['overview', ChartNoAxesCombined, 'Overview'], ['jobs', BriefcaseBusiness, 'Jobs'], ['candidates', Users, 'Candidates'], ['upload', UploadCloud, 'Upload resume']];
  return <div className="shell"><aside className="sidebar"><div className="brand"><div className="brand-icon"><ShieldCheck size={23} /></div><span>Hire<span className="accent">Sense</span></span></div><div className="nav-label">WORKSPACE</div>{nav.map(([key, Icon, name]) => <button key={key} className={'nav ' + (tab === key ? 'active' : '')} onClick={() => setTab(key)}><Icon size={18} />{name}</button>)}<div className="sidebar-bottom"><div className="user-email">{email || 'Recruiter workspace'}</div><button className="nav" onClick={logout}><LogOut size={18} />Sign out</button></div></aside><main><header><div><div className="eyebrow">TALENT ACQUISITION / WORKSPACE</div><h1>{{
              overview: 'Recruitment overview',
              jobs: 'Job openings',
              candidates: 'Candidate pipeline',
              upload: 'Screen a resume',
              'new-job': 'Create a job opening'
            }[tab]}</h1><p>Manage roles, evaluate skills, and make informed decisions.</p></div><span className={'pill ' + connection} role="status"><span className="dot" />{connection === 'online' ? 'Connected' : connection === 'offline' ? 'Connection unavailable' : 'Connecting...'}</span></header>{error && <div className="error">{error} <button aria-label="Dismiss error" onClick={() => setError('')}>×</button></div>}
 {tab === 'overview' && <><div className="stat-grid"><div className="stat"><div className="stat-head"><span>Open positions</span><BriefcaseBusiness size={19} /></div><strong>{jobs.length}</strong><small>Active job profiles</small></div><div className="stat"><div className="stat-head"><span>Resumes screened</span><Users size={19} /></div><strong>{stats.total_candidates || 0}</strong><small>Across all positions</small></div><div className="stat"><div className="stat-head"><span>Average match score</span><ChartNoAxesCombined size={19} /></div><strong>{stats.average_match_score || 0}%</strong><small>Skills overlap</small></div><div className="stat"><div className="stat-head"><span>Shortlisted</span><ShieldCheck size={19} /></div><strong>{stats.shortlisted || 0}</strong><small>For human review</small></div></div><div className="panel"><div className="panel-title"><div><h2>Top matching candidates</h2><p>Ranked by matching score</p></div><button className="secondary" onClick={() => setTab('candidates')}>View all</button></div><CandidateTable candidates={candidates.slice(0, 6)} jobs={jobs} status={status} /></div></>}
 {tab === 'jobs' && <><div className="panel"><div className="panel-title"><div><h2>Job openings</h2><p>Create roles with a clearly defined skill set.</p></div><button className="primary small" onClick={() => setTab('new-job')}><Plus size={16} />New job</button></div><div className="job-grid">{jobs.map(j => <div className="job" key={j.id}><div className="job-top"><div className="job-icon"><BriefcaseBusiness size={20} /></div><button className="icon-button" title="Delete job" onClick={() => removeJob(j.id)}><Trash2 size={17} /></button></div><h3>{j.title}</h3><p>{j.description}</p><div className="tags">{j.skills.map(s => <span key={s}>{s}</span>)}</div><small>{candidates.filter(c => c.job_id === j.id).length} candidates</small></div>)}</div>{!jobs.length && <Empty text="No jobs yet. Create your first opening." />}</div></>}
 {tab === 'new-job' && <div className="panel form-panel"><h2>Create a job opening</h2><form onSubmit={addJob}><label>Job title<input minLength="2" maxLength="200" value={title} onChange={e => setTitle(e.target.value)} required placeholder="Backend Python Developer" /></label><label>Job description<textarea value={description} onChange={e => setDescription(e.target.value)} required minLength="10" rows="4" placeholder="Describe the role and responsibilities" /></label><label>Required skills (comma separated)<input value={skills} onChange={e => setSkills(e.target.value)} required placeholder="python, fastapi, sql, docker" /></label><button className="primary" disabled={busy}>Create job</button></form></div>}
 {tab === 'candidates' && <div className="panel"><div className="panel-title"><div><h2>All candidates</h2><p>Review match scores and update candidate status.</p></div><button className="primary small" onClick={() => setTab('upload')}><UploadCloud size={16} />Upload</button></div><CandidateTable candidates={candidates} jobs={jobs} status={status} /></div>}
 {tab === 'upload' && <div className="panel form-panel"><h2>Upload a candidate resume</h2><p>Supports PDF, DOCX, or TXT (maximum 2 MB). Scores reflect explicit skill mentions only.</p><form onSubmit={upload}><label>Job opening<select required value={selectedJob} onChange={e => setSelectedJob(e.target.value)}><option value="">Select a job</option>{jobs.map(j => <option value={j.id} key={j.id}>{j.title}</option>)}</select></label><label>Resume file<input type="file" accept=".pdf,.docx,.txt" required onChange={e => setFile(e.target.files?.[0])} /></label><button className="primary" disabled={busy || !jobs.length}>{busy ? 'Analyzing...' : 'Analyze resume'}</button></form>{!jobs.length && <p>Create a job first to enable uploads.</p>}</div>}
 <footer>HireSense · Skills-based decision support only. Human review required; do not use as an automated hiring decision.</footer></main></div>;
}
