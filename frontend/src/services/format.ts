export const pct = (x: number | null | undefined, digits = 1) =>
  x === null || x === undefined || Number.isNaN(x) ? '–' : `${(x * 100).toFixed(digits)}%`

export const num = (x: number | null | undefined) => (x === null || x === undefined ? '–' : x.toLocaleString('en-US'))

export function timeAgo(iso: string | null | undefined, now = Date.now()): string {
  if (!iso) return 'no activity yet'
  const s = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000))
  if (s < 5) return 'just now'
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

export const clock = (iso: string) => new Date(iso).toLocaleTimeString('en-GB', { hour12: false })

export const LABEL_NAMES: Record<string, string> = {
  normal: 'Normal', brute_force: 'Credential brute force', connection_burst: 'Connection burst',
  publish_flood: 'Publish flood', topic_enumeration: 'Topic enumeration',
  dos: 'Denial of service', mitm: 'Man-in-the-middle', intrusion: 'Intrusion',
}
export const labelName = (l: string) => LABEL_NAMES[l] ?? l.replace(/_/g, ' ')

export const LABEL_COLORS: Record<string, string> = {
  normal: '#34d399', brute_force: '#f87171', connection_burst: '#fbbf24', publish_flood: '#fb923c',
  topic_enumeration: '#60a5fa', dos: '#f87171', mitm: '#fbbf24', intrusion: '#fb923c',
}
export const labelColor = (l: string) => LABEL_COLORS[l] ?? '#94a3b8'
