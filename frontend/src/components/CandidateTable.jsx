import React from 'react';
import { FileText } from 'lucide-react';
export function Empty({
  text
}) {
  return <div className="empty"><FileText size={30} /><p>{text}</p></div>;
}
export function CandidateTable({
  candidates,
  jobs,
  status
}) {
  if (!candidates.length) return <Empty text="No candidates yet. Upload a resume to begin." />;
  return <div className="table-wrap"><table><thead><tr><th>Resume</th><th>Job</th><th>Match</th><th>Matched skills</th><th>Missing skills</th><th>Status</th></tr></thead><tbody>{candidates.map(c => <tr key={c.id}><td><strong>{c.filename}</strong></td><td>{jobs.find(j => j.id === c.job_id)?.title || '—'}</td><td><span className={'score ' + (c.score >= 70 ? 'good' : '')}>{c.score}%</span></td><td>{c.matched_skills.join(', ') || '—'}</td><td>{c.missing_skills.join(', ') || '—'}</td><td><select aria-label={"Status for " + c.filename} className="status" value={c.status} onChange={e => status(c.id, e.target.value)}>{['New', 'Review', 'Shortlisted', 'Rejected'].map(s => <option key={s}>{s}</option>)}</select></td></tr>)}</tbody></table></div>;
}
