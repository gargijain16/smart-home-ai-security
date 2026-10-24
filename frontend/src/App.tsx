import { useCallback, useEffect, useState } from 'react'
import { api } from './services/api'
import { useApi } from './hooks/useApi'
import { NAV, Shell } from './components/Shell'
import type { PageId } from './components/Shell'
import { OverviewPage } from './pages/OverviewPage'
import { DevicesPage } from './pages/DevicesPage'
import { DetectionPage } from './pages/DetectionPage'
import { EventsPage } from './pages/EventsPage'
import { EvaluationPage } from './pages/EvaluationPage'
import { DatasetPage } from './pages/DatasetPage'

const IDS = NAV.map((n) => n.id)
const fromHash = (): PageId => {
  const h = window.location.hash.replace('#', '') as PageId
  return IDS.includes(h) ? h : 'overview'
}

export default function App() {
  const [page, setPage] = useState<PageId>(fromHash)
  const health = useApi(api.health, [], 4000)
  const model = useApi(api.modelStatus, [], 8000)
  const overview = useApi(api.overview, [], 2500)

  useEffect(() => {
    const on = () => setPage(fromHash())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  const go = useCallback((p: PageId) => { window.location.hash = p; setPage(p) }, [])

  const reloadModel = useCallback(() => { void model.reload(); void health.reload() }, [model, health])

  return (
    <Shell page={page} onNavigate={go} health={health.data} healthError={health.error} model={model.data} overview={overview.data}>
      {page === 'overview' && <OverviewPage overview={overview.data} error={overview.error} reload={overview.reload} go={go} />}
      {page === 'devices' && <DevicesPage overview={overview.data} error={overview.error} reload={overview.reload} />}
      {page === 'detection' && <DetectionPage model={model.data} reloadModel={reloadModel} />}
      {page === 'events' && <EventsPage devices={overview.data?.device_health ?? []} />}
      {page === 'evaluation' && <EvaluationPage />}
      {page === 'dataset' && <DatasetPage />}
    </Shell>
  )
}
