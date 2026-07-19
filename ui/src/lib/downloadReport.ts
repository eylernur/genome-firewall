import { jsPDF } from 'jspdf'
import type { DrugResult, PredictReport } from './types'
import { EV_LABEL } from './types'
import {
  formatConfidencePct,
  formatProbFail,
  formatReportTimestamp,
  gateLabel,
} from './format'

const DISCLAIMER =
  'Research prototype — confirm every result with standard laboratory testing.'

export type ReportBundle = {
  report: PredictReport
  genomeId: string
  analyzedAt: Date
  best: DrugResult | undefined
  fails: DrugResult[]
  nocalls: DrugResult[]
}

function geneNames(r: DrugResult): string {
  return (r.detected_genes ?? []).map((g) => g.split(':').pop() ?? g).join(', ')
}

function fileBase(genomeId: string): string {
  const safe = (genomeId || 'isolate').replace(/[^\w.-]+/g, '_')
  return `GenoWall-report-${safe}`
}

function buildPdf(opts: ReportBundle): jsPDF {
  const { report, genomeId, analyzedAt, best, fails, nocalls } = opts
  const doc = new jsPDF({ unit: 'mm', format: 'a4' })
  const pageW = doc.internal.pageSize.getWidth()
  const margin = 16
  const maxW = pageW - margin * 2
  let y = 18

  const ensure = (need: number) => {
    if (y + need > 280) {
      doc.addPage()
      y = 18
    }
  }

  const line = (text: string, size = 10, style: 'normal' | 'bold' = 'normal', color = '#1C1B18') => {
    ensure(size * 0.55 + 4)
    doc.setFont('helvetica', style)
    doc.setFontSize(size)
    doc.setTextColor(color)
    const rows = doc.splitTextToSize(text, maxW) as string[]
    doc.text(rows, margin, y)
    y += rows.length * (size * 0.42) + 3
  }

  // Header
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(22)
  doc.setTextColor('#1C1B18')
  doc.text('GenoWall', margin, y)
  y += 8
  line(
    `Analyzed ${formatReportTimestamp(analyzedAt)} · Isolate ${genomeId} · ${report.species}`,
    9,
    'normal',
    '#8A8272',
  )
  y += 2

  // Disclaimer box
  ensure(16)
  doc.setFillColor(243, 226, 219)
  doc.setDrawColor(229, 201, 189)
  doc.roundedRect(margin, y, maxW, 12, 2, 2, 'FD')
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(9)
  doc.setTextColor('#1C1B18')
  doc.text(`⚠ ${DISCLAIMER}`, margin + 3, y + 7.5)
  y += 18

  // Recommendation
  if (best) {
    const conf = formatConfidencePct(best.confidence) ?? '—'
    ensure(28)
    doc.setFillColor(228, 237, 230)
    doc.setDrawColor(198, 216, 203)
    const recoLines = [
      `Recommended empiric choice: ${best.antibiotic} — predicted effective (${conf}% confidence).`,
      `${fails.length} of ${report.results.length} tested agents predicted to fail: ${
        fails.length ? fails.map((r) => r.antibiotic).join(', ') : 'none'
      }.`,
      ...nocalls.map((r) => `${r.antibiotic} returned no-call (insufficient evidence).`),
    ]
    const wrapped = recoLines.flatMap((t) => doc.splitTextToSize(t, maxW - 6) as string[])
    const boxH = wrapped.length * 5 + 8
    doc.roundedRect(margin, y, maxW, boxH, 2, 2, 'FD')
    doc.setTextColor('#2C5E3A')
    doc.setFontSize(10)
    doc.text(wrapped, margin + 3, y + 6)
    y += boxH + 6
  } else {
    ensure(22)
    doc.setFillColor(240, 233, 220)
    doc.setDrawColor(226, 213, 188)
    const warn = [
      'No tested agent is predicted to work — escalate and await culture.',
      fails.length
        ? `${fails.length} of ${report.results.length} tested agents predicted to fail: ${fails
            .map((r) => r.antibiotic)
            .join(', ')}.`
        : '',
      ...nocalls.map((r) => `${r.antibiotic} returned no-call (insufficient evidence).`),
    ].filter(Boolean)
    const wrapped = warn.flatMap((t) => doc.splitTextToSize(t, maxW - 6) as string[])
    const boxH = wrapped.length * 5 + 8
    doc.roundedRect(margin, y, maxW, boxH, 2, 2, 'FD')
    doc.setTextColor('#7A5A2E')
    doc.setFontSize(10)
    doc.text(wrapped, margin + 3, y + 6)
    y += boxH + 6
  }

  line('Per-agent results', 12, 'bold', '#1C1B18')
  y += 1

  for (const r of report.results) {
    const conf = formatConfidencePct(r.confidence)
    const genes = geneNames(r)
    const gate = gateLabel(r.gate)
    const block = [
      `${r.antibiotic} — ${r.call}`,
      `Confidence: ${conf != null ? conf + '%' : '—'} · p(resistant) = ${formatProbFail(r.prob_fail)}`,
      `Evidence: ${EV_LABEL[r.evidence_type ?? ''] ?? '—'}`,
      genes ? `Resistance gene(s): ${genes}` : '',
      r.note ? r.note : '',
      gate ? `Drug-target check: ${gate}` : '',
    ].filter(Boolean)

    const wrapped = block.flatMap((t) => doc.splitTextToSize(t, maxW - 6) as string[])
    const boxH = wrapped.length * 4.6 + 7
    ensure(boxH + 4)
    doc.setFillColor(255, 253, 249)
    doc.setDrawColor(201, 193, 177)
    doc.roundedRect(margin, y, maxW, boxH, 2, 2, 'FD')
    // accent bar
    const bar =
      r.call === 'likely to fail' ? [188, 75, 38] : r.call === 'likely to work' ? [44, 94, 58] : [122, 90, 46]
    doc.setFillColor(bar[0], bar[1], bar[2])
    doc.rect(margin, y, 1.5, boxH, 'F')
    doc.setTextColor('#1C1B18')
    doc.setFontSize(9)
    doc.setFont('helvetica', 'normal')
    doc.text(wrapped, margin + 4, y + 5)
    y += boxH + 4
  }

  y += 2
  ensure(14)
  doc.setFillColor(243, 226, 219)
  doc.setDrawColor(229, 201, 189)
  doc.roundedRect(margin, y, maxW, 12, 2, 2, 'FD')
  doc.setFontSize(9)
  doc.setTextColor('#1C1B18')
  doc.text(`⚠ ${DISCLAIMER}`, margin + 3, y + 7.5)

  return doc
}

