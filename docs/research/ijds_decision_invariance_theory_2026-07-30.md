# IJDS feasible-difference decision-invariance theory (2026-07-30)

## Status and authority

This is an active exact-theory note. It adds no empirical result, selects no
score or policy, and authorizes no selected-set or temporal-validity claim. The
active claim registry remains the prose authority and the V4 evidence manifest
remains the sole numeric authority.

The note answers a narrower question left open by the set-preserving-embedding
audit: when do two numeric score vectors define the same downstream linear
decisions? Equality of binary prediction sets is not the answer. The relevant
object is the restriction of each score functional to feasible allocation
differences.

## Setup

Let \(\mathcal A\subset\mathbb R^n\) be a nonempty convex set of allocations
before adding the score constraint, and define its feasible-difference space

\[
D=\operatorname{span}(\mathcal A-\mathcal A).
\]

For score vectors \(s,t\in\mathbb R^n\), say that they are *order-equivalent on
\(\mathcal A\)* when

\[
s^\top a\le s^\top b
\quad\Longleftrightarrow\quad
t^\top a\le t^\top b
\qquad\text{for every }a,b\in\mathcal A.
\]

This is stronger than giving the loans the same coordinatewise ranking. A
portfolio score is a linear average over allocations, so equivalence must hold
on allocation differences rather than only at unit-vector vertices.

## Exact characterization

**Theorem (feasible-difference score-order equivalence).** The following are
equivalent:

1. \(s\) and \(t\) are order-equivalent on \(\mathcal A\).
2. There are \(\kappa>0\) and \(h\in D^\perp\) such that

   \[
   t=\kappa s+h.
   \]

Equivalently, for any fixed \(a_0\in\mathcal A\), there is a constant
\(\delta=t^\top a_0-\kappa s^\top a_0\) such that

\[
t^\top a=\kappa s^\top a+\delta
\qquad\text{for every }a\in\mathcal A.
\]

If the affine hull of \(\mathcal A\) is exactly the full-budget hyperplane
\(\mathbf 1^\top a=B\), then \(D=\mathbf 1^\perp\) and the condition reduces to

\[
t=\kappa s+b\mathbf 1,\qquad \kappa>0,
\]

with portfolio-score offset \(\delta=bB\). More generally, if
\(\operatorname{aff}(\mathcal A)=\{a:Ea=d\}\), then
\(D^\perp=\operatorname{range}(E^\top)\). Only equalities defining the complete
affine hull belong in this term; a constraint that happens to bind at one
solution supplies at most a local condition.

### Proof

The positive-affine representation immediately preserves every pairwise weak
order because \(h^\top(a-b)=0\) for all \(a,b\in\mathcal A\).

For the converse, choose \(a_0\) in the relative interior of \(\mathcal A\).
Small displacements from \(a_0\) in every direction of \(D\) remain feasible.
Consequently, equality of weak orders on \(\mathcal A\), followed by positive
homogeneity, implies that the two linear functionals
\(d\mapsto s^\top d\) and \(d\mapsto t^\top d\) have the same zero set and the
same sign on all of \(D\). If the first functional is zero on \(D\), the second
must also be zero there; taking any \(\kappa>0\), for example \(\kappa=1\),
then gives \(t-\kappa s\in D^\perp\). Otherwise choose \(d_0\in D\) with
\(s^\top d_0=1\). For any \(d\in D\),
\(d-(s^\top d)d_0\) lies in the common kernel, and therefore

\[
t^\top d=(t^\top d_0)s^\top d.
\]

The common sign implies \(\kappa=t^\top d_0>0\). Thus
\((t-\kappa s)^\top d=0\) for every \(d\in D\), which is exactly
\(t-\kappa s\in D^\perp\).

## Consequences for the two rulers

Let \(v\) be the plug-in objective.
The cap-set identity below needs no existence assumption. For statements about
optimizers and ruler anchors, assume that the invoked feasible sets are
nonempty and the stated optima are attained, as they are on the bounded CRPTO
allocation polytope.

### Translated score caps

For any total-score cap \(K_s\), define \(K_t=\kappa K_s+\delta\). Under the
theorem's condition,

\[
\mathcal A\cap\{a:s^\top a\le K_s\}
=
\mathcal A\cap\{a:t^\top a\le K_t\}.
\]

