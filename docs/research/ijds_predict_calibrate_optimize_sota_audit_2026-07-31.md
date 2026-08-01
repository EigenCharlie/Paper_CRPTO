# IJDS predict--calibrate--optimize state-of-the-art audit (2026-07-31)

Status: literature and narrative-governance document. It is not an empirical
evidence source, does not activate a method or claim, and does not modify the
active evidence registry.

## Question and search boundary

This audit asks what the current literature actually supplies when a machine-
learning output is calibrated, conformalized, or otherwise uncertainty-
quantified and then passed to an optimizer. It uses the exact local PDFs and
primary proceedings/arXiv records inventoried in
`ijds_literature_corpus_ledger_2026-07-30.md`. The search snapshot is current
through 2026-07-31 but is not a universal nonexistence proof.

Dispositions have the following operational meaning:

- **A -- cite now:** a primary source whose scoped result directly clarifies
  the active manuscript's comparison or identification boundary.
- **B -- design/context:** a useful construction or diagnostic that belongs in
  limitations, discussion, or a prospectively locked redesign; it is not an
  active repair.
- **C -- watchlist:** an early, nonconformal, empirically under-validated, or
  otherwise nontransferable neighbor. Keep its exact metadata and PDF, but do
  not use it as affirmative support for an active CRPTO claim.

## Primary-source metadata adjudication

| Work | Exact primary record | Disposition | Metadata or use correction |
|---|---|---|---|
| Johnstone and Cox, *Conformal Uncertainty Sets for Robust Optimization* | PMLR 152:72--90, Tenth Symposium on Conformal and Probabilistic Prediction and Applications, 2021 | A | The prior BibTeX named the wrong conference and pages 1--19. The PMLR record fixes the venue, pages, editors, and publisher. |
| Sun, Liu, and Li, *Predict-then-Calibrate: A New Perspective of Robust Contextual LP* | arXiv:2305.15686v4, revised 2024-05-10 | A | Pin v4 and 2024. Its split separates prediction from risk/robustness calibration; it does not imply that ordinary probability calibration is a decision certificate. |
| Lekeufack et al., *Conformal Decision Theory* | ICRA 2024, pp. 11668--11675, DOI `10.1109/ICRA57147.2024.10610041` | B | The prior entry was an arXiv preprint dated 2023. It is a published online/adaptive risk-control construction, not selected-set validity for a retrospective credit archive. |
| Zhao et al., *Calibrating Predictions to Decisions* | NeurIPS 2021, volume 34, pp. 22313--22324 | A | Decision calibration is relative to declared losses and decision rules. It is not conformal prediction and cannot be silently exported from one decision class to another. |
| Im, Benslimane, and Grigas, *Smart Surrogate Losses for Contextual Stochastic Linear Optimization with Robust Constraints* | NeurIPS 2025, volume 38, pp. 75149--75174 | A | The closest current integrated-learning neighbor for uncertain constraints. Its conformal set is supplied upstream; the paper learns objective coefficients through SPO-RC/SPO-RC+ and states restrictive Fisher-consistency conditions. |
| Angelopoulos, *Conformal Risk Control for Non-Monotonic Losses* | arXiv:2602.20151v1 | B | Extends risk control through algorithmic stability. It requires exchangeability, symmetry, a full-data reference algorithm that already controls risk, and an explicit stability remainder. |
| Caunhye, Lu, and Martin-Barragan, *Smart predict-then-robustly-optimize* | arXiv:2607.21773v1 | C | Robustifies the SPO pipeline against feature perturbations. It is not a conformal or calibration method, and its surrogate analysis relies on declared structural and sub-Gaussian assumptions. |
| Guo, *Learning Predictive Ambiguity Sets for Decision-Focused DRO* | arXiv:2607.09820v1 | C | Learns a context-dependent Wasserstein radius using prediction, quantile, size, and decision losses. The seven-page v1 has no coverage theorem and explicitly reports below-nominal empirical coverage after decision-aware tuning. |
| Ziliaskopoulos, Vinel, and Smith, *Decision-Value Attribution in Predict-then-Optimize Systems* | arXiv:2606.29878v1 | B | Explains value in a fixed prediction--optimization pipeline. It supports the distinction between predictive and decision relevance, but its Shapley results are diagnostic, background-dependent, and noncausal. |

Primary surfaces checked:

