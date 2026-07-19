# Genome Firewall — 90-second demo script

*Spoken pace. Leave `[RESULTS]` for live metrics.*

---

**[0:00–0:15 — Problem]**

Labs take one to three days to say which antibiotic will work. Doctors guess in that window — and about one in five empiric choices is wrong. In many places, they never test at all and overuse broad-spectrum drugs. The genome already has the answer. Genome Firewall reads it — defensively, and honestly.

**[0:15–0:40 — Resistant genome: known-gene evidence]**

Here’s a resistant *Klebsiella* FASTA. We upload it.  
Watch meropenem: **likely to fail**, high calibrated confidence, evidence category **known resistance gene** — for example a KPC carbapenemase hit from AMRFinderPlus. Not a black box: the call is tied to a real mechanism.

**[0:40–1:00 — Borderline genome: no-call as a strength]**

Now a borderline or unfamiliar genome.  
The system returns **no-call** — weak, conflicting, or out-of-distribution evidence. That is the product working. Forcing a yes/no creates false confidence. Abstaining is safer for patients and for stewardship.

**[1:00–1:20 — Reliability + generalization]**

Here’s the **reliability plot** and held-out evaluation: `[RESULTS]`.  
Confidence tracks real accuracy. And because we split by **homology groups**, these numbers are about generalization to unseen genetic clusters — not memorizing near-duplicates.

**[1:20–1:30 — Close]**

Defensive only. Decision support only. Every result: **confirm with standard lab testing.** That’s Genome Firewall.

---

**Props checklist**

- [ ] Demo FASTA with clear known-gene resistance (e.g. meropenem / KPC story)
- [ ] Borderline or OOD FASTA that triggers no-call
- [ ] Reliability plot + per-group table ready (`[RESULTS]`)
- [ ] Lab-confirmation banner visible on screen
