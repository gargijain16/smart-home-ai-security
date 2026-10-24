import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { motion, useDragControls } from 'framer-motion'
import { GripHorizontal, X } from 'lucide-react'

/** Non-modal floating window. Drag it by the header; it is constrained to the viewport. Esc closes it. */
export function DetailWindow({ title, subtitle, onClose, children }: { title: string; subtitle?: string; onClose: () => void; children: ReactNode }) {
  const bounds = useRef<HTMLDivElement>(null)
  const win = useRef<HTMLDivElement>(null)
  const controls = useDragControls()

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    win.current?.focus()
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div ref={bounds} className="pointer-events-none fixed inset-0 z-40">
      <motion.div
        ref={win} role="dialog" aria-label={title} tabIndex={-1}
        drag dragControls={controls} dragListener={false} dragConstraints={bounds} dragElastic={0} dragMomentum={false}
        initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.97 }}
        className="glass-strong pointer-events-auto absolute right-4 top-24 flex max-h-[72vh] w-[min(460px,calc(100vw-2rem))] flex-col rounded-2xl"
      >
        <div onPointerDown={(e) => controls.start(e)} className="flex cursor-grab touch-none items-center gap-2 border-b border-slate-700/60 px-4 py-3 active:cursor-grabbing">
          <GripHorizontal className="h-4 w-4 text-slate-500" aria-hidden />
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-sm font-semibold text-slate-100">{title}</h2>
            {subtitle && <p className="truncate text-xs text-slate-400">{subtitle}</p>}
          </div>
          <button aria-label="Close details" className="rounded-md p-1 text-slate-400 hover:bg-slate-700/50 hover:text-white" onPointerDown={(e) => e.stopPropagation()} onClick={onClose}>
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="overflow-y-auto p-4">{children}</div>
      </motion.div>
    </div>
  )
}
