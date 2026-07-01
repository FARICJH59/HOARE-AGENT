/**
 * StatePanel — Sidebar showing live FSM event log, agent task runner,
 * and Hoare triple verifier.
 */
import React, { useState } from 'react'
import { usePipelineStore, FSM_STATE_COLORS } from '../store.js'

const S = {
  panel: {
    width: 340,
    minWidth: 340,
    background: '#161b22',
    borderLeft: '1px solid #30363d',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  header: {
    padding: '12px 16px',
    borderBottom: '1px solid #30363d',
    fontSize: 13,
    fontWeight: 700,
    color: '#e6edf3',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  dot: (online) => ({
    width: 8, height: 8, borderRadius: '50%',
    background: online ? '#3fb950' : '#f85149',
  }),
  section: {
    borderBottom: '1px solid #30363d',
    padding: '12px 16px',
  },
  label: {
    fontSize: 11,
    color: '#8b949e',
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  input: {
    width: '100%',
    background: '#0d1117',
    border: '1px solid #30363d',
    borderRadius: 6,
    color: '#e6edf3',
    padding: '6px 8px',
    fontSize: 12,
    marginBottom: 6,
    fontFamily: 'inherit',
    resize: 'vertical',
  },
  btn: (disabled) => ({
    background: disabled ? '#21262d' : '#1f6feb',
    color: disabled ? '#6e7681' : '#e6edf3',
    border: 'none',
    borderRadius: 6,
    padding: '6px 12px',
    fontSize: 12,
    cursor: disabled ? 'not-allowed' : 'pointer',
    width: '100%',
    fontWeight: 600,
  }),
  eventList: {
    flex: 1,
    overflowY: 'auto',
    padding: '8px 16px',
  },
  event: {
    fontSize: 11,
    padding: '4px 8px',
    marginBottom: 4,
    borderRadius: 4,
    borderLeft: '3px solid',
    background: '#0d1117',
    lineHeight: 1.6,
  },
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatusBadge({ state }) {
  const color = FSM_STATE_COLORS[state] ?? '#6e7681'
  return (
    <span style={{
      fontSize: 10,
      fontWeight: 700,
      color,
      background: `${color}22`,
      border: `1px solid ${color}44`,
      borderRadius: 4,
      padding: '1px 5px',
    }}>
      {state}
    </span>
  )
}

function AgentTaskPanel() {
  const { runAgentTask, schemas } = usePipelineStore()
  const [desc, setDesc]         = useState('Extract and normalise telemetry events')
  const [running, setRunning]   = useState(false)
  const [result,  setResult]    = useState(null)

  const schema = schemas[0] ?? 'TelemetryEvent'

  async function handleRun() {
    setRunning(true)
    setResult(null)
    const schemaJson = JSON.stringify({ name: schema })
    const r = await runAgentTask(desc, schemaJson)
    setResult(r)
    setRunning(false)
  }

  return (
    <div style={S.section}>
      <div style={S.label}>▶ Run Agent Task</div>
      <textarea
        style={{ ...S.input, height: 60 }}
        value={desc}
        onChange={(e) => setDesc(e.target.value)}
        placeholder="Task description…"
      />
      <button style={S.btn(running)} disabled={running} onClick={handleRun}>
        {running ? 'Running…' : 'Execute (Generate → Verify)'}
      </button>
      {result && (
        <div style={{
          marginTop: 8,
          padding: 8,
          borderRadius: 6,
          background: '#0d1117',
          border: `1px solid ${result.success ? '#238636' : '#da3633'}`,
          fontSize: 11,
        }}>
          <StatusBadge state={result.success ? 'COMMITTED' : 'BLOCKED'} />
          {' '}
          {result.success
            ? `Verified in ${result.iterations} iteration(s).`
            : `Failed: ${result.failure_reason}`}
          {result.proof?.counterexample && (
            <div style={{ color: '#f85149', marginTop: 4 }}>
              Counter-example: {result.proof.counterexample}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function VerifyPanel() {
  const { verifyTriple } = usePipelineStore()
  const [pre,  setPre]  = useState('n >= 0')
  const [post, setPost] = useState('n >= 0')
  const [prog, setProg] = useState('# identity')
  const [res,  setRes]  = useState(null)
  const [busy, setBusy] = useState(false)

  async function handleVerify() {
    setBusy(true)
    const r = await verifyTriple(pre, prog, post)
    setRes(r)
    setBusy(false)
  }

  return (
    <div style={S.section}>
      <div style={S.label}>🔍 Hoare Triple Verifier</div>
      <input style={S.input} value={pre}  onChange={(e) => setPre(e.target.value)}  placeholder="Pre-condition P" />
      <input style={S.input} value={post} onChange={(e) => setPost(e.target.value)} placeholder="Post-condition Q" />
      <textarea style={{ ...S.input, height: 48 }} value={prog} onChange={(e) => setProg(e.target.value)} placeholder="Program C" />
      <button style={S.btn(busy)} disabled={busy} onClick={handleVerify}>
        {busy ? 'Checking…' : 'Verify with Z3'}
      </button>
      {res && (
        <div style={{
          marginTop: 8,
          padding: 8,
          borderRadius: 6,
          background: '#0d1117',
          border: `1px solid ${res.verified ? '#238636' : '#da3633'}`,
          fontSize: 11,
        }}>
          <StatusBadge state={res.verdict} />
          {res.counterexample && (
            <div style={{ color: '#f85149', marginTop: 4 }}>
              Counter-example: {res.counterexample}
            </div>
          )}
          {res.error_detail && (
            <div style={{ color: '#8b949e', marginTop: 4 }}>{res.error_detail}</div>
          )}
        </div>
      )}
    </div>
  )
}

function EventLog() {
  const { fsmEvents } = usePipelineStore()

  return (
    <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      <div style={{ ...S.section, paddingBottom: 8 }}>
        <div style={S.label}>📋 Live FSM Event Log</div>
      </div>
      <div style={S.eventList}>
        {fsmEvents.length === 0 && (
          <div style={{ color: '#6e7681', fontSize: 12, textAlign: 'center', marginTop: 16 }}>
            No events yet — parse a payload or run an agent task.
          </div>
        )}
        {fsmEvents.map((ev, i) => {
          const color = FSM_STATE_COLORS[ev.state] ?? '#6e7681'
          return (
            <div key={i} style={{ ...S.event, borderLeftColor: color }}>
              <StatusBadge state={ev.state} />
              {' '}
              <span style={{ color: '#8b949e' }}>{ev.payload_id?.slice(0, 8)}</span>
              {ev.detail && (
                <div style={{ color: '#6e7681', marginTop: 2 }}>{ev.detail}</div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Main panel ────────────────────────────────────────────────────────────────
export default function StatePanel() {
  const { backendOnline } = usePipelineStore()

  return (
    <div style={S.panel}>
      <div style={S.header}>
        <div style={S.dot(backendOnline)} />
        Hoare-Agent Pipeline
        <span style={{ marginLeft: 'auto', fontSize: 10, color: '#6e7681' }}>
          {backendOnline ? 'Connected' : 'Offline'}
        </span>
      </div>

      <AgentTaskPanel />
      <VerifyPanel />
      <EventLog />
    </div>
  )
}
