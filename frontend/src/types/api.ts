// Mirrors backend/app/schemas.py. Keep the two in sync.
export type Severity = 'info' | 'low' | 'medium' | 'high'
export type EventStatus = 'open' | 'acknowledged' | 'resolved'
export type SimState = 'stopped' | 'running' | 'paused'

export interface Health { status: 'ok'; version: string; time: string; mode: 'ml' | 'demo'; model_loaded: boolean; simulation_state: SimState }

export interface Device {
  id: string; name: string; type: string; room: string; protocol: string
  status: 'normal' | 'alert' | 'idle'; last_activity: string | null
  open_alerts: number; total_events: number; is_simulated: boolean
}

export interface SecEvent {
  id: number; ts: string; device_id: string; device_name: string; event_type: string; protocol: string
  topic: string; source_ip: string; metrics: Record<string, number | boolean>; label: string
  severity: Severity; status: EventStatus; detection_source: string; is_simulated: boolean; run_id: string
}
export interface EventPage { total: number; limit: number; offset: number; items: SecEvent[] }

export interface SimulationState {
  state: SimState; run_id: string | null; seed: number; ticks: number; events_generated: number
  tick_seconds: number; rules: Record<string, { description: string; metric: string; medium_at: number | null; high_at: number | boolean }>
  notice: string
}

export interface Overview {
  devices_monitored: number; total_events: number; suspicious_events: number; high_priority_open: number
  threat_distribution: Record<string, number>
  timeline: { t: string; normal: number; suspicious: number }[]
  device_health: Device[]; recent_events: SecEvent[]; simulation: SimulationState
  model: { available: boolean; mode: 'ml' | 'demo'; model_version: string | null; is_synthetic: boolean; selected_model?: string
    headline: { accuracy: number; macro_precision: number; macro_recall: number; macro_f1: number } | null }
  data_origin: string
}

export interface ModelStatus {
  available: boolean; mode: 'ml' | 'demo'; reason: string | null; model_version: string | null; model_type: string | null
  is_synthetic: boolean; is_benchmark: boolean; trained_at: string | null; classes: string[]; n_features: number
  dataset_name: string | null; sklearn_version_trained: string | null; sklearn_version_runtime: string
  version_mismatch: boolean; how_to_enable: string[]
}

export interface ClassRates { fpr: number | null; fnr: number | null; support: number }
export interface ModelMetrics {
  mode: string; is_synthetic: boolean; selected_model: string; generated_at: string; n_test: number
  test: { accuracy: number; macro_precision: number; macro_recall: number; macro_f1: number; weighted_f1: number
    per_class_rates: Record<string, ClassRates>
    binary_attack_vs_normal: { false_positive_rate: number | null; false_negative_rate: number | null } }
  comparison: Record<string, { validation_macro_f1: number; test_macro_f1: number; test_accuracy: number }>
  confusion_matrix: { labels: string[]; matrix: number[][] }
  latency_ms: { single_sample_median_ms: number; single_sample_p95_ms: number; batch_1000_ms: number; measured_on: string }
}
export interface ClassRow { precision: number; recall: number; 'f1-score': number; support: number }
export interface MetricsResponse {
  available: boolean; reason: string | null; metrics: ModelMetrics | null
  classification_report: Record<string, ClassRow | number> | null
  images: string[]; limitations: string[]; is_synthetic: boolean
}

export interface Manifest {
  selected: { name: string; authors: string; year: number; data_doi: string; data_url: string; paper_url: string; licence: string
    size: string; files: string[]; granularity: string; intended_use: string; bundled_in_repo: boolean
    published_counts: Record<string, { attack: number; normal: number; total: number }> }
  verified_from_public_pages: string[]; NOT_verified: string[]
  alternatives_considered: { name: string; url: string; note: string }[]
  why_selected: string; known_limitations: string[]
}
export interface DatasetInfo {
  manifest: Manifest; trained_on: Record<string, unknown> | null
  feature_schema: { name: string; dtype: string }[]
  label_distribution: Record<string, Record<string, number>> | null
  model: { model_version: string; model_type: string; trained_at: string; is_synthetic: boolean
    evaluation: Record<string, unknown>; environment: Record<string, string> } | null
}

export interface Evidence { feature: string; value: number | null; global_importance: number }
export interface RowPrediction { row: number; predicted_class: string; is_attack: boolean; probabilities: Record<string, number> | null; evidence: Evidence[] }
export interface PredictResponse {
  mode: 'ml'; model_version: string; predicted_at: string; is_synthetic_model: boolean
  validation: { status: string; rows: number; columns: number; rows_with_missing_values: number; note: string }
  summary: Record<string, number>; probability_note: string | null; explanation_type: string; predictions: RowPrediction[]
}
