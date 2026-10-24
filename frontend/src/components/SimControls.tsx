import { useState } from 'react'
import { Play, Pause, RotateCcw, StepForward } from 'lucide-react'
import { api, ApiError } from '../services/api'
import type { SimulationState } from '../types/api'
import { Pill } from './ui'

export function SimControls({ sim, onChange }: { sim?: SimulationState; onChange: () => void }) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const state = sim?.state ?? 'stopped'

  async function run(action: 'start' | 'pause' | 'resume' | 'reset' | 'step') {
    setBusy(true)
    setErr(null)
    try {
      await api.sim(action)
      onChange()
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : 'Action failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Simulation controls">
      <span aria-live="polite"><Pill tone={state === 'running' ? 'green' : state === 'paused' ? 'amber' : 'slate'}>Simulation {state}</Pill></span>
      {state === 'stopped' && <button className="btn btn-primary" disabled={busy} onClick={() => run('start')}><Play className="h-4 w-4" aria-hidden />Start</button>}
      {state === 'running' && <button className="btn" disabled={busy} onClick={() => run('pause')}><Pause className="h-4 w-4" aria-hidden />Pause</button>}
      {state === 'paused' && <button className="btn btn-primary" disabled={busy} onClick={() => run('resume')}><Play className="h-4 w-4" aria-hidden />Resume</button>}
      <button className="btn" disabled={busy} onClick={() => run('step')} title="Generate one tick of events"><StepForward className="h-4 w-4" aria-hidden />Step</button>
      <button className="btn" disabled={busy} onClick={() => run('reset')} title="Clear all events and restart from the seed"><RotateCcw className="h-4 w-4" aria-hidden />Reset</button>
      {err && <span role="alert" className="text-xs text-red-300">{err}</span>}
    </div>
  )
}