- <https://proceedings.mlr.press/v152/johnstone21a.html>
- <https://arxiv.org/abs/2305.15686v4>
- <https://doi.org/10.1109/ICRA57147.2024.10610041>
- <https://proceedings.neurips.cc/paper_files/paper/2021/hash/bbc92a647199b832ec90d7cf57074e9e-Abstract.html>
- <https://proceedings.neurips.cc/paper_files/paper/2025/hash/6cc2e83abc493d8f7db72c3da1feccb8-Abstract-Conference.html>
- <https://arxiv.org/abs/2602.20151v1>
- <https://arxiv.org/abs/2607.21773v1>
- <https://arxiv.org/abs/2607.09820v1>
- <https://arxiv.org/abs/2606.29878v1>

### Citation surface for the six-object 2026-07-31 intake

| Object | Recommended surface now | Boundary |
|---|---|---|
| Zhao et al. (2021) | Body and supplement | Cite for the definition and restricted-family nature of decision calibration, not for conformal or funded-set validity. |
| Im, Benslimane, and Grigas (2025) | Body and supplement | Cite as the closest integrated robust-constraint/SPO neighbor, with the upstream-set and Fisher-consistency qualifications visible. |
| Angelopoulos (2026) | Body prospective-design boundary and supplement | Cite only for the stability route to non-monotonic risk control and enumerate the unmet premises. |
| Ziliaskopoulos, Vinel, and Smith (2026) | Supplement/context | Use for the predictive-value versus decision-value distinction, never as a guarantee or causal result. |
| Caunhye, Lu, and Martin-Barragan (2026) | Watchlist only | No present CRPTO claim concerns robust covariate perturbation under its assumptions. |
| Guo (2026) | Watchlist only | The current v1 is empirical, single-split, and below nominal after tuning; it is not affirmative calibration evidence. |

## What each pipeline calibrates

| Pipeline family | Object learned or calibrated | Downstream role | Guarantee actually supplied | Why it does not automatically solve CRPTO |
|---|---|---|---|---|
| Probability-to-decision calibration (Zhao et al.) | Class-probability predictions relative to a declared family of losses and decision rules | Bayes actions and loss estimation for that family | Decision-calibration approximation/sample-complexity results for bounded action classes | The active binary conformal set is not a decision-calibrated probability vector; the funded LP and dollar-weighted error target were not the paper's calibrated decision family. |
| Predict-then-calibrate contextual LP (Sun et al.) | Residual/uncertainty layer after an arbitrary predictor | Robust or distributionally robust contextual LP | Generalization/risk bounds under its split and contextual-LP assumptions | A prospective independent calibration split and the paper's uncertainty construction would be required; Platt calibration alone is not this layer. |
| Conformal uncertainty set to robust optimization (Johnstone--Cox; Patel et al.) | Multivariate response-region geometry | Worst-case robust feasible/objective set | Finite-sample region coverage under the source construction and exchangeability contract | CRPTO has a binary label set whose arbitrary continuous embedding is not identified by coverage. A robust optimizer cannot recover missing endpoint geometry. |
| Direct decision/risk calibration (Lekeufack et al.; Angelopoulos) | Online control parameter or a generic possibly multidimensional risk parameter | Directly adjusts a decision or algorithm | Long-run/expected-risk control under the respective online or stability contract | The historical archive lacks prompt feedback, verified target exchangeability, and a proved stability/reference-algorithm layer. |
| SPO with robust uncertain constraints (Im et al.) | Objective-cost predictor, with a contextual uncertainty set for constraint coefficients | Contextual robust LP; feasibility-sensitive SPO loss | Fisher consistency of SPO-RC+ under uniqueness, central symmetry, continuity, and interiority assumptions | The uncertainty set is learned separately, the theorem is not a selected-set conformal guarantee, and the active credit LP does not satisfy those assumptions by declaration. |
| Feature-robust SPO (Caunhye et al.) | Objective predictor robust to perturbations in covariates | Robustly trained PtO objective | Convex surrogate and probabilistic approximation results under feature-perturbation assumptions | It treats a different uncertainty source and has no conformal calibration, delayed-label, or funded-set theorem. |
| Learned predictive ambiguity set (Guo) | Nominal scenario distribution, state-dependent Wasserstein radius, optional metric | Differentiable DRO layer | Empirical portfolio comparison only in v1; no coverage theorem | Decision-aware tuning itself lowers empirical coverage below nominal in the reported experiment; a new post-calibration layer is acknowledged as necessary. |
| Decision-value attribution (Ziliaskopoulos et al.) | Shapley allocation of realized or model-implied decision value | Explains a fixed PtO pipeline | Additive attribution relative to a chosen background/player game | It diagnoses rather than calibrates; it neither identifies causal improvement nor supplies prediction, conformal, or post-selection validity. |

