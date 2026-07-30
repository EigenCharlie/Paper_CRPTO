# IJDS funded-selection estimand audit V1 protocol (2026-07-29)

## Status and disclosure

This protocol is **retrospectively locked after complete inspection of the
candidate numerical results and before any clean tagged execution**. Preliminary
calculations already exposed the direction and approximate range of several
results. They are not success gates, preregistered hypotheses, confirmatory
tests, or grounds for selecting cells. The clean replay must retain all 96
policy tracks and all 48 gamma endpoint pairs. Its exact tag is
`protocol/ijds-funded-selection-estimand-audit-2026-07-29-v1`.

Two pre-lock exploratory code paths produced slightly different pooled
count-selected coverage ranges. An early scratch result was reported as
approximately 0.6793--0.8959 lower and 0.7054--0.9267 upper. The later
lineage-repaired implementation probe gave 0.6800554017--0.8948717949 lower
and 0.7056786704--0.9269230769 upper. This discrepancy is itself disclosed and
is why only the clean, exact-source replay can supply the reported values. Both
probes found count-selected coverage above
invested-dollar-selected coverage in all 96 tracks and an identified
count-selected gamma1-minus-gamma0 FCP sign in all 48 pairs (40 higher, 8
lower). They also found that replacing the continuous support by the registered
USD 25 support removed 8 positions, changed 2,985 positions under V3's
`1e-8` rule, changed only 8 track counts by one, and moved a fixed-capital FCP
endpoint by at most about 0.000185. These observations forced full disclosure
and the exhaustive census; none is an acceptance threshold for the clean
replay.

The exercise is a finite-archive audit of an already frozen allocation. It does
not claim selection-conditional conformal validity, false-coverage-rate (FCR)
control, exchangeability, causal effects, or prospective performance.

## Why this front is worth running

The active allocation-granularity audit evaluates miscoverage contributions
against common committed capital (USD 1 million monthly, USD 15 million pooled),
with residual cash retained. This fixed-capital decision estimand is distinct
from both conditional weighting among invested dollars and the false coverage
proportion used in selected-inference work. A loan that
receives USD 25 and one that receives USD 25,000 each count once in binary FCP,
while they receive different weights in both dollar estimands. This audit measures
that estimand dependence without relabeling any target as another.

The USD 25 floor-with-cash V3 artifact supplies a deterministic, outcome-free
binary support. It removed only 8 of 143,175 positive continuous positions and
retained 143,167 positions across all 1,440 monthly portfolios. This registered
support avoids inventing a new positive-exposure cutoff after seeing outcomes.
The exact historical implementation was
$25\lfloor(\max(a,0)+10^{-8})/25\rfloor$; the same $10^{-8}$ is used when
counting an exposure as changed. The clean replay must reproduce that rule,
prove that every omitted row maps to zero, and reconcile the complete 143,175-row
parent support one-to-one with the V5 outcome join before using any endpoint.

## Literature boundary

Jin and Ren's JOMI construction targets focal selection-conditional coverage by
recomputing a permutation-invariant selection rule after calibration--test
swaps and forming target-specific reference sets. Strong conditioning, such as
conditioning on the selected-set size, can imply FCR control; weak focal
coverage alone need not. The current study does not satisfy that contract:

1. its frozen calibration loans are from 2012 whereas target menus are from
   2016--2017, and the manuscript already rejects unqualified transport;
2. swapping a 2012 loan into a later issue-month menu violates chronology and
   the eligibility population;
3. the LP support depends on conformal endpoints and therefore on calibration
   labels, so the label-free black-box shortcut is unavailable;
4. a literal generic replay would require about 6.5 billion swap-and-resolve calls;
5. LP support would additionally need a deterministic immutable-ID tie rule.

Gazin et al.'s InfoSP/InfoSCOP procedures control FCR only under their monotone
informative-selection and iid/class-conditional contracts, with InfoSCOP using
an additional calibration split. An arbitrary fractional LP support is not an
InfoSP selection rule. Hegazy et al. select among several conformal predictors
for one target; that is not selection of funded units. These papers motivate the
binary estimand and make clear why the present output is descriptive, not a new
validity theorem.

## Frozen population and unit

For policy track $p=(w,r,c,\gamma)$, month $t$, and loan $i$, let

\[
Z_{itp}=1\{a^{(25)}_{itp}>0\},
\]

