import type { PredictReport } from './types'
import { SCOPE } from './types'

/** Demo report so the UI is usable before a REST API exists on the Python backend. */
export function mockReport(genomeName: string): PredictReport {
  const id = genomeName.replace(/\.(fna|fasta|fa|txt)$/i, '')
  return {
    species: SCOPE.species,
    coverage_note: `Covers ${SCOPE.species} and ${SCOPE.antibiotics.length} antibiotics only.`,
    lab_banner: SCOPE.labBanner,
    defensive_note: SCOPE.defensiveNote,
    results: [
      {
        antibiotic: 'ciprofloxacin',
        call: 'likely to fail',
        confidence: 0.91,
        prob_fail: 0.93,
        evidence_type: 'known_resistance_mechanism',
        detected_genes: ['GYR:gyrA_S83I'],
        statistical_features: [],
        note: `Demo call for ${id}: fluoroquinolone resistance determinant present.`,
        nocall_reason: null,
        gate: 'target_present',
        prose: 'Known gyrA mutation associated with ciprofloxacin resistance.',
      },
      {
        antibiotic: 'gentamicin',
        call: 'likely to work',
        confidence: 0.86,
        prob_fail: 0.12,
        evidence_type: 'no_known_signal',
        detected_genes: [],
        statistical_features: [],
        note: 'No aminoglycoside resistance determinant detected in this demo genome.',
        nocall_reason: null,
        gate: 'target_present',
      },
      {
        antibiotic: 'meropenem',
        call: 'likely to fail',
        confidence: 0.96,
        prob_fail: 0.97,
        evidence_type: 'known_resistance_mechanism',
        detected_genes: ['Bla:KPC-2'],
        statistical_features: [],
        note: 'Carbapenemase (KPC) detected — high confidence fail call.',
        nocall_reason: null,
        gate: 'target_present',
        prose: 'Mechanistic evidence: KPC carbapenemase.',
      },
      {
        antibiotic: 'ceftazidime',
        call: 'no-call',
        confidence: 0.52,
        prob_fail: 0.51,
        evidence_type: 'statistical_association_only',
        detected_genes: [],
        statistical_features: ['Bla:SHV-variant'],
        note: 'Borderline calibrated probability with conflicting signals.',
        nocall_reason: 'calibrated probability in uncertain band',
        gate: 'unknown',
      },
    ],
  }
}
