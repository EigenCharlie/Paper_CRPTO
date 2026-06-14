# Fernandez-Loria and Provost (2022) - reading note

Source PDF:

- Local ignored archive: `Papers_tesis/paper/Fernandez-Loria Provost 2022 - Causal Decision Making and Causal Effect Estimation Are Not the Same and Why It Matters.pdf`
- User download checked: `C:\Users\carlos\Downloads\papers_nuevos\2104.04103v3.pdf`
- SHA-256: `72551FD3AD3FEA779BC114578680750ABBB2A619C02ECF56CB7705FB2900DF69`
- Bib key: `fernandezloria2022causaldecision`
- DOI: `10.1287/ijds.2021.0006`
- Pages inspected with PyMuPDF: 24

## What the paper contributes

The paper argues that causal decision making (CDM) and causal effect estimation
(CEE) are not the same task. Its key claim is that accurate effect-size
estimation is not necessary for accurate decision making when the operational
goal is treatment assignment. In the authors' framing, the estimand changes:
the model should be judged by whether it assigns the right action, not only by
whether it estimates individual effects precisely.

The abstract and introduction emphasize three implications:

1. The modeling objective should, where possible, optimize treatment assignment
   rather than effect-size accuracy.
2. Confounding affects decision quality differently from effect estimation
   quality; confounded data can sometimes be decision-useful.
3. A non-causal proxy target can sometimes support a useful decision rule,
   which explains why firms often use predictive models for intervention
   targeting even when those models are not causal models.

The paper does not mention credit, loans, Lending Club, portfolio selection, or
conformal prediction. Its value for CRPTO is conceptual rather than empirical.

## How CRPTO should use it

Use this source to support a narrow point in related work: prediction, effect
estimation, and downstream action are different objects. CRPTO uses the same
separation in a non-causal credit setting. The PD model is an input artifact;
the manuscript's claim is about the auditable portfolio decision and the
funded-set risk certificate.

Do not use this source as evidence that CRPTO estimates causal treatment
effects, that Lending Club decisions are causal interventions, or that the
portfolio policy has experimental policy value. Those would require a separate
design.

Action taken on 2026-06-14:

- Kept `fernandezloria2022causaldecision` in the manuscript.
- Rewrote the related-work sentence so the citation supports the estimand /
  assignment-rule distinction rather than a generic "prediction vs action"
  slogan.
- Kept the PDF in the ignored local literature archive instead of committing a
  copyrighted PDF under `docs/`.