where $a^{(25)}$ is the registered V3 exposure after flooring each positive
allocation to USD 25 lots and holding the residual as cash. The binary selection
unit is one unique loan within one issue month and one policy. The 15-month
track estimand pools positions before division; it is not an average of monthly
ratios. Loan IDs must not repeat across issue months within a track.

The reference population is exactly the registered positive USD 25 support,
not all listed candidates and not the continuous LP's positive support. The
outcome and binary set endpoints come from the registered V5 post-freeze join.
The join key is `(id, window_id, role, period, candidate_id)`. Stored rowwise
miscoverage bounds must equal a fresh recomputation from the endpoints and the
nullable binary outcome.

## Three distinct estimands

For $S_i=[\ell_i,u_i]\cap\{0,1\}$, define
$M_i(y)=1\{y\notin S_i\}$. For a monthly cell or pooled track $G$,

\[
\operatorname{FCP}^{N}_G(y)=\frac{1}{N_G}\sum_{i\in G}M_i(y),\qquad
\operatorname{FCP}^{I\$}_G(y)=
\frac{\sum_{i\in G}a_iM_i(y)}{\sum_{i\in G}a_i}.
\]

These are the **count-selected** and **invested-dollar-selected** estimands. The
third, active granularity estimand is the **fixed-capital decision** functional

\[
\operatorname{FCP}^{B}_G(y)=
\frac{\sum_{i\in G}a_iM_i(y)}{B_G},
\]

where $B_G$ is USD 1 million for one month and USD 15 million for a pooled
track. The notation FCP is retained only to expose the common miscoverage
numerator; $\operatorname{FCP}^{B}$ is not a selected-unit false coverage
proportion because residual cash remains in its denominator. `Coverage = 1-FCP`
is reported separately under each denominator. Invested-dollar-selected coverage
must never be described as the active fixed-capital metric.

The audit reports both
$\operatorname{FCP}^{N}-\operatorname{FCP}^{I\$}$ and
$\operatorname{FCP}^{N}-\operatorname{FCP}^{B}$, with the same completion of
every unresolved binary outcome on both sides.

For each complete $(w,r,c)$ cell, the endpoint contrast is

\[
\Delta_\gamma=\operatorname{FCP}(\gamma=1)-
\operatorname{FCP}(\gamma=0),
\]

computed separately for count-selected, invested-dollar-selected, and
fixed-capital decision weights. A loan in the support union
receives one shared unresolved label under both policies. Missing support is
represented by zero weight. Bounds sum the rowwise minimum and maximum shared
contribution and are therefore sharp within each cell under unrestricted
loan-wise binary completion. They are not jointly sharp across the 96 tracks or
48 endpoint pairs.

## Complete outputs

The clean replay writes, without filtering or ranking:

1. 1,440 monthly policy summaries;
2. 96 pooled 15-month policy summaries;
3. 720 monthly gamma1-minus-gamma0 contrasts;
4. 48 pooled 15-month gamma1-minus-gamma0 contrasts; and
5. 96 exact support-and-fixed-capital reconciliations: continuous and rounded
   support counts, removed/added/changed counts, sharp count-selected
   rounded-minus-continuous bounds, and exact fixed-capital reconciliation to
   the registered V3 allocation-granularity artifact.

Every summary reports selected, resolved, unresolved, empty, full, and singleton
set counts; the three explicitly named FCP/coverage bounds; and the sharp shared-
completion count-minus-invested-dollar and count-minus-fixed-capital contrasts.
Every gamma output reports both supports,
their union and overlap, unresolved union count, all three estimand contrasts, and a
sign classification.

The clean summary may count bounds below the manuscript's 0.90 descriptive
reference. That comparison is not a funded-set nominal guarantee or a new test.

## Source identities

- V3 allocation freeze: 4,677 bytes,
  SHA-256 `cb66f9eedcd130d5d8f57cd182bcb83603df3fb2bdd8292244ec6a5f77d78c1d`.
- V3 continuous parent allocations: 3,180,848 bytes,
  SHA-256 `83870a9e0234289a46641f53f8857eeba5937ebdb8cd19b25eb56f7e8a8dfa81`.
- V3 rounded allocations: 3,209,311 bytes,
  SHA-256 `16b1e6496f86c3ea6f5cab7d6e32c68601cbcc448ab1fccfb5e83f75c610b7a2`.
