import React, { useMemo } from 'react'
import { usePipelineStore, FSM_STATE_COLORS } from '../store.js'

const S = {
  panel: {
    width: 380,
    minWidth: 380,
    background: '#0d1117',
    borderLeft: '1px solid #30363d',
    display: 'flex',
    flexDirection: 'column',
    overflowY: 'auto',
  },
  title: {
    padding: '12px 16px',
    borderBottom: '1px solid #30363d',
    fontSize: 13,
    fontWeight: 700,
    color: '#e6edf3',
  },
  card: {
    margin: 12,
    padding: 12,
    border: '1px solid #30363d',
    borderRadius: 8,
    background: '#161b22',
  },
  label: {
    fontSize: 11,
    color: '#8b949e',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
}

function RepairLoopCard() {
  const latestTask = usePipelineStore((s) => s.agentTasks[0])
  const trace = latestTask?.repair_trace ?? []

  return (
    <div style={S.card}>
      <div style={S.label}>Agent Repair Loop</div>
      {trace.length === 0 && <div style={{ fontSize: 12, color: '#6e7681' }}>Run an agent task to visualize loop attempts.</div>}
      {trace.map((step) => {
        const color = step.verified ? '#238636' : '#da3633'
        return (
          <div key={step.attempt} style={{ marginBottom: 6, fontSize: 11, color: '#c9d1d9' }}>
            <span style={{ color, fontWeight: 700 }}>Attempt {step.attempt}</span> · {step.verdict} · {step.elapsed_ms} ms
            {step.counterexample && <div style={{ color: '#f85149' }}>Counterexample: {step.counterexample}</div>}
          </div>
        )
      })}
    </div>
  )
}

function ProofLogCard() {
  const latestTask = usePipelineStore((s) => s.agentTasks[0])
  const trace = latestTask?.repair_trace ?? []

  return (
    <div style={S.card}>
      <div style={S.label}>Proof Logs</div>
      {trace.length === 0 && <div style={{ fontSize: 12, color: '#6e7681' }}>No proof logs yet.</div>}
      {trace.map((step) => (
        <div key={`proof-${step.attempt}`} style={{ marginBottom: 8, fontSize: 11, color: '#8b949e' }}>
          #{step.attempt} → {step.verified ? 'VERIFIED' : 'FAILED'} ({step.verdict})
          {step.error_detail && <div style={{ color: '#f0883e' }}>{step.error_detail}</div>}
        </div>
      ))}
    </div>
  )
}

function SchemaRegistryCard() {
  const schemas = usePipelineStore((s) => s.schemas)

  return (
    <div style={S.card}>
      <div style={S.label}>Schema Registry</div>
      {schemas.map((schema) => (
        <div key={schema} style={{ fontSize: 12, color: '#c9d1d9', marginBottom: 6 }}>
          {schema}
        </div>
      ))}
      {schemas.length === 0 && <div style={{ fontSize: 12, color: '#6e7681' }}>No schemas loaded.</div>}
    </div>
  )
}

function FSMViewerCard() {
  const fsmEvents = usePipelineStore((s) => s.fsmEvents)
  const recentEvents = useMemo(() => fsmEvents.slice(0, 8), [fsmEvents])

  return (
    <div style={S.card}>
      <div style={S.label}>FSM Viewer</div>
      {recentEvents.map((ev, index) => {
        const color = FSM_STATE_COLORS[ev.state] ?? '#6e7681'
        return (
          <div key={`${ev.payload_id}-${index}`} style={{ fontSize: 11, color: '#c9d1d9', marginBottom: 6 }}>
            <span style={{ color, fontWeight: 700 }}>{ev.state}</span> · {ev.detail || 'Transition'}
          </div>
        )
      })}
      {recentEvents.length === 0 && <div style={{ fontSize: 12, color: '#6e7681' }}>No FSM events available.</div>}
    </div>
  )
}

function ConnectorCard() {
  const { connectors, validateConnector } = usePipelineStore()

  return (
    <div style={S.card}>
      <div style={S.label}>Ecosystem Connectors</div>
      {connectors.map((connector) => (
        <div key={connector.name} style={{ marginBottom: 8 }}>
          <div style={{ fontSize: 12, color: '#e6edf3', fontWeight: 600 }}>
            {connector.name} · {connector.ready ? 'Ready' : 'Needs setup'}
          </div>
          <div style={{ fontSize: 11, color: '#8b949e' }}>{connector.description}</div>
          <button
            style={{
              marginTop: 4,
              padding: '3px 8px',
              fontSize: 11,
              borderRadius: 6,
              border: '1px solid #30363d',
              background: '#0d1117',
              color: '#c9d1d9',
              cursor: 'pointer',
            }}
            onClick={() => validateConnector(connector.name)}
          >
            Validate
          </button>
        </div>
      ))}
      {connectors.length === 0 && <div style={{ fontSize: 12, color: '#6e7681' }}>No connector metadata available.</div>}
    </div>
  )
}

export default function TechFusionGrid() {
  return (
    <div style={S.panel}>
      <div style={S.title}>🧩 Tech Fusion Grid</div>
      <RepairLoopCard />
      <ProofLogCard />
      <SchemaRegistryCard />
      <FSMViewerCard />
      <ConnectorCard />
    </div>
  )
}
