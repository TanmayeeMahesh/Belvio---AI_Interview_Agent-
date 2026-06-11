import { useState, useEffect } from 'react'
import API from '../api'

const STATUS_ORDER = ['all', 'scheduled', 'in_progress', 'completed', 'incomplete', 'no_show', 'capped', 'stopped', 'error']

function badgeClass(status) {
  if (!status) return 'badge'
  const s = status.split('_')[0]  // "incomplete_no_response" → "incomplete"
  const map = { scheduled: 'badge-scheduled', in: 'badge-in_progress', completed: 'badge-completed',
                incomplete: 'badge-incomplete', no: 'badge-no_show', capped: 'badge-capped',
                stopped: 'badge-stopped', error: 'badge-error' }
  return `badge ${map[s] || 'badge-capped'}`
}

function StatusBadge({ status }) {
  return <span className={badgeClass(status)}>{status?.replace(/_/g, ' ') || '—'}</span>
}

function Modal({ title, onClose, children }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="flex-between" style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 600 }}>{title}</div>
          <button className="btn-ghost btn-sm" onClick={onClose}>✕</button>
        </div>
        {children}
      </div>
    </div>
  )
}

function PlanModal({ sessionId, onClose, token }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    API.get(`/api/hr/session/${sessionId}`, { headers: { authorization: `Bearer ${token}` } })
      .then(r => { setData(r.data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [sessionId])

  const questions = data?.questions || []

  return (
    <Modal title="Question Plan" onClose={onClose}>
      {loading && <div className="text-secondary text-sm">Loading…</div>}
      {!loading && questions.length === 0 && <div className="text-secondary text-sm">No questions found.</div>}
      {questions.map((q, i) => (
        <div key={i} style={{ padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
          <div className="flex-row" style={{ marginBottom: 4 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent)', minWidth: 24 }}>Q{i + 1}</span>
            <span className="badge badge-scheduled" style={{ fontSize: 11 }}>{q.topic || 'General'}</span>
          </div>
          <div style={{ fontSize: 14, paddingLeft: 24 }}>{q.question_text || q.question}</div>
          {q.key_concepts?.length > 0 && (
            <div className="text-xs text-secondary" style={{ paddingLeft: 24, marginTop: 4 }}>
              Concepts: {(q.key_concepts || []).join(', ')}
            </div>
          )}
        </div>
      ))}
    </Modal>
  )
}

export default function Sessions({ token, onViewReport }) {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [planFor, setPlanFor] = useState(null)
  const [reasonFor, setReasonFor] = useState(null)

  useEffect(() => { fetchSessions() }, [])

  async function fetchSessions() {
    setLoading(true); setError('')
    try {
      const { data } = await API.get('/api/hr/sessions', { headers: { authorization: `Bearer ${token}` } })
      setSessions(Array.isArray(data) ? data : [])
    } catch (e) {
      setError('Failed to load sessions.')
    }
    setLoading(false)
  }

  const filtered = sessions.filter(s => {
    if (statusFilter !== 'all' && !(s.status || '').startsWith(statusFilter)) return false
    if (search) {
      const q = search.toLowerCase()
      return (s.candidate_name || '').toLowerCase().includes(q) || (s.role || '').toLowerCase().includes(q)
    }
    return true
  })

  function formatDate(iso) {
    if (!iso) return '—'
    return new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
  }

  return (
    <div className="page">
      <div className="flex-between" style={{ marginBottom: 20 }}>
        <div className="page-title" style={{ marginBottom: 0 }}>Sessions</div>
        <button className="btn-ghost btn-sm" onClick={fetchSessions}>↻ Refresh</button>
      </div>

      {/* Filters */}
      <div className="card" style={{ padding: '10px 14px', marginBottom: 16, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 200px' }}>
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search name or role…" style={{ height: 34 }} />
        </div>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} style={{ width: 'auto', height: 34 }}>
          {STATUS_ORDER.map(s => <option key={s} value={s}>{s === 'all' ? 'All statuses' : s.replace(/_/g, ' ')}</option>)}
        </select>
      </div>

      {error && <div className="text-danger text-sm" style={{ marginBottom: 12 }}>{error}</div>}

      <div className="card">
        {loading ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-secondary)' }}>Loading…</div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-secondary)' }}>
            {sessions.length === 0 ? 'No sessions yet.' : 'No sessions match the filter.'}
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Candidate</th>
                <th>Role</th>
                <th>Status</th>
                <th>Scheduled At</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(s => (
                <tr key={s.id}>
                  <td>
                    <div className="font-semibold">{s.candidate_name || '—'}</div>
                    {s.candidate_email && <div className="text-xs text-secondary">{s.candidate_email}</div>}
                  </td>
                  <td className="text-secondary">{s.role || '—'}</td>
                  <td><StatusBadge status={s.status} /></td>
                  <td className="text-secondary text-sm">{formatDate(s.scheduled_at || s.created_at)}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                      <button className="btn-ghost btn-sm" onClick={() => setPlanFor(s.id)}>Plan</button>
                      {s.status && s.status !== 'scheduled' && (
                        <button className="btn-ghost btn-sm" onClick={() => setReasonFor(s)}>Reason</button>
                      )}
                      {(s.recommendation || s.overall_score != null) && (
                        <button className="btn-primary btn-sm" onClick={() => onViewReport(s.id)}>Report</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Plan modal */}
      {planFor && <PlanModal sessionId={planFor} token={token} onClose={() => setPlanFor(null)} />}

      {/* Reason modal */}
      {reasonFor && (
        <Modal title="Session Reason" onClose={() => setReasonFor(null)}>
          <div className="gap-12" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <div className="text-xs text-secondary">Candidate</div>
              <div>{reasonFor.candidate_name || '—'}</div>
            </div>
            <div>
              <div className="text-xs text-secondary">Status</div>
              <StatusBadge status={reasonFor.status} />
            </div>
            <div>
              <div className="text-xs text-secondary">Questions answered</div>
              <div>{reasonFor.questions_answered ?? reasonFor.question_count ?? '—'}</div>
            </div>
            {reasonFor.completion_reason && (
              <div>
                <div className="text-xs text-secondary">Completion reason</div>
                <div className="text-sm">{reasonFor.completion_reason}</div>
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  )
}
