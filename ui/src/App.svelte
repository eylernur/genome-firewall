<script lang="ts">
  import { predictGenome } from './lib/api'
  import type { PredictReport } from './lib/types'
  import { SCOPE } from './lib/types'
  import UploadZone from './lib/components/UploadZone.svelte'
  import DrugCard from './lib/components/DrugCard.svelte'

  let report = $state<PredictReport | null>(null)
  let genomeId = $state('')
  let source = $state<'api' | 'mock' | null>(null)
  let loading = $state(false)
  let error = $state('')

  const counts = $derived.by(() => {
    if (!report) return { fail: 0, work: 0, nocall: 0 }
    return {
      fail: report.results.filter((r) => r.call === 'likely to fail').length,
      work: report.results.filter((r) => r.call === 'likely to work').length,
      nocall: report.results.filter((r) => r.call === 'no-call').length,
    }
  })

  async function onFile(file: File) {
    loading = true
    error = ''
    report = null
    genomeId = file.name.replace(/\.(fna|fasta|fa|txt)$/i, '')
    try {
      const out = await predictGenome(file)
      report = out.report
      source = out.source
    } catch (e) {
      error = e instanceof Error ? e.message : String(e)
    } finally {
      loading = false
    }
  }
</script>

<div class="page">
  <header class="hero">
    <p class="eyebrow">Clinical AI · Decision support</p>
    <p class="brand">GenoWall</p>
    <h1>Which antibiotics may fail — from one genome.</h1>
    <p class="lede">
      Per-drug work / fail / no-call with calibrated confidence and honest evidence,
      before culture results arrive.
    </p>
    <div class="hero-upload">
      <UploadZone disabled={loading} onfile={onFile} />
    </div>
  </header>

  <aside class="scope">
    <p class="eyebrow">Scope</p>
    <p class="scope-species"><span>Species</span> {SCOPE.species}</p>
    <ul>
      {#each SCOPE.antibiotics as drug}
        <li>{drug}</li>
      {/each}
    </ul>
    <p class="metrics">
      Held-out (backend): AUROC 0.94–0.98 · balanced acc ~0.93 · Brier ~0.045 · grouped by
      genetic similarity
    </p>
  </aside>

  <div class="banners">
    <div class="banner attention">
      <span class="dot"></span>
      <div>
        <strong>Confirm with lab testing</strong>
        <p>{SCOPE.labBanner}</p>
      </div>
    </div>
    <div class="banner deep">
      <p>{SCOPE.defensiveNote}</p>
    </div>
  </div>

  {#if error}
    <p class="error" role="alert">{error}</p>
  {/if}

  {#if loading}
    <p class="status" aria-live="polite">
      Annotating genome with AMRFinderPlus and predicting… this can take 1–2 minutes on the
      live API.
    </p>
  {/if}

  {#if report}
    <section class="report" aria-label="Decision report">
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

      <p class="coverage">
        {report.coverage_note}
        {#if source === 'mock'}
          <em>
            · Demo mode (mock report — set <code>VITE_API_URL</code> to call a backend)
          </em>
        {/if}
      </p>

      <div class="grid">
        {#each report.results as result, i}
          <DrugCard {result} index={i} />
        {/each}
      </div>

      <div class="banner attention foot">
        <span class="dot"></span>
        <div>
          <strong>Confirm with lab testing</strong>
          <p>{report.lab_banner}</p>
        </div>
      </div>
      <p class="footnote">
        A no-call is a strength, not a failure — it flags weak, conflicting, or
        out-of-distribution evidence rather than forcing a false yes/no.
      </p>
    </section>
  {:else if !loading}
    <p class="tip">
      Tip: BV-BRC <em>Klebsiella pneumoniae</em> genome FASTAs work well. Research prototype for
      demonstration.
    </p>
  {/if}
</div>

<style>
  .page {
    max-width: 1080px;
    margin: 0 auto;
    padding: var(--space-5) var(--space-3) var(--space-6);
    display: grid;
    gap: var(--space-4);
  }

  .hero {
    display: grid;
    gap: var(--space-2);
    animation: rise 0.55s cubic-bezier(0.22, 1, 0.36, 1) both;
  }
  .brand {
    margin: 0;
    font-family: var(--font-display);
    font-weight: 400;
    font-size: clamp(3rem, 8vw, 4.5rem);
    line-height: 0.95;
    letter-spacing: -0.02em;
    color: var(--fg-ink);
  }
  h1 {
    margin: 0;
    max-width: 20ch;
    font-family: var(--font-display);
    font-weight: 400;
    font-size: clamp(1.5rem, 3vw, 2rem);
    line-height: 1.2;
    color: var(--fg-body);
  }
  .lede {
    margin: 0;
    max-width: 40ch;
    color: var(--fg-muted);
    font-size: 1.05rem;
  }
  .hero-upload {
    margin-top: var(--space-3);
    max-width: 440px;
  }

  .scope {
    border-left: 2px solid var(--accent);
    padding-left: var(--space-3);
  }
  .scope-species {
    margin: var(--space-2) 0;
    font-family: var(--font-display);
    font-size: 1.25rem;
    color: var(--fg-ink);
  }
  .scope-species span,
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
  .scope ul {
    margin: 0 0 var(--space-2);
    padding-left: 1.1rem;
    color: var(--fg-body);
  }
  .scope li {
    text-transform: capitalize;
  }
  .metrics {
    margin: 0;
    font-size: 0.85rem;
    color: var(--fg-muted);
    max-width: 36ch;
  }

  .banners {
    display: grid;
    gap: var(--space-2);
  }
  .banner {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    border-radius: var(--r-md);
    padding: 14px 16px;
  }
  .banner p {
    margin: 2px 0 0;
    font-size: 0.9rem;
    font-weight: 400;
    line-height: 1.4;
  }
  .banner strong {
    font-family: var(--font-body);
    font-size: 0.9rem;
    font-weight: 600;
  }
  .banner.attention {
    background: var(--fail-bg);
    border: 1px solid var(--fail-line);
    color: var(--fg-ink);
  }
  .banner.attention .dot {
    width: 8px;
    height: 8px;
    margin-top: 6px;
    border-radius: 50%;
    background: var(--accent-hover);
    flex-shrink: 0;
  }
  .banner.deep {
    background: var(--accent-deep);
    border: 1px solid #1f4249;
    color: #dce7e5;
  }
  .banner.deep p {
    margin: 0;
    font-size: 0.88rem;
  }
  .banner.foot {
    margin-top: var(--space-2);
  }

  .status,
  .tip,
  .coverage,
  .footnote {
    margin: 0;
    color: var(--fg-muted);
    font-size: 0.92rem;
  }
  .error {
    margin: 0;
    color: var(--accent-hover);
    font-weight: 600;
  }

  .stat-band {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-4);
    background: var(--accent);
    color: var(--bg-base);
    border-radius: 12px;
    padding: var(--space-4);
    margin-bottom: var(--space-3);
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
      grid-template-columns: 1fr 240px;
      grid-template-areas:
        'hero scope'
        'banners banners'
        'main main';
      column-gap: var(--space-5);
    }
    .hero {
      grid-area: hero;
    }
    .scope {
      grid-area: scope;
      align-self: start;
      margin-top: 2.5rem;
    }
    .banners {
      grid-area: banners;
    }
    .report,
    .tip,
    .status,
    .error {
      grid-column: 1 / -1;
    }
  }
</style>
