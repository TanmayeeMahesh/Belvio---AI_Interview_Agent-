import { useState, useEffect } from 'react'
import API from '../api'

const DIM_LABELS = {
  technical_accuracy:    'Technical Accuracy',
  depth:                 'Depth',
  clarity_communication: 'Clarity & Communication',
  problem_solving:       'Problem Solving',
}

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString([], { month: 'short', day: 'numeric', year: '2-digit' })
}

function ScoreBar({ value, max = 10 }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  const color = pct >= 70 ? '#10b981' : pct >= 50 ? '#f59e0b' : '#ef4444'
  return (
    <div className="score-bar-track" style={{ marginTop: 6 }}>
      <div className="score-bar-fill" style={{ width: `${pct}%`, background: color }} />
    </div>
  )
}

function ScoreCard({ label, value }) {
  return (
    <div className="card" style={{ padding: '14px 16px' }}>
      <div className="text-xs text-secondary">{label}</div>
      <div style={{ fontSize: 26, fontWeight: 700, marginTop: 4 }}>
        {value != null ? value.toFixed(1) : '—'}
        <span className="text-secondary" style={{ fontSize: 14, fontWeight: 400 }}>/10</span>
      </div>
      {value != null && <ScoreBar value={value} />}
    </div>
  )
}

function RecommendationBadge({ rec }) {
  if (!rec) return null
  const base = rec.replace(/ \(Incomplete Session\)$/, '')
  const styles = {
    'Strongly Recommended': { bg: '#ecfdf5', color: '#059669' },
    'Recommended':           { bg: '#eff6ff', color: '#3b82f6' },
    'Needs Further Review':  { bg: '#fffbeb', color: '#d97706' },
    'Not Recommended':       { bg: '#fef2f2', color: '#dc2626' },
  }
  const s = styles[base] || { bg: '#f3f4f6', color: '#6b7280' }
  return (
    <span style={{ display: 'inline-block', padding: '4px 14px', borderRadius: 999, fontWeight: 600, fontSize: 13, background: s.bg, color: s.color }}>
      {rec}
    </span>
  )
}

function RecommendationChip({ rec }) {
  if (!rec) return <span className="text-secondary">—</span>
  const base = rec.replace(/ \(Incomplete Session\)$/, '')
  const styles = {
    'Strongly Recommended': { bg: '#ecfdf5', color: '#059669' },
    'Recommended':           { bg: '#eff6ff', color: '#3b82f6' },
    'Needs Further Review':  { bg: '#fffbeb', color: '#d97706' },
    'Not Recommended':       { bg: '#fef2f2', color: '#dc2626' },
  }
  const s = styles[base] || { bg: '#f3f4f6', color: '#6b7280' }
  return (
    <span style={{ display: 'inline-block', padding: '2px 10px', borderRadius: 999, fontWeight: 500, fontSize: 12, background: s.bg, color: s.color }}>
      {base}
    </span>
  )
}

function NarrativeSection({ title, text }) {
  if (!text) return null
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>{title}</div>
      <div className="text-sm" style={{ lineHeight: 1.7 }}>{text}</div>
    </div>
  )
}

