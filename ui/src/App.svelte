<script lang="ts">
  import { predictGenome } from './lib/api'
  import type { DrugResult, PredictReport } from './lib/types'
  import { SCOPE } from './lib/types'
  import { formatConfidencePct, formatReportTimestamp } from './lib/format'
  import { downloadReportPdf, shareReport } from './lib/downloadReport'
  import UploadZone from './lib/components/UploadZone.svelte'
  import DrugCard from './lib/components/DrugCard.svelte'

  const DISCLAIMER =
    '⚠ Research prototype — confirm every result with standard laboratory testing.'

  let report = $state<PredictReport | null>(null)
  let genomeId = $state('')
  let source = $state<'api' | 'mock' | null>(null)
  let loading = $state(false)
  let error = $state('')
  let analyzedAt = $state<Date | null>(null)

  const counts = $derived.by(() => {
    if (!report) return { fail: 0, work: 0, nocall: 0 }
    return {
      fail: report.results.filter((r) => r.call === 'likely to fail').length,
      work: report.results.filter((r) => r.call === 'likely to work').length,
      nocall: report.results.filter((r) => r.call === 'no-call').length,
    }
  })

  const recommendation = $derived.by(() => {
    if (!report) return null
    const results = report.results
    const work = results
      .filter((r) => r.call === 'likely to work')
      .slice()
      .sort((a, b) => (b.confidence ?? -1) - (a.confidence ?? -1))
    const fails = results.filter((r) => r.call === 'likely to fail')
    const nocalls = results.filter((r) => r.call === 'no-call')
    const best: DrugResult | undefined = work[0]
    return { best, fails, nocalls, total: results.length }
  })

  async function onFile(file: File) {
    loading = true
    error = ''
    report = null
    analyzedAt = null
    genomeId = file.name.replace(/\.(fna|fasta|fa|txt)$/i, '')
    try {
      const out = await predictGenome(file)
      report = out.report
      source = out.source
      if (out.report.genome_id) genomeId = out.report.genome_id
      analyzedAt = new Date()
    } catch (e) {
      error = e instanceof Error ? e.message : String(e)
    } finally {
      loading = false
    }
  }

  function reportBundle() {
    if (!report || !recommendation || !analyzedAt) return null
    return {
      report,
      genomeId,
      analyzedAt,
      best: recommendation.best,
      fails: recommendation.fails,
      nocalls: recommendation.nocalls,
    }
  }

  function downloadReport() {
    const bundle = reportBundle()
    if (!bundle) return
    downloadReportPdf(bundle)
  }

  let shareNote = $state('')

  async function onShare() {
    const bundle = reportBundle()
    if (!bundle) return
    shareNote = ''
    try {
      const mode = await shareReport(bundle)
      if (mode === 'mailto') shareNote = 'Opening your email app…'
      else if (mode === 'copied') shareNote = 'Report summary copied — paste into an email.'
      else shareNote = ''
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') return
      shareNote = 'Could not share — try Download PDF instead.'
    }
  }

  function analyzeAnother() {
    report = null
    analyzedAt = null
    source = null
    error = ''
    shareNote = ''
  }
</script>