## Consequences for the active paper

### 1. “Calibrated” is not one transferable property

The literature now makes the taxonomy sharper. Probability calibration,
decision calibration, conformal coverage, risk control, surrogate Fisher
consistency, and ambiguity-set tuning answer different questions. A paper can
possess one while lacking the others. In particular, Platt scaling calibrates a
binary score as a probability map on its fitting distribution; it does not
create Sun-style robust-contextual-LP calibration, Zhao-style calibration for a
declared decision catalog, or funded-set conformal validity.

### 2. The strongest adjacent methods construct a new decision-aware object

Johnstone--Cox construct multivariate conformal regions; Sun calibrates a
robustness layer; Zhao declares a loss/decision family; Im embeds a separately
constructed uncertainty set in robust constraints; Angelopoulos requires a
stable algorithm and full-data reference. None treats an arbitrary continuous
upper endpoint as if it were identified by a pre-existing binary set. This
supports CRPTO's framing as an audit of the prediction-to-decision handoff,
provided the manuscript does not claim uniqueness of that framing.

### 3. Optimization can amplify, ignore, or redirect predictive differences

The current decision-focused literature supports three distinct phenomena:

1. a predictor should sometimes be trained against downstream regret (SPO);
2. the uncertainty object should sometimes be calibrated against a declared
   decision or risk class (Zhao, Sun, Shekhar--Howard); and
3. a predictive change can be decision-inactive, while a smaller change near an
   optimizer boundary can be decisive (Ziliaskopoulos et al.).

These observations motivate CRPTO's comparator and feasible-direction audit.
They do not prove a direction of portfolio effect or select a preferred
embedding, calibrator, ruler, gamma, cap, or policy.

### 4. Selected/funded-set validity remains the central unclosed interface

None of the six newly adjudicated papers gives a drop-in guarantee for a
budget-coupled funded subset with dollar-weighted loss, delayed binary labels,
unresolved outcomes, and unverified temporal transport. Im et al. address
robust feasibility but not conformal validity after selection. Angelopoulos
offers a possible route only after proving exchangeability and algorithmic
stability for the exact selected-risk functional. Guo's v1 is cautionary:
joint decision-aware tuning can consume calibration unless an independent
post-calibration contract is added.

## Research actions implied by the audit

The literature supports the following prospective designs, not retrospective
claim upgrades:

1. **Decision-family lock.** Declare the finite policy/loss catalog first,
   reserve an independent calibration sample, and calibrate a simultaneous
   decision-relevant score. Zhao and Shekhar--Howard motivate this route.
2. **Constraint-native redesign.** If uncertainty enters the LP constraints,
   define the uncertain coefficient and its contextual set directly, then use
   an SPO-RC-like training/evaluation split. Do not treat a binary-set endpoint
   embedding as that construction.
3. **Post-selection risk route.** Define the exact funded count- or dollar-
   weighted loss, prove permutation symmetry and a usable stability bound for
   the solver, and identify a full-data reference rule before invoking
   non-monotonic conformal risk control.
4. **Temporal replication.** All of the above still require a genuinely later,
   untouched target origin or a law-level transport assumption. No method in
   this intake erases that requirement.
5. **Decision-value diagnostic.** DVA could be used only as an exploratory
   explanation of a frozen pipeline, with background distributions, player
   groups, approximation error, and noncausal status declared in advance.

No additional empirical run is justified merely because these papers exist.
Any implementation would create a new scientific object and therefore needs a
predeclared protocol, a distinct run tag, contained output paths, and explicit
promotion gates.

## Watchlist promotion gates

- **Caunhye et al.** Promote from C only if a manuscript claim specifically
  concerns corrupted covariates or feature-space robustness and the exact
  structural assumptions are relevant.
- **Guo.** Do not promote as affirmative calibration evidence unless a later
  version adds a defensible theorem or a properly nested post-calibration and
  multi-fold empirical design. The present below-nominal coverage must remain
  visible.
- **Ziliaskopoulos et al.** Promote from B to A only for a narrowly worded
  interpretability claim, never for calibration, causality, or uncertainty
  validity.

These dispositions should be rechecked if any version, venue, theorem, or
empirical design changes.