export function downloadReportPdf(opts: ReportBundle): void {
  const doc = buildPdf(opts)
  doc.save(`${fileBase(opts.genomeId)}.pdf`)
}

export function buildShareText(opts: ReportBundle): string {
  const { report, genomeId, analyzedAt, best, fails, nocalls } = opts
  const lines = [
    'GenoWall — genomic resistance report',
    `Isolate: ${genomeId}`,
    `Species: ${report.species}`,
    `Analyzed: ${formatReportTimestamp(analyzedAt)}`,
    '',
  ]
  if (best) {
    const conf = formatConfidencePct(best.confidence) ?? '—'
    lines.push(
      `Recommended empiric choice: ${best.antibiotic} (${conf}% confidence).`,
      `Predicted to fail (${fails.length}/${report.results.length}): ${
        fails.map((r) => r.antibiotic).join(', ') || 'none'
      }.`,
    )
  } else {
    lines.push('No tested agent is predicted to work — escalate and await culture.')
  }
  for (const r of nocalls) {
    lines.push(`${r.antibiotic}: no-call (insufficient evidence).`)
  }
  lines.push(
    '',
    `⚠ ${DISCLAIMER}`,
    '',
    'Tip: Use Download PDF in GenoWall and attach the file to this email.',
    '',
    '— Sent from GenoWall',
  )
  return lines.join('\n')
}

/** Share via system sheet (with PDF when supported), else open a mailto draft. */
export async function shareReport(opts: ReportBundle): Promise<'shared' | 'mailto' | 'copied'> {
  const text = buildShareText(opts)
  const subject = `GenoWall report — ${opts.genomeId}`
  const doc = buildPdf(opts)
  const blob = doc.output('blob')
  const file = new File([blob], `${fileBase(opts.genomeId)}.pdf`, { type: 'application/pdf' })

  if (typeof navigator !== 'undefined' && typeof navigator.share === 'function') {
    try {
      const data: ShareData = { title: subject, text, files: [file] }
      if (navigator.canShare?.(data)) {
        await navigator.share(data)
        return 'shared'
      }
      await navigator.share({ title: subject, text })
      return 'shared'
    } catch (e) {
      // User cancelled — don't fall through to mailto
      if (e instanceof DOMException && e.name === 'AbortError') throw e
    }
  }

  const mailto = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(text)}`
  // mailto length limits — if too long, copy instead
  if (mailto.length < 1800) {
    window.location.href = mailto
    return 'mailto'
  }
  await navigator.clipboard.writeText(text)
  return 'copied'
}
