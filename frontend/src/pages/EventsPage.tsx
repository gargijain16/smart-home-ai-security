import { useDeferredValue, useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { api } from '../services/api'
import type { Device, EventStatus, SecEvent } from '../types/api'
import { useApi } from '../hooks/useApi'
import { DetailWindow } from '../components/DetailWindow'
import { Banner, Empty, ErrorState, Panel, Pill, severityTone } from '../components/ui'
import { clock, labelName, num } from '../services/format'

const LIMIT = 25
const TYPES = ['heartbeat', 'publish', 'mqtt_connect', 'auth_failure', 'wildcard_subscribe']
const LABELS = ['normal', 'brute_force', 'connection_burst', 'publish_flood', 'topic_enumeration']
const iso = (v: string) => (v ? new Date(v).toISOString() : '')

export function EventsPage({ devices }: { devices: Device[] }) {
  const [f, setF] = useState({ q: '', device_id: '', event_type: '', label: '', severity: '', status: '', since: '', until: '' })
  const [offset, setOffset] = useState(0)
  const [open, setOpen] = useState<SecEvent | null>(null)
  const q = useDeferredValue(f.q)
  const params = { ...f, q, since: iso(f.since), until: iso(f.until), limit: LIMIT, offset }
  const res = useApi(() => api.events(params), [JSON.stringify(params)], 3000)
  const set = (k: keyof typeof f) => (v: string) => { setOffset(0); setF((p) => ({ ...p, [k]: v })) }

  async function changeStatus(ev: SecEvent, status: EventStatus) {
    const updated = await api.setEventStatus(ev.id, status)
    setOpen(updated)
    void res.reload()
  }

  const Select = ({ k, label, options }: { k: keyof typeof f; label: string; options: { v: string; t: string }[] }) => (
    <label className="text-xs text-slate-400">{label}
      <select className="field mt-1 w-full" value={f[k]} onChange={(e) => set(k)(e.target.value)}>
        <option value="">All</option>{options.map((o) => <option key={o.v} value={o.v}>{o.t}</option>)}
      </select>
    </label>
  )
  const total = res.data?.total ?? 0

  return (
    <>
      <div><h2 className="text-xl font-extrabold text-white">Security event explorer</h2>
        <p className="text-sm text-slate-400">Search, filter and review stored events</p></div>
      <Banner tone="cyan" title="Simulated events, rule-based labels">The “predicted class” here is the simulator’s threshold rule. Model predictions on uploaded CSVs are on the AI intrusion detection page.</Banner>
      <Panel>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="text-xs text-slate-400 sm:col-span-2">Search
            <input className="field mt-1 w-full" type="search" placeholder="Device, topic, source IP, threat…" value={f.q} onChange={(e) => set('q')(e.target.value)} /></label>
          <label className="text-xs text-slate-400">From<input className="field mt-1 w-full" type="datetime-local" value={f.since} onChange={(e) => set('since')(e.target.value)} /></label>
          <label className="text-xs text-slate-400">To<input className="field mt-1 w-full" type="datetime-local" value={f.until} onChange={(e) => set('until')(e.target.value)} /></label>
          {Select({ k: 'device_id', label: 'Device', options: devices.map((d) => ({ v: d.id, t: d.name })) })}
          {Select({ k: 'event_type', label: 'Event type', options: TYPES.map((t) => ({ v: t, t: t.replace(/_/g, ' ') })) })}
          {Select({ k: 'label', label: 'Predicted class (rule)', options: LABELS.map((l) => ({ v: l, t: labelName(l) })) })}
          {Select({ k: 'severity', label: 'Severity', options: ['high', 'medium', 'low', 'info'].map((s) => ({ v: s, t: s })) })}
          {Select({ k: 'status', label: 'Status', options: ['open', 'acknowledged', 'resolved'].map((s) => ({ v: s, t: s })) })}
        </div>
      </Panel>

      {res.error && !res.data ? <ErrorState error={res.error} onRetry={res.reload} /> : (
        <Panel title={`${num(total)} matching events`} action={<button className="btn" onClick={() => { setF({ q: '', device_id: '', event_type: '', label: '', severity: '', status: '', since: '', until: '' }); setOffset(0) }}>Clear filters</button>}>
          {res.data && res.data.items.length === 0 ? <Empty title="No events match">Start the simulation or relax the filters.</Empty> : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px]">
                <caption className="sr-only">Security events</caption>
                <thead><tr><th scope="col" className="th">Time</th><th scope="col" className="th">Device</th><th scope="col" className="th">Event</th><th scope="col" className="th">Predicted class</th><th scope="col" className="th">Severity</th><th scope="col" className="th">Status</th><th scope="col" className="th"><span className="sr-only">Details</span></th></tr></thead>
                <tbody>
                  {res.data?.items.map((e) => (
                    <tr key={e.id} className="border-t border-slate-700/40 hover:bg-slate-700/20">
                      <td className="td">{clock(e.ts)}</td><td className="td">{e.device_name}</td><td className="td">{e.event_type.replace(/_/g, ' ')}</td>
                      <td className="td">{labelName(e.label)}</td><td className="td"><Pill tone={severityTone(e.severity)}>{e.severity}</Pill></td>
                      <td className="td">{e.status}</td>
                      <td className="td"><button className="btn px-2 py-1 text-xs" onClick={() => setOpen(e)} aria-label={`Inspect event ${e.id}`}>Inspect</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
            <span>Showing {total === 0 ? 0 : offset + 1}–{Math.min(offset + LIMIT, total)} of {num(total)}</span>
            <span className="flex gap-2"><button className="btn" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - LIMIT))}>Previous</button>
              <button className="btn" disabled={offset + LIMIT >= total} onClick={() => setOffset(offset + LIMIT)}>Next</button></span>
          </div>
        </Panel>
      )}

      <AnimatePresence>
        {open && (
          <DetailWindow key={open.id} title={`Event ${open.id}`} subtitle={`${open.device_name} · ${clock(open.ts)}`} onClose={() => setOpen(null)}>
            <div className="mb-3 flex flex-wrap gap-2"><Pill tone={severityTone(open.severity)}>{open.severity}</Pill><Pill tone="slate">{labelName(open.label)}</Pill><Pill tone="cyan">simulated</Pill></div>
            <dl className="grid grid-cols-2 gap-2 text-sm">
              {([['Event type', open.event_type], ['Protocol', open.protocol], ['Source IP', open.source_ip], ['Detected by', open.detection_source], ['Run', open.run_id], ['Status', open.status]] as const).map(([k, v]) => (
                <div key={k}><dt className="text-xs text-slate-500">{k}</dt><dd className="break-all text-slate-200">{v}</dd></div>))}
              <div className="col-span-2"><dt className="text-xs text-slate-500">Topic</dt><dd className="break-all text-slate-200">{open.topic}</dd></div>
            </dl>
            <h3 className="mb-1 mt-4 text-xs font-semibold text-slate-400">Evidence metrics</h3>
            <ul className="space-y-1 text-sm">{Object.entries(open.metrics).map(([k, v]) => <li key={k} className="flex justify-between border-b border-slate-700/40 py-1"><span className="text-slate-400">{k}</span><span>{String(v)}</span></li>)}</ul>
            {open.label !== 'normal' && (
              <div className="mt-4 flex flex-wrap gap-2">
                {(['open', 'acknowledged', 'resolved'] as const).map((s) => <button key={s} className="btn" disabled={open.status === s} onClick={() => void changeStatus(open, s)}>Mark {s}</button>)}
              </div>
            )}
          </DetailWindow>
        )}
      </AnimatePresence>
    </>
  )
}
