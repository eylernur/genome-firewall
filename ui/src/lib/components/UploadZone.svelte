<script lang="ts">
  interface Props {
    disabled?: boolean
    onfile: (file: File) => void
  }
  let { disabled = false, onfile }: Props = $props()
  let drag = $state(false)
  let inputEl: HTMLInputElement | undefined = $state()

  function take(file: File | undefined) {
    if (!file || disabled) return
    onfile(file)
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    drag = false
    take(e.dataTransfer?.files?.[0])
  }
</script>

<div
  class="zone"
  class:drag
  class:disabled
  role="button"
  tabindex="0"
  ondragover={(e) => {
    e.preventDefault()
    drag = true
  }}
  ondragleave={() => (drag = false)}
  ondrop={onDrop}
  onclick={() => !disabled && inputEl?.click()}
  onkeydown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      if (!disabled) inputEl?.click()
    }
  }}
>
  <input
    bind:this={inputEl}
    type="file"
    accept=".fna,.fasta,.fa,.txt"
    hidden
    {disabled}
    onchange={(e) => take(e.currentTarget.files?.[0])}
  />
  <p class="eyebrow">Genome input</p>
  <p class="title">Upload a reconstructed FASTA</p>
  <p class="hint"><code>.fna</code> / <code>.fasta</code> · quality-checked assembly</p>
  <span class="cta">{disabled ? 'Running…' : 'Choose file'}</span>
</div>

<style>
  .zone {
    border: 1px solid var(--border);
    background: var(--bg-elevated);
    border-radius: var(--r-card);
    box-shadow: var(--shadow-card);
    padding: var(--space-4);
    text-align: left;
    cursor: pointer;
    transition:
      border-color 0.2s ease,
      transform 0.25s cubic-bezier(0.22, 1, 0.36, 1),
      box-shadow 0.2s ease;
  }
  .zone:hover:not(.disabled),
  .zone.drag {
    border-color: var(--accent);
    transform: translateY(-2px);
  }
  .zone.disabled {
    opacity: 0.65;
    cursor: wait;
  }
  .eyebrow {
    margin: 0 0 8px;
  }
  .title {
    margin: 0;
    font-family: var(--font-display);
    font-weight: 400;
    font-size: 1.35rem;
    color: var(--fg-ink);
  }
  .hint {
    margin: 0.4rem 0 1.1rem;
    color: var(--fg-muted);
    font-size: 0.9rem;
  }
  code {
    font-family: var(--font-mono);
    font-size: 0.85em;
  }
  .cta {
    display: inline-block;
    padding: 12px 24px;
    background: var(--accent);
    color: var(--bg-base);
    font-family: var(--font-body);
    font-weight: 500;
    font-size: 14px;
    border-radius: var(--r-pill);
    transition: background 0.15s ease;
  }
  .zone:hover:not(.disabled) .cta {
    background: var(--accent-hover);
  }
</style>