export default function Reports({ token, defaultSessionId }) {
  const [sessions, setSessions] = useState([])
  const [selectedId, setSelectedId] = useState('')
  const [fullData, setFullData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showTranscript, setShowTranscript] = useState(false)
  const [sortBy, setSortBy] = useState('date-desc')

  useEffect(() => {
    API.get('/api/hr/sessions', { headers: { authorization: `Bearer ${token}` } })
      .then(r => setSessions(Array.isArray(r.data) ? r.data : []))
      .catch(() => {})
  }, [])

  // Open from Sessions tab "Report" button
  useEffect(() => {
    if (defaultSessionId) openReport(defaultSessionId)
  }, [defaultSessionId])

  function openReport(id) {
    setSelectedId(id)
    setFullData(null)
    setShowTranscript(false)
    setError('')
    fetchSession(id)
  }

  function goBack() {
    setSelectedId('')
    setFullData(null)
    setShowTranscript(false)
    setError('')
  }

  async function fetchSession(id) {
    setLoading(true); setError('')
    try {
      const { data } = await API.get(`/api/hr/session/${id}`, { headers: { authorization: `Bearer ${token}` } })
      setFullData(data)
    } catch (e) {
      setError(e.response?.status === 404 ? 'Session not found.' : 'Failed to load report.')
    }
    setLoading(false)
  }

  async function downloadPdf(id) {
    try {
      const res = await API.get(`/api/hr/report/${id}/pdf`, {
        headers: { authorization: `Bearer ${token}` },
        responseType: 'blob',
      })
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url; a.download = `report_${id.slice(0, 8)}.pdf`
      a.click(); URL.revokeObjectURL(url)
    } catch (e) {
      alert('PDF download failed. Check server logs.')
    }
  }

  const sessionsWithReports = sessions
    .filter(s => s.recommendation || s.overall_score != null)
    .sort((a, b) => {
      if (sortBy === 'date-asc') return new Date(a.scheduled_at || a.created_at || 0) - new Date(b.scheduled_at || b.created_at || 0)
      if (sortBy === 'role') return (a.role || '').localeCompare(b.role || '')
      if (sortBy === 'score') return (b.overall_score ?? -1) - (a.overall_score ?? -1)
      return new Date(b.scheduled_at || b.created_at || 0) - new Date(a.scheduled_at || a.created_at || 0)
    })

  const r = fullData?.report || {}
  const sess = fullData?.session || {}
  const answers = fullData?.answers || []
  const perTopic = r.per_topic || []
  const candidateName = sess.candidate_name || sessions.find(s => s.id === selectedId)?.candidate_name || '—'
  const candidateRole = sess.role || sessions.find(s => s.id === selectedId)?.role || '—'

  // ── Session list view ──
  if (!selectedId) {
    return (
      <div className="page">
        <div className="flex-between" style={{ marginBottom: 20 }}>
          <div className="page-title" style={{ marginBottom: 0 }}>Reports</div>
          <select value={sortBy} onChange={e => setSortBy(e.target.value)} style={{ width: 'auto' }}>
            <option value="date-desc">Newest first</option>
            <option value="date-asc">Oldest first</option>
            <option value="role">By role</option>
            <option value="score">By score</option>
          </select>
        </div>

        {sessionsWithReports.length === 0 ? (
          <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)' }}>
            No completed reports yet.
          </div>
        ) : (
          <div className="card">
            <table>
              <thead>
                <tr>
                  <th>Candidate</th>
                  <th>Role</th>
                  <th>Date</th>
                  <th>Score</th>
                  <th>Result</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {sessionsWithReports.map(s => (
                  <tr key={s.id}>
                    <td>
                      <div className="font-semibold">{s.candidate_name || '—'}</div>
                      {s.candidate_email && <div className="text-xs text-secondary">{s.candidate_email}</div>}
                    </td>
                    <td className="text-secondary">{s.role || '—'}</td>
                    <td className="text-secondary text-sm">{fmtDate(s.scheduled_at || s.created_at)}</td>
                    <td>
                      {s.overall_score != null
                        ? <span className="font-semibold">{s.overall_score.toFixed(1)}<span className="text-secondary" style={{ fontWeight: 400, fontSize: 12 }}>/10</span></span>
                        : <span className="text-secondary">—</span>}
                    </td>
                    <td><RecommendationChip rec={s.recommendation} /></td>
                    <td>
                      <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                        <button className="btn-primary btn-sm" onClick={() => openReport(s.id)}>Preview</button>
                        <button className="btn-ghost btn-sm" onClick={() => downloadPdf(s.id)}>⬇ PDF</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    )
  }

  // ── Report detail view ──
  return (
    <div className="page">
      <div className="flex-between" style={{ marginBottom: 20 }}>
        <button className="btn-ghost btn-sm" onClick={goBack}>← Back to reports</button>
        {fullData?.report && (
          <button className="btn-primary btn-sm" onClick={() => downloadPdf(selectedId)}>⬇ Download PDF</button>
        )}
      </div>

      {loading && <div style={{ textAlign: 'center', padding: 48, color: 'var(--text-secondary)' }}>Loading…</div>}
      {error && <div className="text-danger text-sm">{error}</div>}

      {fullData && !fullData.report && (
        <div className="card" style={{ padding: 24, textAlign: 'center', color: 'var(--text-secondary)' }}>
          Report not yet generated — interview may still be in progress or pending evaluation.
        </div>
      )}

      {fullData?.report && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

          {/* Header */}
          <div className="card" style={{ padding: 20 }}>
            <div className="flex-between" style={{ flexWrap: 'wrap', gap: 12 }}>
              <div>
                <div style={{ fontSize: 18, fontWeight: 700 }}>{candidateName}</div>
                <div className="text-secondary text-sm">{candidateRole}</div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <div style={{ textAlign: 'right' }}>
                  <div className="text-xs text-secondary">Overall Score</div>
                  <div style={{ fontSize: 32, fontWeight: 700, lineHeight: 1 }}>
                    {r.overall_score != null ? r.overall_score.toFixed(1) : '—'}
                    <span className="text-secondary" style={{ fontSize: 16, fontWeight: 400 }}>/10</span>
                  </div>
                </div>
                <RecommendationBadge rec={r.recommendation} />
              </div>
            </div>
            {r.executive_summary && (
              <div style={{ marginTop: 14, padding: '10px 14px', background: 'var(--bg)', borderRadius: 'var(--radius)', fontSize: 14, lineHeight: 1.6 }}>
                {r.executive_summary}
              </div>
            )}
          </div>

          {/* Dimension scores */}
          <div>
            <div style={{ fontWeight: 600, marginBottom: 12 }}>Dimension Scores</div>
            <div className="grid-4">
              {Object.entries(DIM_LABELS).map(([key, label]) => (
                <ScoreCard key={key} label={label} value={r[key]} />
              ))}
            </div>
          </div>

          {/* Narrative */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ fontWeight: 600, marginBottom: 14 }}>Evaluation</div>
            <NarrativeSection title="Strengths" text={r.strengths} />
            <NarrativeSection title="Gaps" text={r.gaps} />
            <NarrativeSection title="Justification" text={r.justification} />
          </div>

          {/* Per-topic breakdown */}
          {perTopic.length > 0 && (
            <div className="card" style={{ overflowX: 'auto' }}>
              <div style={{ padding: '14px 16px 10px', fontWeight: 600 }}>Per-Topic Breakdown</div>
              <table>
                <thead>
                  <tr>
                    <th>Topic</th>
                    <th>Score</th>
                    <th>Technical</th>
                    <th>Depth</th>
                    <th>Clarity</th>
                    <th>Problem Solving</th>
                    <th>Answered</th>
                  </tr>
                </thead>
                <tbody>
                  {perTopic.map((t, i) => (
                    <tr key={i}>
                      <td>{t.topic}</td>
                      <td style={{ fontWeight: 600 }}>{t.topic_score?.toFixed(1) ?? '—'}</td>
                      <td>{t.technical_accuracy ?? '—'}</td>
                      <td>{t.depth ?? '—'}</td>
                      <td>{t.clarity_communication ?? '—'}</td>
                      <td>{t.problem_solving ?? '—'}</td>
                      <td>
                        {t.answered === false
                          ? <span className="badge badge-incomplete">No</span>
                          : <span className="badge badge-completed">Yes</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {perTopic.some(t => t.note) && (
                <div style={{ padding: '0 16px 16px' }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8, marginTop: 16 }}>Evaluator Notes</div>
                  {perTopic.filter(t => t.note).map((t, i) => (
                    <div key={i} style={{ fontSize: 13, marginBottom: 6 }}>
                      <span style={{ fontWeight: 500 }}>{t.topic}:</span> <span className="text-secondary">{t.note}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Paired transcript */}
          <div className="card" style={{ padding: 20 }}>
            <button
              className="btn-ghost"
              onClick={() => setShowTranscript(v => !v)}
              style={{ width: '100%', textAlign: 'left', fontWeight: 600, border: 'none', background: 'none' }}
            >
              {showTranscript ? '▾' : '▸'} Transcript ({answers.length} exchanges)
            </button>
            {showTranscript && (
              answers.length === 0
                ? <div className="text-secondary text-sm" style={{ marginTop: 12 }}>No transcript available.</div>
                : <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 16 }}>
                    {answers.map((pair, i) => (
                      <div key={i} style={{ borderBottom: i < answers.length - 1 ? '1px solid var(--border)' : 'none', paddingBottom: 14 }}>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 8 }}>
                          <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--accent)', minWidth: 60 }}>
                            Q{i + 1} {pair.topic ? `· ${pair.topic}` : ''}
                          </span>
                          {pair.overall_score != null && (
                            <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                              score: {pair.overall_score.toFixed(1)}/10
                            </span>
                          )}
                        </div>
                        {pair.question_text && (
                          <div style={{ marginBottom: 6 }}>
                            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent)' }}>AI: </span>
                            <span className="text-sm">{pair.question_text}</span>
                          </div>
                        )}
                        {pair.answer_text && (
                          <div style={{ marginBottom: pair.evaluation_note ? 4 : 0 }}>
                            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>Candidate: </span>
                            <span className="text-sm">{pair.answer_text}</span>
                          </div>
                        )}
                        {pair.evaluation_note && (
                          <div className="text-xs text-secondary" style={{ marginTop: 4, fontStyle: 'italic' }}>{pair.evaluation_note}</div>
                        )}
                      </div>
                    ))}
                  </div>
            )}
          </div>

        </div>
      )}
    </div>
  )
}
