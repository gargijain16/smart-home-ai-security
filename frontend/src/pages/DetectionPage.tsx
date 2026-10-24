import { useState } from 'react'
import type { DragEvent } from 'react'
import { BrainCircuit, Download, FileUp } from 'lucide-react'
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, ApiError } from '../services/api'
import type { ModelStatus, PredictResponse } from '../types/api'
import { useApi } from '../hooks/useApi'
import { Banner, Empty, Panel, Pill } from '../components/ui'
import { labelColor, labelName } from '../services/format'

export function DetectionPage({ model, reloadModel }: { model: ModelStatus | null; reloadModel: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [result, setResult] = useState<PredictResponse | null>(null)
  const [row, setRow] = useState(0)
  const [shapOk, setShapOk] = useState(true)
  const [impOk, setImpOk] = useState(true)
  const info = useApi(api.datasetInfo, [model?.available], 0)
  const schema = info.data?.feature_schema ?? []

  async function run() {
    if (!file) return
    setBusy(true); setError(null); setResult(null)
    try { setResult(await api.predictCsv(file)); setRow(0) }
    catch (e) { setError(e instanceof ApiError ? e : new ApiError('unknown', String(e))) }
    finally { setBusy(false) }
  }
  const drop = (e: DragEvent) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) setFile(f) }
  const template = () => {
    const url = URL.createObjectURL(new Blob([schema.map((s) => s.name).join(',') + '\n'], { type: 'text/csv' }))
    const a = document.createElement('a'); a.href = url; a.download = 'feature_template.csv'; a.click(); URL.revokeObjectURL(url)
  }
  const summary = result ? Object.entries(result.summary).map(([k, v]) => ({ key: k, name: labelName(k), value: v })) : []
  const sel = result?.predictions[row]
  const details = error?.details as { missing?: string[]; unexpected?: string[]; columns?: string[]; example_rows?: number[] } | undefined

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h2 className="text-xl font-extrabold text-white">AI intrusion detection</h2>
          <p className="text-sm text-slate-400">Score a CSV of MQTT network-frame features with the trained model</p></div>
        {model && <Pill tone={model.available ? (model.is_synthetic ? 'amber' : 'violet') : 'cyan'}><BrainCircuit className="h-3.5 w-3.5" aria-hidden />{model.available ? (model.is_synthetic ? 'Synthetic pipeline-check model' : 'Trained model loaded') : 'Demo mode: no model'}</Pill>}
      </div>

      {!model?.available && (
        <Panel title="No trained model is installed" className="border-cyan-400/20">
          <p className="text-sm text-slate-300">The dashboard is running in demo mode. Predictions stay disabled rather than showing made-up results.</p>
          {model?.reason && <p className="mt-2 text-xs text-slate-500">{model.reason}</p>}
          <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-slate-300">{(model?.how_to_enable ?? []).map((s) => <li key={s}>{s}</li>)}</ol>
          <button className="btn mt-4" onClick={reloadModel}>I’ve added the files, check again</button>
        </Panel>
      )}
      {model?.available && model.is_synthetic && <Banner tone="amber" title="Synthetic model">Trained on generated data to check the pipeline. Its predictions say nothing about real MQTT traffic.</Banner>}
      {model?.version_mismatch && <Banner tone="amber" title="scikit-learn version differs">Trained with {model.sklearn_version_trained}, running {model.sklearn_version_runtime}. Install the training version if predictions fail or look odd.</Banner>}

      {model?.available && (
        <Panel title="Upload samples" className="border-violet-400/20" action={<button className="btn" onClick={template} disabled={!schema.length}><Download className="h-4 w-4" aria-hidden />Header template</button>}>
          <label onDragOver={(e) => e.preventDefault()} onDrop={drop}
            className="flex cursor-pointer flex-col items-center gap-2 rounded-xl border border-dashed border-violet-400/40 p-6 text-center focus-within:ring-2 focus-within:ring-cyan-400 hover:bg-violet-400/5">
            <FileUp className="h-6 w-6 text-violet-300" aria-hidden />
            <span className="text-sm font-semibold text-slate-200">{file ? file.name : 'Choose a CSV file or drop it here'}</span>
            <span className="text-xs text-slate-400">Columns must match the {model.n_features} trained features exactly. Extra, missing or non-numeric columns are rejected.</span>
            <input className="sr-only" type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </label>
          <div className="mt-3 flex items-center gap-3"><button className="btn btn-ai" disabled={!file || busy} onClick={() => void run()}>{busy ? 'Scoring…' : 'Run detection'}</button>
            {file && <button className="btn" onClick={() => { setFile(null); setResult(null); setError(null) }}>Clear</button>}</div>
          {error && (
            <div role="alert" className="mt-3 rounded-lg border border-red-400/30 bg-red-400/10 p-3 text-sm text-red-200">
              <p className="font-semibold">{error.message}</p>
              {details?.missing && details.missing.length > 0 && <p className="mt-1 text-xs">Missing columns: {details.missing.slice(0, 12).join(', ')}{details.missing.length > 12 ? '…' : ''}</p>}
              {details?.unexpected && details.unexpected.length > 0 && <p className="mt-1 text-xs">Unexpected columns: {details.unexpected.slice(0, 12).join(', ')}</p>}
              {details?.columns && <p className="mt-1 text-xs">Non-numeric in: {details.columns.join(', ')} (rows {details.example_rows?.join(', ')})</p>}
            </div>
          )}
        </Panel>
      )}

      {result && (
        <>
          <Panel title="Prediction results" action={<span className="text-xs text-slate-400">model {result.model_version} · {new Date(result.predicted_at).toLocaleString()}</span>}>
            <div className="mb-3 flex flex-wrap gap-2"><Pill tone="violet">Real ML inference</Pill><Pill tone="slate">{result.validation.rows} rows validated</Pill>
              {result.validation.rows_with_missing_values > 0 && <Pill tone="amber">{result.validation.rows_with_missing_values} rows with missing cells (median-imputed)</Pill>}
              {result.is_synthetic_model && <Pill tone="amber">synthetic model</Pill>}</div>
            <div className="h-32" role="img" aria-label="Bar chart of predicted class counts">
              <ResponsiveContainer width="100%" height="100%"><BarChart data={summary} layout="vertical" margin={{ left: 20 }}>
                <XAxis type="number" allowDecimals={false} tick={{ fill: '#94a3b8', fontSize: 11 }} /><YAxis type="category" dataKey="name" width={140} tick={{ fill: '#cbd5e1', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#0a1020', border: '1px solid rgba(148,163,184,.25)', borderRadius: 10, fontSize: 12 }} />
                <Bar dataKey="value" name="Rows" radius={[0, 6, 6, 0]}>{summary.map((s) => <Cell key={s.key} fill={labelColor(s.key)} />)}</Bar></BarChart></ResponsiveContainer>
            </div>
            <div className="mt-3 max-h-80 overflow-auto">
              <table className="w-full min-w-[520px]"><caption className="sr-only">Per-row predictions</caption>
                <thead><tr><th scope="col" className="th">Row</th><th scope="col" className="th">Predicted class</th><th scope="col" className="th">{result.probability_note ? 'Tree vote share' : 'Confidence'}</th></tr></thead>
                <tbody>{result.predictions.slice(0, 200).map((p) => (
                  <tr key={p.row} onClick={() => setRow(p.row)} className={`cursor-pointer border-t border-slate-700/40 hover:bg-slate-700/20 ${row === p.row ? 'bg-violet-400/10' : ''}`}>
                    <td className="td">{p.row + 1}</td>
                    <td className="td"><span className="font-semibold" style={{ color: labelColor(p.predicted_class) }}>{labelName(p.predicted_class)}</span>{p.is_attack && <span className="ml-2 text-xs text-red-300">attack</span>}</td>
                    <td className="td">{p.probabilities ? (
                      <div className="flex h-2 w-48 overflow-hidden rounded-full bg-slate-700/50" aria-label={Object.entries(p.probabilities).map(([k, v]) => `${labelName(k)} ${(v * 100).toFixed(0)}%`).join(', ')}>
                        {Object.entries(p.probabilities).map(([k, v]) => <div key={k} style={{ width: `${v * 100}%`, background: labelColor(k) }} title={`${labelName(k)} ${(v * 100).toFixed(1)}%`} />)}</div>
                    ) : <span className="text-xs text-slate-500">not shown for this model type</span>}</td>
                  </tr>))}</tbody></table>
              {result.predictions.length > 200 && <p className="mt-2 text-xs text-slate-500">Showing the first 200 of {result.predictions.length} rows.</p>}
            </div>
            {result.probability_note && <p className="mt-2 text-xs text-slate-500">{result.probability_note}</p>}
          </Panel>
          {sel && (
            <Panel title={`Evidence for row ${sel.row + 1}`}>
              <p className="mb-2 text-xs text-slate-400">The five most important features overall, with this row’s values. This is global feature importance, not a per-prediction attribution.</p>
              <ul className="space-y-1 text-sm">{sel.evidence.map((e) => <li key={e.feature} className="flex items-center justify-between border-b border-slate-700/40 py-1">
                <span className="break-all text-slate-300">{e.feature}</span><span className="text-slate-100">{e.value ?? 'missing'} <span className="text-xs text-slate-500">importance {(e.global_importance * 100).toFixed(1)}%</span></span></li>)}</ul>
            </Panel>
          )}
        </>
      )}

      {model?.available && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Panel title="Feature importance">{impOk ? <img src={api.reportUrl('feature_importance.png')} alt="Feature importance bar chart from training" className="w-full rounded-lg bg-white/95" onError={() => setImpOk(false)} /> : <Empty title="Image not available" />}</Panel>
          <Panel title="SHAP explanation (optional)">{shapOk ? <img src={api.reportUrl('shap_summary.png')} alt="SHAP summary plot" className="w-full rounded-lg bg-white/95" onError={() => setShapOk(false)} /> : <Empty title="No SHAP plot generated">Run the notebook with the <code>shap</code> package installed to create one.</Empty>}</Panel>
        </div>
      )}
      {schema.length > 0 && (
        <Panel title={`Required input columns (${schema.length})`}><p className="flex flex-wrap gap-1.5 text-xs">{schema.map((s) => <code key={s.name} className="rounded bg-slate-700/50 px-1.5 py-0.5">{s.name}</code>)}</p></Panel>
      )}
    </>
  )
}
