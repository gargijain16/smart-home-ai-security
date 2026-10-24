import { useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { api } from '../services/api'
import type { ApiError } from '../services/api'
import type { Overview } from '../types/api'
import { useApi } from '../hooks/useApi'
import { DetailWindow } from '../components/DetailWindow'
import { FloorPlan } from '../components/FloorPlan'
import { SimControls } from '../components/SimControls'
import { Banner, Empty, ErrorState, Panel, Pill, deviceIcon, deviceTone, severityTone } from '../components/ui'
import { clock, labelName, timeAgo } from '../services/format'

export function DevicesPage({ overview, error, reload }: { overview: Overview | null; error: ApiError | null; reload: () => void }) {
  const [selected, setSelected] = useState<string | null>(null)
  const history = useApi(() => (selected ? api.deviceEvents(selected) : Promise.resolve(null)), [selected], selected ? 2500 : 0)
  if (error && !overview) return <ErrorState error={error} onRetry={reload} />
  if (!overview) return <p className="p-6 text-sm text-slate-400">Loading devices…</p>
  const devices = overview.device_health
  const sel = devices.find((d) => d.id === selected) ?? null

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-extrabold text-white">Smart home devices</h2>
          <p className="text-sm text-slate-400">Select a device on the plan or in the list to inspect its event history</p>
        </div>
        <SimControls sim={overview.simulation} onChange={reload} />
      </div>
      <Banner tone="cyan" title="Virtual devices">These devices and their activity are simulated. No physical device or live MQTT broker is connected.</Banner>
      <Panel title="Floor plan"><FloorPlan devices={devices} selectedId={selected} onSelect={setSelected} /></Panel>

      <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {devices.map((d) => {
          const Icon = deviceIcon(d.type)
          return (
            <li key={d.id}>
              <button onClick={() => setSelected(d.id)} aria-pressed={selected === d.id}
                className={`glass w-full rounded-2xl p-4 text-left transition-colors hover:border-cyan-400/40 ${selected === d.id ? 'ring-2 ring-cyan-400/60' : ''}`}>
                <div className="flex items-start justify-between gap-2">
                  <span className="flex items-center gap-3"><span className="grid h-9 w-9 place-items-center rounded-lg bg-slate-700/50"><Icon className="h-4 w-4 text-cyan-300" aria-hidden /></span>
                    <span><span className="block text-sm font-bold text-white">{d.name}</span><span className="text-xs text-slate-400">{d.type} · {d.room}</span></span></span>
                  <Pill tone={deviceTone(d.status)}>{d.status}</Pill>
                </div>
                <dl className="mt-3 grid grid-cols-3 gap-2 text-xs">
                  <div><dt className="text-slate-500">Protocol</dt><dd className="text-slate-200">{d.protocol}</dd></div>
                  <div><dt className="text-slate-500">Last activity</dt><dd className="text-slate-200">{timeAgo(d.last_activity)}</dd></div>
                  <div><dt className="text-slate-500">Open alerts</dt><dd className={d.open_alerts ? 'font-bold text-red-300' : 'text-slate-200'}>{d.open_alerts}</dd></div>
                </dl>
              </button>
            </li>
          )
        })}
      </ul>

      <AnimatePresence>
        {sel && (
          <DetailWindow key={sel.id} title={sel.name} subtitle={`${sel.id} · ${sel.type} · ${sel.protocol}`} onClose={() => setSelected(null)}>
            <div className="mb-3 flex flex-wrap gap-2"><Pill tone={deviceTone(sel.status)}>{sel.status}</Pill><Pill tone="slate">{sel.total_events} events</Pill><Pill tone={sel.open_alerts ? 'red' : 'green'}>{sel.open_alerts} open alerts</Pill></div>
            {history.error && <p role="alert" className="text-sm text-red-300">{history.error.message}</p>}
            {history.data && history.data.items.length === 0 && <Empty title="No events for this device yet" />}
            <ol className="space-y-2">
              {history.data?.items.map((e) => (
                <li key={e.id} className="rounded-lg border border-slate-700/50 p-2 text-sm">
                  <div className="flex items-center justify-between gap-2"><span className="font-semibold text-slate-200">{e.event_type.replace(/_/g, ' ')}</span><Pill tone={severityTone(e.severity)}>{labelName(e.label)}</Pill></div>
                  <p className="mt-1 text-xs text-slate-400">{clock(e.ts)} · from {e.source_ip} · <span className="break-all">{e.topic}</span></p>
                </li>
              ))}
            </ol>
          </DetailWindow>
        )}
      </AnimatePresence>
    </>
  )
}