- V3 allocation-granularity summary: 2,226 bytes,
  SHA-256 `7e8d9609367ae2cb07e9d0d56e676d7af5486258f7f36a2680d66d2f90d4b51a`.
- V3 granularity contrasts: 33,656 bytes,
  SHA-256 `12a91dbc69b4f666a16a6fe51524f13fb192a1122f8eab2f40fe38b50cd191a4`.
- V5 verified evaluation manifest: 18,231 bytes,
  SHA-256 `9ee55a2522349c8520f308bc69273774dd48964847dfd340b78a7be46474cd7f`.
- V5 joined funded allocations: 15,289,032 bytes,
  SHA-256 `2c95e0c8cec52f5be8d52084e7842f253e6a297a70cd6f413acde4065ec95d04`.

All seven are protected read-only inputs. The runner must accept an explicit
`--protected-read-root`, verify each descriptor and its nested manifest lineage
before reading parquet data, verify the same descriptors after computation, and
write only fresh atomic outputs.

## Predeclared Git artifact transport

The required artifact tag is
`artifacts/ijds-funded-selection-estimand-audit-2026-07-29-v1`. The runner must
exit with both summary and receipt marked `pending_git_artifact_commit`; it
does not itself create an artifact commit or tag. The serialized transport
contract contains repository-relative paths only and must not disclose the
execution checkout or protected materialization root.

The later artifact commit must be one single direct child of the protocol
commit. Its complete diff must equal exactly the seven declared output paths:
five parquet tables, the summary, and the receipt. No code, configuration,
protocol, source, DVC pointer, or unrelated path may be included. The required
artifact tag must resolve exactly to that direct-child commit. These outputs
are transported directly in Git with `dvc_required: false`; DVC is neither a
gate nor an authorized operation for V1. The calculation remains pending until
the direct-child relationship, exact path set, and tag are independently
verified.

## Deferred validity design (not executed by V1)

A future JOMI-compatible design would treat a loan-month position as selected
when a prospectively locked deterministic USD 25 policy gives it positive
exposure. Calibration and target loans would have to be sampled from the same
eligible issue-cohort population, or a defensible conditional exchangeability
statement would have to be proved. Conditioning only on the historical
2012-versus-2016/17 split is not sufficient.

For selected target (j) and candidate label (y\in\{0,1\}), the focal
reference set would contain calibration index (i) only when swapping (i)
and (j), inserting (y), and rerunning the entire deterministic selection
rule leaves (j) selected and the resulting selection belongs to the locked
taxonomy. Conditioning on exact selected-set size is the conservative taxonomy
needed to connect the focal statement to FCR. The algorithm would enumerate
both binary labels, construct the swap-specific reference scores, and apply the
JOMI order-statistic rule. Every solver tie would be resolved by an immutable-ID
rule and permutation invariance would be tested synthetically before execution.

That algorithm is not computationally justified on the present full grid: the
naive census is about 6.5 billion LP selections. It becomes a conditional GO
only for a new, smaller prospective design with a registered runtime budget and
same-population calibration. The label-free black-box shortcut may be used only
if the future selection rule is proved not to depend on calibration labels.
InfoSCOP is a separate possible route for a funded-and-reported subset, but it
would require its own independent split and monotone informative-set contract;
it would not validate the arbitrary current LP support retroactively.

## Fail-closed rules and compute decision

Stop without scientific output if the current HEAD is not clean and exactly
tagged, any source or nested descriptor changes, the V3 USD 25 contract changes,
any month/track/gamma cell is absent or duplicated, a loan repeats across months
within a track, the V3 parent and V5 join differ on any key/exposure/locked policy
metadata, a removed position does not floor to zero under the exact V3 rule,
endpoint or rowwise miscoverage reconciliation fails, any census differs,
implementation changes during execution, or an output directory exists.

**GO:** one linear-time clean replay of the complete deterministic USD 25 audit.
Expected cost is four parquet reads plus grouped vector operations over 143,175
continuous and 143,167 rounded selected rows and their gamma unions.

**NO-GO:** generic full-grid JOMI, an FCR-validity claim, or any selected subset
of the 96/48 cells. A future conditional GO would require a prospectively locked
same-population or independently split calibration design, a permutation-
invariant deterministic selection rule, and a procedure whose assumptions match
the desired JOMI/InfoSP/InfoSCOP guarantee.
