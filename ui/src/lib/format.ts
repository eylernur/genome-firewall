/** Cap clinical confidence displays — never show 100%. */
export function formatConfidencePct(confidence: number | null | undefined): string | null {
  if (confidence == null || Number.isNaN(Number(confidence))) return null
  const c = Number(confidence)
  if (c >= 1) return '99'
  return String(Math.min(99, Math.round(c * 100)))
}

export function formatProbFail(prob: number | string | null | undefined): string {
  if (prob == null || prob === '') return '—'
  const p = typeof prob === 'string' ? Number(prob) : prob
  if (Number.isNaN(p)) return String(prob)
  if (p >= 1) return '≥0.99'
  if (p <= 0) return '≤0.01'
  return p.toFixed(2)
}

export function gateLabel(gate: string | undefined): string | null {
  if (!gate) return null
  switch (gate) {
    case 'target_present':
      return 'Drug target intact ✓'
    case 'target_absent':
      return 'Drug target disrupted ✗'
    case 'unknown':
      return 'Target status unknown'
    default:
      return gate
  }
}

export function formatReportTimestamp(d: Date): string {
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
