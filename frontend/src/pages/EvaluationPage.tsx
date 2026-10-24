import { api } from '../services/api'
import { useApi } from '../hooks/useApi'
import { Banner, Empty, ErrorState, Panel, Stat } from '../components/ui'
import { labelName, pct } from '../services/format'
import type { ClassRow } from '../types/api'

export function EvaluationPage() {
  const { data, error, reload } = useApi(api.modelMetrics, [], 0)
  if (error && !data) return <ErrorState error={error} onRetry={reload} />
  if (!data) return <p className="p-6 text-sm text-slate-400">Loading evaluation…</p>
  if (!data.available || !data.metrics) {
    return (<><h2 className="text-xl font-extrabold text-white">Model evaluation</h2>
      <Empty title="No saved evaluation results">{data.reason ?? 'Train the model in Colab and copy models/ and reports/ into the project.'} Nothing is shown here until real metrics exist.</Empty></>)
  }
  const m = data.metrics, t = m.test, cm = m.confusion_matrix
  const rows = Object.entries(data.classification_report ?? {}).filter((e): e is [string, ClassRow] => typeof e[1] === 'object')
  return (
    <>
      <div><h2 className="text-xl font-extrabold text-white">Model evaluation</h2>
        <p className="text-sm text-slate-400">Saved results from the held-out test split ({m.n_test.toLocaleString()} rows) · selected model: {m.selected_model.replace('_', ' ')}</p></div>
      {m.is_synthetic && <Banner tone="amber" title="Synthetic smoke-test results">These numbers come from generated data and only prove the pipeline runs. They are not a benchmark and must not be cited as model performance.</Banner>}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat label="Accuracy" value={pct(t.accuracy)} tone="violet" /><Stat label="Macro precision" value={pct(t.macro_precision)} tone="violet" />
        <Stat label="Macro recall" value={pct(t.macro_recall)} tone="violet" /><Stat label="Macro F1" value={pct(t.macro_f1)} tone="violet" />
        <Stat label="Latency (1 sample)" value={`${m.latency_ms.single_sample_median_ms.toFixed(1)} ms`} hint={`median · p95 ${m.latency_ms.single_sample_p95_ms.toFixed(1)} ms`} />
      </div>
      <p className="text-xs text-slate-500">Accuracy is dominated by the majority (normal) class. Rely on macro F1 and the per-class table for imbalanced data.</p>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Confusion matrix (rows: actual, columns: predicted)">
          <div className="overflow-x-auto">
            <table className="w-full text-center text-sm"><caption className="sr-only">Confusion matrix</caption>
              <thead><tr><th className="th" /> {cm.labels.map((l) => <th key={l} scope="col" className="th text-center">{labelName(l)}</th>)}</tr></thead>
              <tbody>{cm.matrix.map((r, i) => { const sum = r.reduce((a, b) => a + b, 0) || 1
                return <tr key={cm.labels[i]}><th scope="row" className="th">{labelName(cm.labels[i])}</th>
                  {r.map((v, j) => <td key={j} className="td" style={{ background: `rgba(${i === j ? '52,211,153' : '248,113,113'},${Math.min(0.75, (v / sum) * (i === j ? 0.6 : 2.2))})` }} title={`${(v / sum * 100).toFixed(1)}% of actual ${cm.labels[i]}`}>{v}</td>)}</tr> })}</tbody></table>
          </div>
          {data.images.includes('confusion_matrix.png') && <img className="mt-3 w-full rounded-lg bg-white/95" src={api.reportUrl('confusion_matrix.png')} alt="Confusion matrix image from training" />}
        </Panel>
        <Panel title="Per-class performance">
          <table className="w-full"><caption className="sr-only">Per-class metrics</caption>
            <thead><tr>{['Class', 'Precision', 'Recall', 'F1', 'Support', 'FPR', 'FNR'].map((h) => <th key={h} scope="col" className="th">{h}</th>)}</tr></thead>
            <tbody>{rows.filter(([k]) => k in t.per_class_rates).map(([k, r]) => (
              <tr key={k} className="border-t border-slate-700/40"><td className="td font-semibold">{labelName(k)}</td><td className="td">{pct(r.precision)}</td><td className="td">{pct(r.recall)}</td>
                <td className="td">{pct(r['f1-score'])}</td><td className="td">{r.support}</td><td className="td">{pct(t.per_class_rates[k].fpr, 2)}</td><td className="td">{pct(t.per_class_rates[k].fnr, 1)}</td></tr>))}</tbody></table>
          <p className="mt-3 text-sm text-slate-300">Attack vs normal: false-positive rate <b>{pct(t.binary_attack_vs_normal.false_positive_rate, 2)}</b>, false-negative rate <b>{pct(t.binary_attack_vs_normal.false_negative_rate, 1)}</b>.</p>
          <p className="mt-1 text-xs text-slate-500">FPR: normal or other-class rows wrongly assigned to this class. FNR: rows of this class missed.</p>
        </Panel>
      </div>

      <Panel title="Model comparison (selection used validation macro F1)">
        <table className="w-full"><thead><tr>{['Model', 'Validation macro F1', 'Test macro F1', 'Test accuracy'].map((h) => <th key={h} scope="col" className="th">{h}</th>)}</tr></thead>
          <tbody>{Object.entries(m.comparison).map(([k, v]) => <tr key={k} className="border-t border-slate-700/40"><td className="td font-semibold">{k.replace('_', ' ')}{k === m.selected_model ? ' (selected)' : ''}</td>
            <td className="td">{pct(v.validation_macro_f1)}</td><td className="td">{pct(v.test_macro_f1)}</td><td className="td">{pct(v.test_accuracy)}</td></tr>)}</tbody></table>
        <p className="mt-2 text-xs text-slate-500">Latency measured on: {m.latency_ms.measured_on}. Batch of 1,000 rows: {m.latency_ms.batch_1000_ms.toFixed(1)} ms.</p>
      </Panel>
      <Panel title="Limitations"><ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">{data.limitations.map((l) => <li key={l}>{l}</li>)}</ul></Panel>
    </>
  )
}