<div class="page">
  <!-- Landing hero: one composition -->
  <header class="hero no-print" class:compact={!!report}>
    <p class="eyebrow">Clinical decision support</p>
    <p class="brand">GenoWall</p>
    <h1>
      Genomic resistance prediction with calibrated confidence — days before culture results
      arrive.
    </h1>

    {#if !report}
      <div class="hero-upload">
        <UploadZone disabled={loading} onfile={onFile} />
        {#if loading}
          <p class="status-inline" aria-live="polite">
            Analyzing genome… this can take 1–2 minutes. Keep this tab open.
          </p>
        {/if}
        {#if error}
          <p class="error-inline" role="alert">{error}</p>
        {/if}
      </div>
      <p class="hero-proof">
        Validated on 4,416 genomes · AUROC 0.94–0.98 · balanced accuracy 0.93
      </p>
      <div class="banner strip slim" role="note">{DISCLAIMER}</div>
    {:else}
      <button type="button" class="analyze-again" onclick={analyzeAnother}>
        Analyze another genome →
      </button>
    {/if}
  </header>

  {#if report && recommendation && analyzedAt}
    <section class="report" id="print-report" aria-label="Decision report">
      <div class="report-toolbar">
        <span class="turnaround">⚡ Result in ~30 seconds · standard culture takes 2–3 days</span>
        <div class="actions no-print">
          <button type="button" class="btn ghost" onclick={onShare}>Share</button>
          <button type="button" class="btn solid" onclick={downloadReport}>Download PDF</button>
        </div>
      </div>
      {#if shareNote}
        <p class="share-note no-print" aria-live="polite">{shareNote}</p>
      {/if}

      {#if recommendation.best}
        {@const conf = formatConfidencePct(recommendation.best.confidence) ?? '—'}
        <div class="reco work">
          <p class="reco-main">
            ✓ Recommended empiric choice:
            <strong class="drug">{recommendation.best.antibiotic}</strong>
            — predicted effective ({conf}% confidence).
          </p>
          {#if recommendation.fails.length}
            <p class="reco-sub">
              {recommendation.fails.length} of {recommendation.total} tested agents predicted to
              fail: {recommendation.fails.map((r) => r.antibiotic).join(', ')}.
            </p>
          {:else}
            <p class="reco-sub">
              0 of {recommendation.total} tested agents predicted to fail.
            </p>
          {/if}
          {#each recommendation.nocalls as nc}
            <p class="reco-sub nocall-note">
              {nc.antibiotic} returned no-call (insufficient evidence).
            </p>
          {/each}
        </div>
      {:else}
        <div class="reco warn">
          <p class="reco-main">
            ⚠ No tested agent is predicted to work — escalate and await culture.
          </p>
          {#if recommendation.fails.length}
            <p class="reco-sub">
              {recommendation.fails.length} of {recommendation.total} tested agents predicted to
              fail: {recommendation.fails.map((r) => r.antibiotic).join(', ')}.
            </p>
          {/if}
          {#each recommendation.nocalls as nc}
            <p class="reco-sub nocall-note">
              {nc.antibiotic} returned no-call (insufficient evidence).
            </p>
          {/each}
        </div>
      {/if}

      <div class="stat-band">
        <div>
          <span class="lbl">Genome / isolate</span>
          <strong>{genomeId}</strong>
        </div>
        <div>
          <span class="lbl">Species</span>
          <strong>{report.species}</strong>
        </div>
        <div>
          <span class="lbl">Predicted to fail</span>
          <strong class="fail">{counts.fail}</strong>
        </div>
        <div>
          <span class="lbl">Predicted to work</span>
          <strong class="work">{counts.work}</strong>
        </div>
        <div>
          <span class="lbl">No-call</span>
          <strong class="nocall">{counts.nocall}</strong>
        </div>
      </div>

      <p class="meta-line">
        Analyzed {formatReportTimestamp(analyzedAt)} · Isolate {genomeId} · {report.species}
      </p>

      {#if source === 'mock'}
        <p class="coverage no-print">
          <em>Preview report (connect <code>VITE_API_URL</code> for live analysis)</em>
        </p>
      {/if}

      <div class="grid">
        {#each report.results as result, i}
          <DrugCard {result} index={i} />
        {/each}
      </div>

      <div class="banner strip foot" role="note">{DISCLAIMER}</div>
      <p class="footnote">
        A no-call abstains when evidence is weak, conflicting, or out of distribution — rather
        than forcing a false yes/no.
      </p>
    </section>
  {:else if !loading}
    <!-- Below-fold landing sections -->
    <section class="land no-print" aria-labelledby="how-title">
      <p class="eyebrow">How it works</p>
      <h2 id="how-title">Three steps from FASTA to a clinical call</h2>
      <ol class="steps">
        <li>
          <span class="step-n">01</span>
          <div>
            <strong>Read the genome</strong>
            <p>AMRFinderPlus scans for known resistance genes and mutations.</p>
          </div>
        </li>
        <li>
          <span class="step-n">02</span>
          <div>
            <strong>Predict with calibration</strong>
            <p>Per-drug models return work / fail / no-call with honest confidence.</p>
          </div>
        </li>
        <li>
          <span class="step-n">03</span>
          <div>
            <strong>Support the decision</strong>
            <p>Evidence and a recommended empiric choice — confirm with lab testing.</p>
          </div>
        </li>
      </ol>
    </section>

    <section class="land scope-land no-print" aria-labelledby="scope-title">
      <p class="eyebrow">Scope</p>
      <h2 id="scope-title">{SCOPE.species}</h2>
      <p class="scope-lede">Focused panel — one species, four agents, done well.</p>
      <ul class="drug-row">
        {#each SCOPE.antibiotics as drug}
          <li>{drug}</li>
        {/each}
      </ul>
      <p class="metrics">
        Validated on 4,416 genomes · AUROC 0.94–0.98 · balanced accuracy 0.93 · grouped by
        genetic lineage
      </p>
      <p class="defensive">{SCOPE.defensiveNote}</p>
    </section>
  {/if}

  <footer class="credit no-print">Built by Eyler Nur</footer>
</div>

<style>
  .page {
    position: relative;
    max-width: 720px;
    margin: 0 auto;
    padding: clamp(2.5rem, 8vh, 5rem) var(--space-3) var(--space-6);
    display: grid;
    gap: var(--space-5);
  }

  .hero {
    display: grid;
    gap: var(--space-3);
    min-height: min(72vh, 640px);
    align-content: center;
    animation: rise 0.6s cubic-bezier(0.22, 1, 0.36, 1) both;
  }
  .hero.compact {
    min-height: 0;
    padding-bottom: var(--space-2);
    border-bottom: 1px solid var(--bg-line);
  }
  .eyebrow {
    margin: 0;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--accent);
  }
  .brand {
    margin: 0;
    font-family: var(--font-display);
    font-weight: 400;
    font-size: clamp(3.4rem, 12vw, 5.5rem);
    line-height: 0.92;
    letter-spacing: -0.03em;
    color: var(--fg-ink);
  }
  h1 {
    margin: 0;
    max-width: 28ch;
    font-family: var(--font-display);
    font-weight: 400;
    font-size: clamp(1.25rem, 2.8vw, 1.65rem);
    line-height: 1.3;
    color: var(--fg-body);
  }
  .hero-upload {
    margin-top: var(--space-2);
    max-width: 420px;
  }
  .hero-proof {
    margin: 0;
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.04em;
    color: var(--fg-muted);
    max-width: 42ch;
  }
  .status-inline {
    margin: 0.75rem 0 0;
    color: var(--accent-deep);
    font-size: 0.92rem;
    font-weight: 500;
  }
  .error-inline {
    margin: 0.75rem 0 0;
    color: var(--accent-hover);
    font-size: 0.92rem;
    font-weight: 600;
  }
  .analyze-again {
    justify-self: start;
    margin-top: var(--space-2);
    background: none;
    border: none;
    padding: 0;
    color: var(--accent);
    font-family: var(--font-body);
    font-size: 0.95rem;
    font-weight: 500;
    cursor: pointer;
  }
  .analyze-again:hover {
    color: var(--accent-hover);
  }

  .banner.strip {
    border-radius: var(--r-md);
    padding: 10px 14px;
    background: var(--fail-bg);
    border: 1px solid var(--fail-line);
    color: var(--fg-ink);
    font-size: 0.88rem;
    font-weight: 500;
    line-height: 1.35;
    max-width: 42ch;
  }
  .banner.strip.slim {
    margin-top: var(--space-1);
  }
  .banner.foot {
    margin-top: var(--space-2);
    max-width: none;
  }

  .land {
    padding-top: var(--space-4);
    border-top: 1px solid var(--bg-line);
    animation: rise 0.55s cubic-bezier(0.22, 1, 0.36, 1) 0.08s both;
  }
  .land h2 {
    margin: 0.35rem 0 0.75rem;
    font-family: var(--font-display);
    font-weight: 400;
    font-size: clamp(1.5rem, 3vw, 1.85rem);
    color: var(--fg-ink);
  }
  .steps {
    list-style: none;
    margin: var(--space-4) 0 0;
    padding: 0;
    display: grid;
    gap: var(--space-4);
  }
  .steps li {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: var(--space-3);
    align-items: start;
  }
  .step-n {
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.08em;
    color: var(--accent);
    padding-top: 0.2rem;
  }
  .steps strong {
    display: block;
    font-family: var(--font-display);
    font-weight: 400;
    font-size: 1.2rem;
    color: var(--fg-ink);
    margin-bottom: 0.25rem;
  }
  .steps p {
    margin: 0;
    color: var(--fg-muted);
    font-size: 0.95rem;
    max-width: 36ch;
  }

  .scope-lede {
    margin: 0 0 var(--space-3);
    color: var(--fg-muted);
  }
  .drug-row {
    list-style: none;
    margin: 0 0 var(--space-3);
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .drug-row li {
    padding: 6px 12px;
    border-radius: var(--r-pill);
    border: 1px solid var(--border);
    background: var(--bg-elevated);
    font-size: 0.88rem;
    text-transform: capitalize;
    color: var(--fg-ink);
  }
  .metrics {
    margin: 0;
    font-size: 0.85rem;
    color: var(--fg-muted);
    max-width: 40ch;
  }
  .defensive {
    margin: var(--space-3) 0 0;
    font-size: 0.75rem;
    line-height: 1.4;
    color: var(--fg-muted);
    max-width: 42ch;
  }

  .lbl {
    display: block;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--fg-muted);
    margin-bottom: 4px;
  }

  .report-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-2);
    margin-bottom: var(--space-3);
  }
  .turnaround {
    display: inline-flex;
    align-items: center;
    padding: 6px 12px;
    border-radius: var(--r-pill);
    background: var(--bg-sunken);
    border: 1px solid var(--bg-line);
    color: var(--fg-body);
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.02em;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .btn {
    padding: 10px 18px;
    border-radius: var(--r-pill);
    font-family: var(--font-body);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
  }
  .btn.solid {
    border: none;
    background: var(--fg-ink);
    color: var(--bg-base);
  }
  .btn.solid:hover {
    background: #38352e;
  }
  .btn.ghost {
    border: 1px solid var(--border);
    background: var(--bg-elevated);
    color: var(--fg-ink);
  }
  .btn.ghost:hover {
    border-color: var(--accent);
    color: var(--accent);
  }
  .share-note {
    margin: -0.25rem 0 var(--space-3);
    font-size: 0.85rem;
    color: var(--fg-muted);
  }

  .reco {
    border-radius: var(--r-card);
    padding: 18px 20px;
    margin-bottom: var(--space-3);
    border: 1px solid var(--work-line);
    background: var(--work-bg);
  }
  .reco.warn {
    border-color: var(--nocall-line);
    background: var(--nocall-bg);
  }
  .reco-main {
    margin: 0;
    font-family: var(--font-display);
    font-size: 1.2rem;
    line-height: 1.35;
    color: var(--fg-ink);
  }
  .reco.work .reco-main {
    color: var(--work);
  }
  .reco.warn .reco-main {
    color: var(--nocall);
  }
  .reco-main .drug {
    text-transform: capitalize;
    color: inherit;
  }
  .reco-sub {
    margin: 0.45rem 0 0;
    font-size: 0.9rem;
    color: var(--fg-body);
  }
  .nocall-note {
    color: var(--nocall);
  }

  .coverage,
  .footnote {
    margin: 0;
    color: var(--fg-muted);
    font-size: 0.92rem;
  }
  .meta-line {
    margin: 0 0 var(--space-3);
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.02em;
    color: var(--fg-muted);
  }

  .stat-band {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-4);
    background: var(--accent);
    color: var(--bg-base);
    border-radius: 12px;
    padding: var(--space-4);
    margin-bottom: var(--space-2);
  }
  .stat-band .lbl {
    color: rgba(250, 247, 241, 0.72);
  }
  .stat-band strong {
    font-family: var(--font-display);
    font-size: 1.5rem;
    font-weight: 400;
    color: #fffdf9;
  }
  .stat-band .fail,
  .stat-band .work,
  .stat-band .nocall {
    color: #fffdf9;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: var(--space-3);
    margin: var(--space-3) 0;
  }

  .footnote {
    margin-top: var(--space-3);
    max-width: 58ch;
  }
  .credit {
    margin: var(--space-5) 0 0;
    padding-top: var(--space-3);
    border-top: 1px solid var(--bg-line);
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--fg-muted);
  }
  code {
    font-family: var(--font-mono);
    font-size: 0.85em;
  }

  @keyframes rise {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }

  @media (min-width: 900px) {
    .page {
      max-width: 880px;
    }
    .report .grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media print {
    :global(body) {
      background: white !important;
    }
    .page {
      max-width: none;
      padding: 0;
    }
    .no-print {
      display: none !important;
    }
    .stat-band,
    .reco,
    .banner.strip {
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
  }
</style>