With a common full budget \(B\), the corresponding per-dollar caps
\(\tau_s=K_s/B\) and \(\tau_t=K_t/B\) obey
\(\tau_t=\kappa\tau_s+\delta/B\). In the full-budget special case
\(t=\kappa s+b\mathbf1\), this becomes \(\tau_t=\kappa\tau_s+b\) because
\(\delta=bB\). Every subsequent objective therefore has the same complete
optimizer correspondence. Copying the same numerical cap is not the
translation unless the corresponding scale and offset make it so.

### Objective-matched ruler

For every common objective floor \(z\), put

\[
\mathcal A_z=\mathcal A\cap\{a:v^\top a\ge z\}.
\]

Because \(t^\top a=\kappa s^\top a+\delta\) on \(\mathcal A_z\),

\[
\arg\min_{a\in\mathcal A_z}s^\top a
=
\arg\min_{a\in\mathcal A_z}t^\top a.
\]

This is equality of the full optimal sets, not merely equality of one
solver-returned allocation.

### Normalized-score ruler

The minimum total score and the total score of a common
unconstrained-objective anchor transform as \(M_t=\kappa M_s+\delta\) and
\(O_t=\kappa O_s+\delta\). Hence, at coordinate \(\eta\),

\[
K_t(\eta)
=M_t+\eta(O_t-M_t)
=\kappa K_s(\eta)+\delta,
\]

so the two normalized cap sets and their optimizer correspondences coincide.
With full budget, the per-dollar caps
\(c_s(\eta)=K_s(\eta)/B\) and \(c_t(\eta)=K_t(\eta)/B\) satisfy
\(c_t(\eta)=\kappa c_s(\eta)+\delta/B\), or
\(c_t(\eta)=\kappa c_s(\eta)+b\) when \(t=\kappa s+b\mathbf1\).
This requires the same nonrisk allocation set and anchor. It does not extend a
full-budget additive invariance to a formulation in which cash changes the
affine hull.

## Why set preservation and unit ranking are insufficient

For the active contraction, when \(1\notin S_i\),
\(u_i=p_i+c_{g(i)}<1\), while loans with \(1\in S_i\) retain upper endpoint
one. Therefore, for \(\gamma>0\),

\[
q_i^{(\theta)}-q_i^{(0)}
=-\gamma\theta c_{g(i)}\mathbf 1\{1\notin S_i\}.
\]

Binary-set preservation constrains endpoint contact with zero and one. It does
not require the vector on the right to equal
\((\kappa-1)q^{(0)}+h\) for some \(h\in D^\perp\). The exact invariance
condition is

\[
q^{(\theta)}-\kappa q^{(0)}\in D^\perp
\quad\text{for some }\kappa>0.
\]

Failure of this condition means that no uniform decision-invariance theorem is
available. It does not mean that every evaluated cell must change: slack,
additional constraints, or a shared optimal face can make a particular
decision coincide.

### Complete compatible fibre and its rectangular robust limit

Require each bounded continuous interval to contain its center \(p_i\). For
\(0<\gamma\le1\), every coefficient compatible with the same binary set lies in

\[
q_i\in
\begin{cases}
\{p_i+\gamma(1-p_i)\},&1\in S_i,\\
[p_i,p_i+\gamma(1-p_i)),&1\notin S_i.
\end{cases}
\]

At \(\gamma=0\), \(q_i=p_i\). If
\(I=\{i:1\notin S_i\}\), the linear span of compatible coefficient differences
is \(\operatorname{span}\{e_i:i\in I\}\). The magnitude of the portfolio
functional is therefore identified over the feasible-difference space \(D\)
for every compatible embedding exactly when that coordinate subspace lies in
\(D^\perp\). Outside that condition, nonidentification permits but still does
not require a decision change.

Under rectangular loan-wise ambiguity and \(a_i\ge0\),

\[
\sup_{q\text{ compatible}}q^\top a
=\sum_i a_i\{p_i+\gamma(1-p_i)\}.
\]

For \(1\notin S_i\) this is generally a supremum over an open endpoint. At
\(\gamma=1\), the robust coefficient is one for every loan. A binding
full-budget cap below one is then infeasible; with optional cash the constraint
becomes only a cap on total invested capital and no longer ranks loans. This is
a consequence of robustifying over the entire unidentified fibre, not a
set-native validity result and not a jointly covered Cartesian uncertainty set.

Even a common coordinate ranking is insufficient. On the unit simplex, let

\[
s=(0,.6,1),\qquad t=s^2=(0,.36,1).
\]

