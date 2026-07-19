<script lang="ts">
  import type { DrugResult } from '../types'
  import { EV_LABEL } from '../types'
  import { formatConfidencePct, formatProbFail, gateLabel } from '../format'

  interface Props {
    result: DrugResult
    index?: number
  }
  let { result, index = 0 }: Props = $props()

  const styleMap: Record<string, { klass: string; label: string; color: string }> = {
    'likely to fail': { klass: 'fail', label: 'Likely to fail', color: 'var(--fail)' },
    'likely to work': { klass: 'work', label: 'Likely to work', color: 'var(--work)' },
    'no-call': { klass: 'nocall', label: 'No-call', color: 'var(--nocall)' },
  }

  const meta = $derived(styleMap[result.call] ?? styleMap['no-call'])
  const confPct = $derived(formatConfidencePct(result.confidence))
  const probLabel = $derived(formatProbFail(result.prob_fail))
  const geneNames = $derived(
    (result.detected_genes ?? []).map((g) => g.split(':').pop() ?? g),
  )
  const statNames = $derived(
    (result.statistical_features ?? []).map((f) => f.split(':').pop() ?? f),
  )
  const gate = $derived(gateLabel(result.gate))
  let open = $state(false)
</script>

<article class="card {meta.klass}" style="--i: {index}">
  <p class="eyebrow tag">{meta.label}</p>
  <h3 class="drug">{result.antibiotic}</h3>

  {#if confPct != null}
    <p class="small">confidence {confPct}%</p>
    <div class="track" aria-hidden="true">
      <div class="fill" style="width: {confPct}%; background: {meta.color}"></div>
    </div>
  {/if}

  <p class="small">p(resistant) = {probLabel}</p>
  <p class="small">Evidence: {EV_LABEL[result.evidence_type ?? ''] ?? '—'}</p>

  {#if geneNames.length}
    <div class="chip gene">Resistance gene(s): {geneNames.join(', ')}</div>
  {:else if result.call === 'likely to work'}
    <div class="chip none">No known resistance gene detected.</div>
  {:else if result.evidence_type === 'statistical_association_only'}
    <div class="chip stat">Statistical signal only: {statNames.join(', ') || '—'}</div>
  {/if}

  {#if result.call === 'no-call' && result.nocall_reason}
    <div class="chip stat">No-call: {result.nocall_reason}</div>
  {/if}

  <button
    type="button"
    class="details no-print"
    onclick={() => (open = !open)}
    aria-expanded={open}
  >
    {open ? 'Hide details' : 'Why / details'}
    <span aria-hidden="true">→</span>
  </button>

  <div class="why" class:collapsed={!open}>
    {#if result.note}<p>{result.note}</p>{/if}
    {#if result.prose}<p><strong>Summary:</strong> {result.prose}</p>{/if}
    {#if gate}<p><strong>Drug-target check:</strong> {gate}</p>{/if}
  </div>
</article>

<style>
  .card {
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: var(--r-card);
    box-shadow: var(--shadow-card);
    padding: 18px 18px 14px;
    animation: rise 0.55s cubic-bezier(0.22, 1, 0.36, 1) both;
    animation-delay: calc(var(--i) * 70ms);
    min-height: 100%;
    display: flex;
    flex-direction: column;
    break-inside: avoid;
  }
  .card.fail {
    border-top: 3px solid var(--fail);
  }
  .card.work {
    border-top: 3px solid var(--work);
  }
  .card.nocall {
    border-top: 3px solid var(--nocall);
  }

  .tag {
    margin: 0 0 6px;
  }
  .card.fail .tag {
    color: var(--fail);
  }
  .card.work .tag {
    color: var(--work);
  }
  .card.nocall .tag {
    color: var(--nocall);
  }

  .drug {
    margin: 0 0 10px;
    font-family: var(--font-display);
    font-size: 1.35rem;
    font-weight: 400;
    text-transform: capitalize;
    letter-spacing: -0.01em;
    color: var(--fg-ink);
  }

  .small {
    margin: 0.15rem 0;
    color: var(--fg-muted);
    font-size: 0.82rem;
  }
  .track {
    background: var(--bg-line);
    border-radius: var(--r-pill);
    height: 6px;
    overflow: hidden;
    margin: 0.25rem 0 0.5rem;
  }
  .fill {
    height: 100%;
    border-radius: var(--r-pill);
    transform-origin: left;
    animation: grow 0.8s cubic-bezier(0.22, 1, 0.36, 1) both;
    animation-delay: calc(var(--i) * 70ms + 120ms);
  }

  .chip {
    margin-top: 0.55rem;
    border-radius: var(--r-sm);
    padding: 0.45rem 0.65rem;
    font-size: 0.78rem;
    font-family: var(--font-mono);
    line-height: 1.35;
  }
  .chip.gene {
    background: var(--work-bg);
    border: 1px solid var(--work-line);
    color: var(--work);
  }
  .chip.none {
    background: var(--info-bg);
    border: 1px solid var(--info-line);
    color: var(--accent-deep);
  }
  .chip.stat {
    background: var(--nocall-bg);
    border: 1px solid var(--nocall-line);
    color: var(--nocall);
  }

  .details {
    margin-top: auto;
    padding-top: 0.85rem;
    align-self: flex-start;
    background: none;
    border: none;
    color: var(--accent);
    font-family: var(--font-body);
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .details:hover {
    color: var(--accent-hover);
  }

  .why {
    margin-top: 0.5rem;
    padding-top: 0.55rem;
    border-top: 1px solid var(--bg-line);
    font-size: 0.85rem;
    color: var(--fg-body);
    display: grid;
    gap: 0.4rem;
  }
  .why.collapsed {
    display: none;
  }
  .why p {
    margin: 0;
  }

  @media print {
    .why.collapsed {
      display: grid;
    }
    .card {
      box-shadow: none;
      animation: none;
    }
  }

  @keyframes rise {
    from {
      opacity: 0;
      transform: translateY(12px);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }
  @keyframes grow {
    from {
      transform: scaleX(0);
    }
    to {
      transform: scaleX(1);
    }
  }
</style>
