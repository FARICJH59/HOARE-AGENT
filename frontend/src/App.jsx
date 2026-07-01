/**
 * App — Root component for the Hoare-Agent Dashboard.
 *
 * Layout:
 *   ┌─────────────────────────────────┬──────────────┐
 *   │      NodeMap (FSM graph)         │  StatePanel  │
 *   │      (React Flow)                │  (sidebar)   │
 *   └─────────────────────────────────┴──────────────┘
 *
 * A health-check poll runs every 3 s to keep the backend status fresh.
 */
import React, { useEffect } from 'react'
import NodeMap    from './components/NodeMap.jsx'
import StatePanel from './components/StatePanel.jsx'
import { usePipelineStore } from './store.js'

export default function App() {
  const checkHealth = usePipelineStore((s) => s.checkHealth)

  // Poll backend health every 3 seconds
  useEffect(() => {
    checkHealth()
    const id = setInterval(checkHealth, 3000)
    return () => clearInterval(id)
  }, [checkHealth])

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        position: 'absolute',
        top: 0, left: 0, right: 0,
        zIndex: 10,
        background: '#161b22',
        borderBottom: '1px solid #30363d',
        padding: '8px 16px',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        height: 44,
      }}>
        <span style={{ fontSize: 16, fontWeight: 700, color: '#e6edf3' }}>
          ⚡ Hoare-Agent
        </span>
        <span style={{ fontSize: 12, color: '#8b949e' }}>
          Self-Verifying Code Pipeline — AesirGrid Integration
        </span>
      </div>

      {/* Main layout (below header) */}
      <div style={{ display: 'flex', flex: 1, marginTop: 44, overflow: 'hidden' }}>
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <NodeMap />
        </div>
        <StatePanel />
      </div>
    </div>
  )
}
