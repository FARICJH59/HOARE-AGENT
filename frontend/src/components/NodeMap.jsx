/**
 * NodeMap — Real-time FSM pipeline visualisation.
 *
 * Renders the AesirGrid data-flow as an animated node graph where each
 * node's colour reflects the live FSM state of the most recent event
 * touching that pipeline stage.
 */
import React, { useCallback, useEffect, useMemo } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'

import { usePipelineStore, FSM_STATE_COLORS } from '../store.js'

// ── Node ID → FSM state mapping ──────────────────────────────────────────────
const NODE_FSM_MAP = {
  ingestion:    ['INGESTING'],
  micro_model:  ['PARSING'],
  pda:          ['VALIDATING', 'BLOCKED'],
  hoare_engine: ['VERIFYING'],
  schema_commit:['COMMITTING', 'COMMITTED'],
  dashboard:    ['COMMITTED'],
}

function stateForNode(nodeId, fsmEvents) {
  const relevant = NODE_FSM_MAP[nodeId] ?? []
  const latest = fsmEvents.find((e) => relevant.includes(e.state))
  return latest?.state ?? 'IDLE'
}

// ── Custom node component ─────────────────────────────────────────────────────
function PipelineNode({ data }) {
  const { label, fsmState } = data
  const color  = FSM_STATE_COLORS[fsmState] ?? FSM_STATE_COLORS.IDLE
  const pulse  = ['INGESTING', 'PARSING', 'VERIFYING', 'COMMITTING'].includes(fsmState)

  return (
    <div
      style={{
        background: '#161b22',
        border:     `2px solid ${color}`,
        borderRadius: 8,
        padding:    '10px 16px',
        minWidth:   160,
        textAlign:  'center',
        boxShadow:  pulse ? `0 0 12px ${color}88` : 'none',
        transition: 'box-shadow 0.4s ease, border-color 0.4s ease',
      }}
    >
      <div style={{ fontSize: 11, color, fontWeight: 700, marginBottom: 4 }}>
        {fsmState}
      </div>
      {label.split('\n').map((line, i) => (
        <div key={i} style={{ fontSize: 12, color: '#e6edf3', lineHeight: 1.5 }}>
          {line}
        </div>
      ))}
    </div>
  )
}

const nodeTypes = { pipeline: PipelineNode }

// ── Edge style ────────────────────────────────────────────────────────────────
const edgeDefaults = {
  type:   'smoothstep',
  style:  { stroke: '#30363d', strokeWidth: 2 },
  markerEnd: { type: MarkerType.ArrowClosed, color: '#30363d' },
  animated: true,
}

// ── NodeMap component ─────────────────────────────────────────────────────────
export default function NodeMap() {
  const { nodes: rawNodes, edges: rawEdges, fsmEvents } = usePipelineStore()

  const initialNodes = useMemo(
    () =>
      rawNodes.map((n) => ({
        id:       n.id,
        type:     'pipeline',
        position: { x: n.x, y: n.y },
        data:     { label: n.label, fsmState: 'IDLE' },
      })),
    [rawNodes]
  )

  const initialEdges = useMemo(
    () => rawEdges.map((e) => ({ ...e, ...edgeDefaults })),
    [rawEdges]
  )

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, , onEdgesChange]          = useEdgesState(initialEdges)

  // Re-colour nodes whenever fsmEvents updates
  useEffect(() => {
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: {
          ...n.data,
          fsmState: stateForNode(n.id, fsmEvents),
        },
      }))
    )
  }, [fsmEvents, setNodes])

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-right"
      >
        <Background color="#21262d" gap={20} />
        <Controls style={{ background: '#161b22', border: '1px solid #30363d' }} />
        <MiniMap
          nodeColor={(n) => FSM_STATE_COLORS[n.data?.fsmState] ?? '#6e7681'}
          style={{ background: '#0d1117', border: '1px solid #30363d' }}
        />
      </ReactFlow>
    </div>
  )
}
