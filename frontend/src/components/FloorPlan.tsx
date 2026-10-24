import type { Device } from '../types/api'
import { deviceIcon } from './ui'

const ROOMS: { name: string; x: number; y: number; w: number; h: number }[] = [
  { name: 'Garage', x: 40, y: 40, w: 150, h: 160 }, { name: 'Bedroom', x: 190, y: 40, w: 170, h: 160 },
  { name: 'Study', x: 360, y: 40, w: 140, h: 160 }, { name: 'Utility', x: 500, y: 40, w: 180, h: 160 },
  { name: 'Entrance', x: 40, y: 200, w: 130, h: 180 }, { name: 'Hallway', x: 170, y: 200, w: 160, h: 180 },
  { name: 'Living room', x: 330, y: 200, w: 230, h: 180 }, { name: 'Kitchen', x: 560, y: 200, w: 120, h: 180 },
]
const POS: Record<string, [number, number]> = {
  'cam-garage': [115, 120], 'light-bedroom': [275, 120], 'gateway-hub': [430, 120], 'hvac-main': [590, 120],
  'lock-front': [105, 330], 'motion-hall': [250, 300], 'light-living': [445, 300], 'lock-back': [620, 300], 'cam-porch': [105, 405],
}
const COLOR = { alert: '#f87171', normal: '#34d399', idle: '#64748b' } as const

export function FloorPlan({ devices, selectedId, onSelect }: { devices: Device[]; selectedId: string | null; onSelect: (id: string) => void }) {
  return (
    <svg viewBox="0 0 720 440" className="h-auto w-full" role="group" aria-label="Floor plan with device markers">
      <rect x="40" y="40" width="640" height="340" rx="14" fill="rgba(15,23,42,0.5)" stroke="rgba(148,163,184,0.35)" strokeWidth="2" />
      {ROOMS.map((r) => (
        <g key={r.name}>
          <rect x={r.x} y={r.y} width={r.w} height={r.h} fill="none" stroke="rgba(148,163,184,0.2)" />
          <text x={r.x + 10} y={r.y + 20} fill="#64748b" fontSize="12" fontWeight="600">{r.name}</text>
        </g>
      ))}
      <rect x="40" y="385" width="130" height="40" rx="6" fill="none" stroke="rgba(148,163,184,0.2)" strokeDasharray="4 4" />
      <text x="50" y="400" fill="#64748b" fontSize="12" fontWeight="600">Porch</text>
      {devices.map((d) => {
        const p = POS[d.id]
        if (!p) return null
        const Icon = deviceIcon(d.type)
        const c = COLOR[d.status]
        const sel = selectedId === d.id
        return (
          <g key={d.id} transform={`translate(${p[0]} ${p[1]})`} tabIndex={0} role="button" className="cursor-pointer outline-none focus-visible:[&>circle:nth-of-type(2)]:stroke-cyan-300"
             aria-label={`${d.name}, ${d.status}${d.open_alerts ? `, ${d.open_alerts} open alerts` : ''}`} aria-pressed={sel}
             onClick={() => onSelect(d.id)} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(d.id) } }}>
            {d.status === 'alert' && <circle className="alert-ring" r="16" fill={c} opacity="0.5" />}
            <circle r="17" fill="#0a1020" stroke={sel ? '#22d3ee' : c} strokeWidth={sel ? 3 : 2} />
            <Icon x={-8} y={-8} width={16} height={16} color={c} aria-hidden />
            <text y="32" textAnchor="middle" fill="#cbd5e1" fontSize="11" fontWeight="600">{d.name.replace(' controller', '').replace(' sensor', '')}</text>
          </g>
        )
      })}
    </svg>
  )
}
