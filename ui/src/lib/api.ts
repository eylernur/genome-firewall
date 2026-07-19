import type { PredictReport } from './types'
import { mockReport } from './mockReport'

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ?? ''

/**
 * Upload a FASTA and get a per-antibiotic report.
 * If VITE_API_URL is set, POSTs multipart to `${VITE_API_URL}/predict`.
 * Otherwise returns a local mock report (backend remains Streamlit-only for now).
 */
export async function predictGenome(file: File): Promise<{ report: PredictReport; source: 'api' | 'mock' }> {
  if (!API_BASE) {
    await delay(700)
    return { report: mockReport(file.name), source: 'mock' }
  }

  const body = new FormData()
  body.append('file', file)

  let res: Response
  try {
    res = await fetch(`${API_BASE}/predict`, { method: 'POST', body })
  } catch {
    throw new Error(
      `Cannot reach API at ${API_BASE}. Start the backend with: cd ../genome-firewall && make api`,
    )
  }
  if (!res.ok) {
    let detail = ''
    try {
      const j = (await res.json()) as { detail?: string }
      detail = j.detail ?? ''
    } catch {
      detail = await res.text().catch(() => '')
    }
    throw new Error(detail || `Predict failed (${res.status})`)
  }
  const report = (await res.json()) as PredictReport
  return { report, source: 'api' }
}

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms))
}