The three loans have the same strict order under both scores, but
\(s^\top e_2=.6>s^\top(.5e_1+.5e_3)=.5\), whereas
\(t^\top e_2=.36<t^\top(.5e_1+.5e_3)=.5\). The two scores reverse the order of
two portfolios.

## Exact set-preserving counterexample

Take three loans with

\[
p=(.3,.1,.8),\qquad c=(.3,.6,.3).
\]

The original intervals are \([0,.6]\), \([0,.7]\), and \([.5,1]\). Full
contraction gives \([0,.3]\), \([0,.1]\), and \([.5,1]\). Both constructions
induce exactly the binary sets \(\{0\},\{0\},\{1\}\). At \(\gamma=1\), their
score vectors are

\[
q^{(0)}=(.6,.7,1),\qquad q^{(1)}=(.3,.1,1).
\]

On the unit simplex with \(v=(0,0,1)\), the normalized ruler at
\(\eta=.5\) gives

\[
a^{(0)}=(.5,0,.5),\qquad a^{(1)}=(0,.5,.5),
\]

and the objective-matched ruler at the common floor \(v^\top a\ge.25\) gives

\[
a^{(0)}=(.75,0,.25),\qquad a^{(1)}=(0,.75,.25).
\]

Thus both rulers can change allocations while binary sets and the attained
objective in the objective-matched example remain fixed.

## Fixed-set allocation-reweighting identity

If two embeddings preserve every \(S_i\), they also preserve every miss map
\(m_i(y)=\mathbf 1\{y\notin S_i\}\). For two fully invested allocations
\(a^\theta,a^0\) with common budget \(B\), every binary outcome completion
\(Y\) therefore satisfies

\[
\operatorname{MC}_\theta(Y)-\operatorname{MC}_0(Y)
=
\frac{1}{B}(a^\theta-a^0)^\top m(Y).
\]

The prediction set contributes no direct term: any funded-miscoverage change
comes from reallocating exposure across an unchanged miss map. Because
\(\mathbf1^\top(a^\theta-a^0)=0\), a constant miss vector cancels. The identity
does not supply a sign when miss indicators vary, a conformal guarantee on the
funded set, or a causal interpretation.

## Local invariance and degeneracy

For arbitrary fixed total-score caps \(K_s,K_t\), let

\[
F_s=\mathcal A\cap\{a:s^\top a\le K_s\},\qquad
F_t=\mathcal A\cap\{a:t^\top a\le K_t\}.
\]

Invariance for every linear objective is equivalent to \(F_s=F_t\). For one
declared objective \(v\), only equality of the exposed optimal faces is needed:

\[
\arg\max_{a\in F_s}v^\top a
=
\arg\max_{a\in F_t}v^\top a.
\]

Use the maximization convention

\[
N_F(a)=\{w:w^\top(x-a)\le0\ \text{for every }x\in F\}.
\]

For compact polytopes, a point \(a^\star\) is optimal for both problems if and
only if

\[
a^\star\in F_s\cap F_t,
\qquad
v\in N_{F_s}(a^\star)\cap N_{F_t}(a^\star).
\]

If \(a^\star\) is a vertex of both and \(v\) belongs to the relative interior
of both normal cones, it is the unique optimizer of both. Equality of the
complete exposed optimal face requires a common face \(G\) and
\(v\in\operatorname{ri}N_{F_s}(G)\cap\operatorname{ri}N_{F_t}(G)\). For
\(F_s=[0,1]^2\),
\(F_t=\operatorname{conv}\{(0,0),(1,0),(0,1)\}\), and \(v=(1,0)\), a solver can
return \((1,0)\) in both problems even though the first optimal face is a full
edge and the second is a singleton. A single common output therefore does not
establish equality of faces, uniqueness, or global score equivalence.
Conversely, non-equivalent scores can share an optimizer locally.

## Executable diagnostic and interpretation boundary

`src/ijds_audit/decision_score_equivalence.py` implements an SVD diagnostic on
a supplied finite allocation matrix. It projects both score vectors onto the
span of the supplied allocation differences and checks positive
proportionality there. It reports whether those rows span the complete
full-budget hull. Passing on a lower-dimensional set certifies only that
declared span; it says nothing about an unobserved feasible polytope.

The diagnostic is tested only on synthetic constructions in this change. It
must not be run against active evidence and promoted without a new protocol,
tag, complete finite scope, and registered output. The theorem does not select
an embedding, assert non-affinity in every active cell, require every allocation
to change, establish optimizer uniqueness, or transfer candidate-set validity
to selected or funded loans.
