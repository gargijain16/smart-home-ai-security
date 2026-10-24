import type { ReactNode } from 'react'
import { Camera, Cpu, Info, Lightbulb, Lock, Radar, Router, Thermometer, TriangleAlert, WifiOff } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { ApiError } from '../services/api'
import type { Device, Severity } from '../types/api'

const TONES = {
  green: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300',
  amber: 'border-amber-400/30 bg-amber-400/10 text-amber-300',
  red: 'border-red-400/30 bg-red-400/10 text-red-300',
  cyan: 'border-cyan-400/30 bg-cyan-400/10 text-cyan-300',
  violet: 'border-violet-400/30 bg-violet-400/10 text-violet-300',
  slate: 'border-slate-500/30 bg-slate-500/10 text-slate-300',
} as const
export type Tone = keyof typeof TONES

export function Pill({ tone = 'slate', children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-semibold ${TONES[tone]}`}>{children}</span>
}
export const severityTone = (s: Severity): Tone => ({ high: 'red', medium: 'amber', low: 'cyan', info: 'slate' } as const)[s]
export const deviceTone = (s: Device['status']): Tone => ({ alert: 'red', normal: 'green', idle: 'slate' } as const)[s]

export function Panel({ title, action, children, className = '' }: { title?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`glass rounded-2xl p-4 ${className}`}>
      {(title || action) && (
        <header className="mb-3 flex items-center justify-between gap-3">
          {title && <h2 className="text-sm font-semibold text-slate-200">{title}</h2>}
          {action}
        </header>
      )}
      {children}
    </section>
  )
}

const STAT_TEXT: Record<string, string> = { cyan: 'text-cyan-300', red: 'text-red-300', amber: 'text-amber-300', green: 'text-emerald-300', violet: 'text-violet-300', slate: 'text-slate-100' }
export function Stat({ label, value, hint, tone = 'slate' }: { label: string; value: ReactNode; hint?: string; tone?: Tone }) {
  return (
    <div className="glass rounded-2xl p-4">
      <p className="text-xs text-slate-400">{label}</p>
      <p className={`mt-1 text-2xl font-bold sm:text-3xl ${STAT_TEXT[tone]}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

export function Banner({ tone = 'cyan', title, children }: { tone?: Tone; title: string; children?: ReactNode }) {
  const Icon = tone === 'red' || tone === 'amber' ? TriangleAlert : Info
  return (
    <div role="note" className={`flex gap-3 rounded-xl border p-3 text-sm ${TONES[tone]}`}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div>
        <p className="font-semibold">{title}</p>
        {children && <div className="mt-1 text-slate-300">{children}</div>}
      </div>
    </div>
  )
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-600/60 p-6 text-center">
      <p className="text-sm font-semibold text-slate-200">{title}</p>
      {children && <div className="mx-auto mt-1 max-w-md text-sm text-slate-400">{children}</div>}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  const offline = error.code === 'unreachable' || error.code === 'not_configured'
  return (
    <div role="alert" className="glass rounded-2xl border-red-400/30 p-6">
      <div className="flex items-center gap-3 text-red-300">
        <WifiOff className="h-5 w-5" aria-hidden />
        <h2 className="font-semibold">{offline ? 'Backend not reachable' : 'Request failed'}</h2>
      </div>
      <p className="mt-2 text-sm text-slate-300">{error.message}</p>
      {error.code === 'not_configured' && (
        <p className="mt-2 text-sm text-slate-400">Set <code>VITE_API_BASE_URL</code> in the Vercel project settings to your public backend URL, then redeploy.</p>
      )}
      {error.code === 'unreachable' && (
        <p className="mt-2 text-sm text-slate-400">Start the backend (<code>uvicorn app.main:app --port 8000</code>) or check the deployed API URL. A public site cannot reach an API running on localhost.</p>
      )}
      {onRetry && <button className="btn mt-4" onClick={onRetry}>Retry</button>}
    </div>
  )
}

const ICONS: Record<string, LucideIcon> = {
  'Smart lock': Lock, 'Security camera': Camera, 'Motion sensor': Radar, 'Smart light': Lightbulb,
  'HVAC controller': Thermometer, 'IoT gateway': Router,
}
export const deviceIcon = (type: string): LucideIcon => ICONS[type] ?? Cpu
