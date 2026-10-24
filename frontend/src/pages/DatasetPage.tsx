import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Cell } from 'recharts'
import { api } from '../services/api'
import { useApi } from '../hooks/useApi'
import { Banner, ErrorState, Panel, Pill } from '../components/ui'
import { labelColor, labelName, num } from '../services/format'

export function DatasetPage() {
  const { data, error, reload } = useApi(api.datasetInfo, [], 0)
  if (error && !data) return <ErrorState error={error} onRetry={reload} />
  if (!data) return <p className="p-6 text-sm text-slate-400">Loading dataset information…</p>
  const s = data.manifest.selected
  const dist = data.label_distribution?.all ? Object.entries(data.label_distribution.all).map(([k, v]) => ({ key: k, name: labelName(k), value: v })) : []
  const trained = data.trained_on as Record<string, unknown> | null
  const evalCfg = data.model?.evaluation as Record<string, unknown> | undefined
  return (
    <>
      <div><h2 className="text-xl font-extrabold text-white">Dataset and model information</h2><p className="text-sm text-slate-400">Provenance, schema and evaluation configuration</p></div>
      {data.model?.is_synthetic && <Banner tone="amber" title="The installed model was trained on synthetic data">The dataset section below describes the intended real dataset, not what the installed model saw.</Banner>}
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Selected dataset">
          <h3 className="text-base font-bold text-white">{s.name}</h3>
          <p className="text-xs text-slate-400">{s.authors} ({s.year})</p>
          <dl className="mt-3 space-y-2 text-sm">
            <div><dt className="text-xs text-slate-500">Licence</dt><dd>{s.licence}</dd></div>
            <div><dt className="text-xs text-slate-500">Data</dt><dd><a className="text-cyan-300 underline" href={s.data_url} target="_blank" rel="noreferrer">doi:{s.data_doi}</a></dd></div>
            <div><dt className="text-xs text-slate-500">Paper</dt><dd><a className="text-cyan-300 underline" href={s.paper_url} target="_blank" rel="noreferrer">{s.paper_url}</a></dd></div>
            <div><dt className="text-xs text-slate-500">Files and published frame counts</dt><dd>{Object.entries(s.published_counts).map(([f, c]) => <div key={f}>{f}: {num(c.attack)} attack / {num(c.normal)} normal</div>)}</dd></div>
            <div><dt className="text-xs text-slate-500">Granularity</dt><dd>{s.granularity}</dd></div>
            <div><dt className="text-xs text-slate-500">Bundled in this repository</dt><dd>{s.bundled_in_repo ? 'Yes' : 'No: download it and upload to Colab'}</dd></div>
          </dl>
        </Panel>
        <Panel title="Verification status">
          <p className="text-xs font-semibold text-emerald-300">Confirmed from public pages</p>
          <ul className="mb-3 mt-1 list-disc space-y-1 pl-5 text-sm text-slate-300">{data.manifest.verified_from_public_pages.map((v) => <li key={v}>{v}</li>)}</ul>
          <p className="text-xs font-semibold text-amber-300">Not verified (the notebook checks these at run time)</p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-300">{data.manifest.NOT_verified.map((v) => <li key={v}>{v}</li>)}</ul>
        </Panel>
      </div>
      <Panel title="Known dataset limitations"><ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">{data.manifest.known_limitations.map((v) => <li key={v}>{v}</li>)}</ul></Panel>
      <Panel title="Alternatives considered"><ul className="space-y-2 text-sm">{data.manifest.alternatives_considered.map((a) => <li key={a.name}><a className="font-semibold text-cyan-300 underline" href={a.url} target="_blank" rel="noreferrer">{a.name}</a> <span className="text-slate-400">{a.note}</span></li>)}</ul></Panel>

      {data.model ? (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Installed model" className="border-violet-400/20">
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div><dt className="text-xs text-slate-500">Version</dt><dd className="break-all">{data.model.model_version}</dd></div>
                <div><dt className="text-xs text-slate-500">Algorithm</dt><dd>{data.model.model_type.replace('_', ' ')}</dd></div>
                <div><dt className="text-xs text-slate-500">Trained</dt><dd>{new Date(data.model.trained_at).toLocaleString()}</dd></div>
                <div><dt className="text-xs text-slate-500">Dataset used</dt><dd>{String(trained?.name ?? 'unknown')}</dd></div>
                <div><dt className="text-xs text-slate-500">Rows after cleaning</dt><dd>{num(trained?.rows_after_cleaning as number)}</dd></div>
                <div><dt className="text-xs text-slate-500">Libraries</dt><dd>sklearn {data.model.environment?.sklearn}</dd></div>
              </dl>
              <h3 className="mb-1 mt-4 text-xs font-semibold text-slate-400">Evaluation configuration</h3>
              <ul className="space-y-1 text-sm text-slate-300">{Object.entries(evalCfg ?? {}).map(([k, v]) => <li key={k}><span className="text-slate-500">{k.replace(/_/g, ' ')}:</span> {Array.isArray(v) ? v.join(', ') : String(v)}</li>)}</ul>
            </Panel>
            <Panel title="Label distribution (after cleaning)">
              <div className="h-56" role="img" aria-label="Bar chart of class counts"><ResponsiveContainer width="100%" height="100%"><BarChart data={dist} margin={{ left: 0 }}>
                <XAxis dataKey="name" tick={{ fill: '#cbd5e1', fontSize: 11 }} /><YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#0a1020', border: '1px solid rgba(148,163,184,.25)', borderRadius: 10, fontSize: 12 }} />
                <Bar dataKey="value" name="Rows" radius={[6, 6, 0, 0]}>{dist.map((d) => <Cell key={d.key} fill={labelColor(d.key)} />)}</Bar></BarChart></ResponsiveContainer></div>
            </Panel>
          </div>
          <Panel title={`Feature schema (${data.feature_schema.length} columns)`} action={<Pill tone="slate">enforced on every upload</Pill>}>
            <div className="max-h-64 overflow-auto"><table className="w-full"><thead><tr><th className="th">#</th><th className="th">Column</th><th className="th">Type</th></tr></thead>
              <tbody>{data.feature_schema.map((f, i) => <tr key={f.name} className="border-t border-slate-700/40"><td className="td">{i + 1}</td><td className="td break-all">{f.name}</td><td className="td">{f.dtype}</td></tr>)}</tbody></table></div>
          </Panel>
        </>
      ) : <Banner tone="cyan" title="No model installed">Model version, feature schema, label distribution and evaluation configuration appear here once a trained model is present.</Banner>}
    </>
  )
}
