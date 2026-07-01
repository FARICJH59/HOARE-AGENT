/**
 * usePipelineStore — Zustand store for real-time FSM state.
 *
 * Polls the backend /health + /parse endpoints and accumulates FSM
 * state transitions so the node-map can react live.
 */
import { create } from 'zustand'
import axios from 'axios'

const API = '/api'
const apiClient = axios.create({ baseURL: API })

apiClient.interceptors.request.use((config) => {
  const apiKey = localStorage.getItem('hoareApiKey')
  if (apiKey) {
    config.headers['x-api-key'] = apiKey
  }
  return config
})

export const FSM_STATE_COLORS = {
  IDLE:       '#6e7681',
  INGESTING:  '#1f6feb',
  PARSING:    '#388bfd',
  VALIDATING: '#d29922',
  VERIFYING:  '#a371f7',
  COMMITTING: '#3fb950',
  COMMITTED:  '#238636',
  BLOCKED:    '#da3633',
  ERROR:      '#f85149',
}

const INITIAL_NODES = [
  { id: 'ingestion',   label: 'Ingestion Layer\n(NVIDIA Triton / gRPC)', x: 400, y:  40 },
  { id: 'micro_model', label: 'Ultra-Fast Micro-Model\n(Structural Parsing)',  x: 150, y: 200 },
  { id: 'hoare_engine',label: 'Hoare Verification Engine\n(Z3 Prover)',         x: 650, y: 200 },
  { id: 'pda',         label: 'PDA / Grammar Engine\n(Constrained Generation)', x: 150, y: 360 },
  { id: 'schema_commit',label:'Deterministic Schema Commit\n(Azure / BigQuery)', x: 400, y: 360 },
  { id: 'dashboard',   label: 'Reactive Dashboard\n(FSM Node Map)',              x: 650, y: 360 },
]

const EDGES = [
  { id: 'e1', source: 'ingestion',    target: 'micro_model'  },
  { id: 'e2', source: 'ingestion',    target: 'hoare_engine' },
  { id: 'e3', source: 'micro_model',  target: 'pda'          },
  { id: 'e4', source: 'pda',          target: 'schema_commit'},
  { id: 'e5', source: 'hoare_engine', target: 'schema_commit'},
  { id: 'e6', source: 'schema_commit',target: 'dashboard'    },
]

export const usePipelineStore = create((set, get) => ({
  // ── State ──────────────────────────────────────────────────────────────
  nodes: INITIAL_NODES,
  edges: EDGES,
  fsmEvents:   [],        // [{payload_id, state, detail, timestamp}]
  agentTasks:  [],        // [{task_id, success, iterations, …}]
  backendOnline: false,
  schemas: [],
  apiKey: localStorage.getItem('hoareApiKey') ?? '',
  usageSummary: null,
  auditSummary: null,

  // ── Actions ────────────────────────────────────────────────────────────
  checkHealth: async () => {
    try {
      await axios.get(`${API}/health`, { timeout: 2000 })
      if (!get().backendOnline) {
        set({ backendOnline: true })
        get().fetchSchemas()
        get().fetchUsage()
        get().fetchAuditSummary()
      }
    } catch {
      set({ backendOnline: false })
    }
  },

  setApiKey: (apiKey) => {
    localStorage.setItem('hoareApiKey', apiKey)
    set({ apiKey })
  },

  fetchSchemas: async () => {
    try {
      const res = await apiClient.get(`/schemas`)
      set({ schemas: res.data })
    } catch { /* ignore */ }
  },

  fetchUsage: async () => {
    try {
      const res = await apiClient.get('/usage/me')
      set({ usageSummary: res.data })
    } catch {
      set({ usageSummary: null })
    }
  },

  fetchAuditSummary: async () => {
    try {
      const res = await apiClient.get('/audit/summary')
      set({ auditSummary: res.data })
    } catch {
      set({ auditSummary: null })
    }
  },

  parsePayload: async (sourceName, rawData, schema = 'TelemetryEvent') => {
    const payload = {
      source_name: sourceName,
      raw_data:    rawData,
      metadata:    { schema },
    }
    try {
      const res = await apiClient.post(`/parse`, payload)
      const rec = res.data
      set((s) => ({
        fsmEvents: [
          { ...rec.fsm_state, payload_id: rec.payload_id },
          ...s.fsmEvents,
        ].slice(0, 100),
      }))
      return rec
    } catch (err) {
      return { valid: false, error: String(err) }
    }
  },

  runAgentTask: async (description, schemaJson) => {
    try {
      const res = await apiClient.post(`/agent/run`, {
        description,
        target_schema: schemaJson,
        max_retries: 3,
      })
      const { result, fsm_states } = res.data
      set((s) => ({
        agentTasks: [result, ...s.agentTasks].slice(0, 50),
        fsmEvents:  [...fsm_states, ...s.fsmEvents].slice(0, 100),
      }))
      return result
    } catch (err) {
      return { success: false, failure_reason: String(err) }
    }
  },

  verifyTriple: async (precondition, program, postcondition, loopInvariants = []) => {
    try {
      const res = await apiClient.post(`/verify`, {
        triple: { precondition, program, postcondition, loop_invariants: loopInvariants },
      })
      return res.data
    } catch (err) {
      return { verified: false, error_detail: String(err) }
    }
  },
}))
