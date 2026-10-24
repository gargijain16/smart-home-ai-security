import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { BarChart3, Bell, BrainCircuit, Database, House, LayoutDashboard, PanelLeftClose, PanelLeftOpen, ScanSearch, ScrollText, ShieldCheck } from 'lucide-react'
import type { ApiError } from '../services/api'
import type { Health, ModelStatus, Overview } from '../types/api'
import { clock, labelName } from '../services/format'
import { Pill } from './ui'
import type { Tone } from './ui'

export type PageId = 'overview' | 'devices' | 'detection' | 'events' | 'evaluation' | 'dataset'
export const NAV: { id: PageId; label: string; icon: typeof House }[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'devices', label: 'Smart home devices', icon: House },
  { id: 'detection', label: 'AI intrusion detection', icon: BrainCircuit },
  { id: 'events', label: 'Security events', icon: ScrollText },
  { id: 'evaluation', label: 'Model evaluation', icon: BarChart3 },
  { id: 'dataset', label: 'Dataset and model', icon: Database },
]

export function modeBadge(health: Health | null, healthError: ApiError | null, model: ModelStatus | null): { tone: Tone; text: string } {
  if (healthError) return { tone: 'red', text: 'Backend offline' }
  if (!health) return { tone: 'slate', text: 'Connecting…' }
  if (model?.available && model.is_synthetic) return { tone: 'amber', text: 'ML pipeline check (synthetic data)' }
  if (model?.available) return { tone: 'green', text: 'Trained ML model active' }
  return { tone: 'cyan', text: 'Demo mode, no trained model' }
}

export function Shell(props: { page: PageId; onNavigate: (p: PageId) => void; health: Health | null; healthError: ApiError | null
  model: ModelStatus | null; overview: Overview | null; children: ReactNode }) {
  const { page, onNavigate, health, healthError, model, overview, children } = props
  const [collapsed, setCollapsed] = useState(false)
  const [bellOpen, setBellOpen] = useState(false)
  const bellRef = useRef<HTMLDivElement>(null)
  const badge = modeBadge(health, healthError, model)
  const urgent = (overview?.recent_events ?? []).filter((e) => e.severity === 'high' && e.status === 'open').slice(0, 5)

  useEffect(() => {
    if (!bellOpen) return
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent) { if (e.key === 'Escape') setBellOpen(false) }
      else if (bellRef.current && !bellRef.current.contains(e.target as Node)) setBellOpen(false)
    }
    window.addEventListener('keydown', close)
    window.addEventListener('mousedown', close)
    return () => { window.removeEventListener('keydown', close); window.removeEventListener('mousedown', close) }
  }, [bellOpen])

  return (
    <div className="min-h-screen px-3 py-4 sm:px-6 sm:py-6">
      <a href="#main" className="sr-only rounded-lg bg-cyan-400 px-3 py-2 font-semibold text-slate-900 focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50">Skip to content</a>
      <div className="glass mx-auto max-w-[1500px] rounded-[28px]">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-700/50 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl border border-cyan-400/40 bg-cyan-400/10 text-cyan-300"><ShieldCheck className="h-5 w-5" aria-hidden /></div>
            <div>
              <h1 className="text-base font-extrabold leading-tight text-white sm:text-lg">Smart Home Intrusion Detection</h1>
              <p className="text-xs text-slate-400">Machine-learning monitoring for consumer IoT · MQTT</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span aria-live="polite"><Pill tone={badge.tone}><span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />{badge.text}</Pill></span>
            <div ref={bellRef} className="relative">
              <button className="btn relative px-2.5" aria-label={`Notifications, ${overview?.high_priority_open ?? 0} high-priority open`} aria-expanded={bellOpen} onClick={() => setBellOpen((o) => !o)}>
                <Bell className="h-4 w-4" aria-hidden />
                {(overview?.high_priority_open ?? 0) > 0 && <span className="absolute -right-1 -top-1 grid h-4 min-w-4 place-items-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">{overview!.high_priority_open > 99 ? '99+' : overview!.high_priority_open}</span>}
              </button>
              {bellOpen && (
                <div className="glass-strong absolute right-0 top-12 z-30 w-80 rounded-xl p-3" role="region" aria-label="High-priority alerts">
                  <p className="mb-2 text-xs font-semibold text-slate-300">Latest high-priority alerts (simulated)</p>
                  {urgent.length === 0 && <p className="text-sm text-slate-400">No open high-priority alerts.</p>}
                  <ul className="space-y-2">
                    {urgent.map((e) => (
                      <li key={e.id} className="rounded-lg border border-slate-700/60 p-2 text-sm">
                        <p className="font-semibold text-red-300">{labelName(e.label)}</p>
                        <p className="text-xs text-slate-400">{e.device_name} · {clock(e.ts)}</p>
                      </li>
                    ))}
                  </ul>
                  <button className="btn mt-3 w-full justify-center" onClick={() => { setBellOpen(false); onNavigate('events') }}>Open event explorer</button>
                </div>
              )}
            </div>
          </div>
        </header>

        <div className="flex flex-col gap-4 p-3 md:flex-row md:p-4">
          <nav aria-label="Primary" className={`glass rounded-2xl p-2 md:sticky md:top-4 md:self-start ${collapsed ? 'md:w-16' : 'md:w-60'}`}>
            <ul className="flex gap-1 overflow-x-auto md:flex-col md:overflow-visible">
              {NAV.map(({ id, label, icon: Icon }) => (
                <li key={id}>
                  <button onClick={() => onNavigate(id)} aria-current={page === id ? 'page' : undefined} title={label}
                    className={`flex w-full items-center gap-3 whitespace-nowrap rounded-xl px-3 py-2.5 text-sm font-semibold transition-colors ${page === id ? 'bg-cyan-400/15 text-cyan-200 ring-1 ring-cyan-400/30' : 'text-slate-300 hover:bg-slate-700/40'}`}>
                    <Icon className={`h-4 w-4 shrink-0 ${id === 'detection' ? 'text-violet-300' : ''}`} aria-hidden />
                    <span className={collapsed ? 'md:sr-only' : ''}>{label}</span>
                  </button>
                </li>
              ))}
              <li>
                <button disabled aria-disabled="true" title="Vulnerability assessment is planned for a later phase"
                  className="flex w-full cursor-not-allowed items-center gap-3 whitespace-nowrap rounded-xl px-3 py-2.5 text-sm font-semibold text-slate-500">
                  <ScanSearch className="h-4 w-4 shrink-0" aria-hidden />
                  <span className={collapsed ? 'md:sr-only' : ''}>VAPT</span>
                  {!collapsed && <span className="ml-auto rounded-full border border-slate-600/60 px-2 py-0.5 text-[10px]">Coming later</span>}
                </button>
              </li>
            </ul>
            <button className="btn mt-2 hidden w-full justify-center md:inline-flex" aria-expanded={!collapsed} aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'} onClick={() => setCollapsed((c) => !c)}>
              {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <><PanelLeftClose className="h-4 w-4" />Collapse</>}
            </button>
          </nav>
          <main id="main" tabIndex={-1} className="min-w-0 flex-1 space-y-4 outline-none">{children}</main>
        </div>
      </div>
    </div>
  )
}
