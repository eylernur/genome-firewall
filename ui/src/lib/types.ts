export type Call = 'likely to fail' | 'likely to work' | 'no-call'

export type EvidenceType =
  | 'known_resistance_mechanism'
  | 'statistical_association_only'
  | 'no_known_signal'
  | ''

export interface DrugResult {
  antibiotic: string
  call: Call | string
  confidence: number | null
  prob_fail?: number | string
  evidence_type?: EvidenceType | string
  detected_genes?: string[]
  statistical_features?: string[]
  note?: string
  nocall_reason?: string | null
  prose?: string
  gate?: string
  reason?: string
}

export interface PredictReport {
  species: string
  results: DrugResult[]
  coverage_note: string
  lab_banner: string
  defensive_note: string
}

export const EV_LABEL: Record<string, string> = {
  known_resistance_mechanism: 'Known resistance gene detected',
  statistical_association_only: 'Statistical association only',
  no_known_signal: 'No known resistance signal',
}

export const SCOPE = {
  species: 'Klebsiella pneumoniae',
  antibiotics: ['ciprofloxacin', 'gentamicin', 'meropenem', 'ceftazidime'] as const,
  labBanner:
    'Research prototype. Every result must be confirmed by standard laboratory testing. Not for clinical use.',
  defensiveNote:
    'Defensive use only: this tool predicts and explains resistance that already exists. It never designs, modifies, or optimizes organisms.',
}
