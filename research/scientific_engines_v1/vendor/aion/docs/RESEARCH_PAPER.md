# Machine-checked rare-event sandwiches for infinite-state stochastic reaction networks

*Technical report for Project AION. Draft. Not peer reviewed. Novelty is provisional; see §3 and `NOVELTY_AUDIT.md`.*

## Abstract

We give a certificate format and a Lean 4-verified checker for two-sided bounds
\(L\le P_{x_0}(\tau_B<\tau_A)\le U\) on hitting probabilities of mass-action stochastic reaction networks on
\(\mathbb N^d\). The state space is infinite and the bounds hold for the infinite chain. An upper certificate is a
barrier function glued from three parts: an exact rational table on a finite box, a product-geometric tail
\(C\prod_i\rho_i^{x_i}\) outside it, and the constant 1 on the target. The generator inequality on the infinite exterior
is discharged by an exact factorisation of the generator on exponential functions, followed by a falling-factorial
sign test that is sound on entire orthant cells. A lower certificate is a subsolution table together with a
Foster–Lyapunov escape table. We prove in Lean that the checker is sound with respect to the
least-fixed-point hitting probability of the embedded jump chain. We also prove that this quantity equals an explicit path-sum
probability. On three model families, an untrusted synthesiser produces certificates with relative gaps \(U/L-1\)
between \(4\times10^{-8}\) and \(1.4\times10^{-5}\), for probabilities as small as \(8\times10^{-25}\). Four such certificates
are re-checked inside Lean. We also prove a relative-error transfer principle that explains why these gaps do not degrade as the event
becomes rarer. We formalise three negative results that delimit the method.

## 1. Problem

A mass-action network has species \(1..d\) and reactions \(r\) with reactant/product vectors
\(\alpha_r,\beta_r\in\mathbb N^d\) and rate constants \(k_r\in\mathbb Q_{\ge0}\). The propensity is
\(a_r(x)=k_r\prod_i (x_i)_{\alpha_{ri}}\), where \((x)_m\) is the falling factorial, and the update is
\(x\mapsto x-\alpha_r+\beta_r\). The formal generator is \((Lf)(x)=\sum_r a_r(x)(f(x+\nu_r)-f(x))\).
For a target \(B=\{x_{j_B}\ge \ell\}\) and a taboo \(A=\{\exists i\in Z: x_i=0\}\) (for example, extinction), we want exact rational
\(L,U\) with \(L\le P_{x_0}(\tau_B<\tau_A)\le U\) and \(U/L\) close to 1, even when \(P\) is extremely small.

**Semantics.** In Lean (`Core.lean`), `hitProb A B` is the supremum over \(n\) of the first-step iterates `hitN`.
`PathSemantics.lean` proves `hitN A B n x` \(=\sum_{\text{reaction words } w\in\iota^n}\mathrm{weight}(w)\,1[w \text{ hits } B \text{ before } A]\),
where the weights form a probability distribution. For the minimal CTMC, this is the probability of hitting \(B\) before \(A\) and
before explosion (standard, not formalised; see `TRUST_BOUNDARIES.md`). No nonexplosion assumption is needed.

## 2. Main results (all machine-checked unless marked)

**Theorem 1 (barrier).** If \(g\ge0\), \(g\ge1\) on \(B\) and \(Lg\le0\) off \(A\cup B\), then \(\mathrm{hitProb}\le g\)
everywhere. (`hitProb_le_of_supersolution`.) The proof is an induction on the iterates. It requires no integrability and
no optional stopping for unbounded \(g\). This is the classical minimal-solution argument.

**Theorem 2 (certified lower bound).** Suppose \(f\le C\), \(f\le1\) on \(B\), \(f\le0\) off \(D\cup B\), and \(Lf\ge0\) on \(D\), where
\(D\cap(A\cup B)=\emptyset\) and the total rate is positive on \(D\). Suppose also that there is \(V\ge0\) with \(LV\le-\text{totalRate}\) on \(D\). Then \(f\le\mathrm{hitProb}\).
(`le_hitProb_of_subsolution`.) The escape hypothesis is necessary (N1).

**Theorem 3 (Foster–Lyapunov exit bounds).** These are `expectedJumps_le` and `expectedTime_le`.

**Theorem 4 (relative error).** If \(f\le P\le g\) and \(g\le(1+\varepsilon)f\) at \(x_0\), then \(P\) is known to relative error
\(\varepsilon\). (`relative_error_of_sandwich`.)

**Theorem 5 (relative-error transfer).** Let \(v\) be harmonic on an escape-certified \(D\) disjoint from \(A\cup B\), with
\(v\le(1+\eta)\,\mathrm{hitProb}\) off \(D\). Then \(v\le(1+\eta)\,\mathrm{hitProb}\) on \(D\), and symmetrically for lower bounds.
(`relative_error_transfer_upper/lower`.) Consequently, the relative accuracy of a core/tail sandwich is controlled by the relative
accuracy of the tail on the interface, *not by the absolute size of \(P\)*. This is the mechanism behind the flat
relative gaps in Table 1. Note that the theorem does not guarantee that the tail can be made relatively accurate.
That depends on the model class (§7).

**Theorem 6 (assume–guarantee union bound).** `compositional_union_bound` gives the following. Let module barriers \(\varphi_i\circ\pi_i\) satisfy
local drift inequalities with every coupling rate bounded by an interval that is valid while no module is bad. Then
\(P(\text{some module is bad before }A)\le\sum_i\varphi_i(\pi_i x)\).

**Theorem R (robust affine families).** If the rates are affine in \(\theta\in\prod[lo_k,hi_k]\), then one function satisfying the
worst-case interval drift is a barrier for every \(\theta\). (`AffineFamily.robust_supersolution`.)

**Theorem 7 (exact exponential factorisation).** For \(e(x)=\prod\rho_i^{x_i}\),
\(L(Ce)=Ce\cdot P\), where \(P(x)=\sum_r k_r(\prod_i\rho_i^{\beta_{ri}-\alpha_{ri}}-1)\prod_i(x_i)_{\alpha_{ri}}\) (`genQ_expBar`).

**Theorem 8 (orthant cell check).** Shifting \(x=m+t\) expresses \(P\) in the falling-factorial basis in \(t\), with
nonnegative Vandermonde coefficients. If every resulting coefficient is \(\le0\), then \(P\le0\) on \(\{x\ge m\}\)
(`cellCheck_sound`). The test is finite and exact.

**Theorem 9 (checker soundness).** `checkUpper c = true` implies \(\mathrm{hitProb}\le c.g\) on all of \(\mathbb N^d\). The checker verifies:
- \(\ell\le\) the box size in direction \(j_B\), \(C>0\), \(\rho\ge1\), and \(C\rho_{j_B}^\ell\ge1\);
- at every box state: \(T\ge0\); \(Lg\le0\) at non-taboo, non-target states; and \(T\le Ce\) on the interface layer (states within one jump of the box faces \(i\neq j_B\));
- one cell check per face.

`checkLower A c = true` implies \(c.f\le\mathrm{hitProb}\). It checks \(V\ge0\) on the box, and, wherever \(F>0\): positive total rate, \(Lf\ge0\) and
\(LV\le-\text{totalRate}\). (`checkUpper_sound`, `checkLower_sound`.) In the gluing argument, the generator at box states is computed by the checker with the true glued function. At an exterior state \(y\), the cell check gives \(L(Ce)(y)\le0\). Every neighbour of \(y\) that falls back into the box lies in the interface layer, where \(T\le Ce\). Neighbours in the target have value \(1\le Ce\) because \(\rho\ge1\) and \(C\rho_{j_B}^\ell\ge1\). Hence \(g\le Ce\) at all neighbours while \(g(y)=Ce(y)\), and `gen_le_of_le_on_jumps` transfers \(Lg(y)\le0\).

**Theorem A.** For linear birth–death with \(0<\lambda<\mu\), \(P_x(\text{hit }N\text{ before }0)=\frac{(\mu/\lambda)^x-1}{(\mu/\lambda)^N-1}\),
for symbolic \(\lambda,\mu,N,x\) (`bd_exact`). Both directions are obtained from Theorems 1 and 2.

**Negative results.**
- N1 (`escape_certificate_necessary`).
- N2 (`gen_mul`, `leibniz_fails`): the generator has a carré-du-champ cross term, so products of module barriers are not
  locally checkable.
- N3 (`mm1_hits_surely`): in a stable queue, a level whose stationary mass is \((\lambda/\mu)^N\) is still hit almost surely.

Axioms: `propext`, `Classical.choice` and `Quot.sound` for all abstract theorems. The four concrete certificates also use `native_decide`.

## 3. Related work (abridged; see NOVELTY_AUDIT.md)

- FSP (Munsky–Khammash 2006) bounds the truncation error by the exit mass. sFSP (Gupta et al. 2017) uses Lyapunov functions to choose stationary truncations.
- Barrier certificates for stochastic systems go back to Kushner and Prajna–Jadbabaie–Pappas.
- The minimal-solution characterisation of hitting probabilities is textbook material (Norris).
- Probabilistic model checkers (PRISM, Storm) handle finite or truncated chains with floating-point or exact arithmetic, but do not handle infinite-state CRNs with certificates of this kind.
- Lean libraries for CRNs (Ripple, CRNT-Lean) were not inspected.
- The 2026 papers named in the project brief (partition bounds, filtered FSP, neural rare-event tracking, augmented-truncation perturbation bounds) were not accessible, and may overlap with our weighted-interface idea.

## 4. Algorithm (untrusted synthesis)

1. Choose a box and a tail template. Compute an approximate committor on the box by Gauss–Seidel in floating
   point, using a tail guess as the boundary data.
2. Grid-search \((C,\rho)\) so that the cell checks pass and the tail dominates the core on the interface.
3. Round the core values to dyadic rationals. Inflate the upper table by \((1+\eta)\) and deflate the lower table by \((1-\eta)\). Increase \(\eta\)
   (repair loop) until the exact checker accepts.
4. For the lower bound, compute an escape table \(V\) by solving \(LV=-\text{totalRate}-\delta\) on the support of \(F\).
5. Emit JSON. Optionally emit a Lean file whose theorem `sandwich` is closed by the soundness theorems and `native_decide`.

Nothing in steps 1–4 is trusted. In development, the checker rejected certificates produced by a buggy
synthesiser (`NEGATIVE_RESULTS.md`).

## 5. Experiments

Table 1 (from `results/summary.md`; full details in `PERFORMANCE.md`):

| model | event | P | U/L−1 |
|---|---|---|---|
| A: X→2X (1), X→0 (2) | X: 1 → N before 0, N=10..80 | 9.8e-4 … 8.3e-25 | 4e-8 … 4.6e-7 |
| B: gene expression (mRNA, protein) | P: 1 → N before P=0, N=40/60/80 | 6.1e-6 / 1.7e-9 / 2.3e-13 | 2.7e-7 / 3.8e-7 / 1.4e-5 |
| C: X→2X, X→0, ∅⇄Y, X+Y→Y | X: 1 → N before 0 (Y₀=10), N=20..60 | 5.1e-6 … 2.8e-13 | 2.2e-7 … 5.7e-7 |

* For Example A, every interval contains the exact value.
* The same-box FSP upper bound for C at N=60 overestimates by 84%. For a smaller box (30×22), FSP is uninformative (7e-4), while
  our bound stays at relative gap 6.4e-4.
* SSA with \(2\times10^4\) runs observes no events for any \(P\le10^{-6}\).
* Robust ±1%/±5% certificates on all five rates of C give \(U=7.58\times10^{-8}/1.03\times10^{-6}\), matching the extreme constant-parameter certificates.

## 6. Complexity

Checking is linear in certificate size: \(O(nR)\) for a box with \(n\) states and \(R\) reactions, plus \(O(R(k+1)^d)\) per cell.
We have **no** proof that competing methods need asymptotically more resources. The advantage shown is a constant factor
and a box-size advantage over same-box FSP, together with the certified relative accuracy that SSA cannot provide at equal budget.

## 7. When does the method work?

The tail template works when the committor decays (asymptotically) geometrically in the directions that leave the box.
This holds for linear and catalytic degradation (A, B, C). By Theorem 5, the relative accuracy is inherited from the interface.
In our examples the interface lies in regions where \(P\) is already tiny relative to the core, so even a crude tail
contributes negligibly. The method fails or becomes loose for:
- events that are almost sure over an infinite horizon (N3);
- tails that are not geometric;
- targets on which the drift of the exponential has the wrong sign everywhere outside a bounded region.

We do not have a characterisation of this class. That is the main open mathematical question.

## 8. Limitations and trust

See `TRUST_BOUNDARIES.md`. Summary:
- no measure-theoretic CTMC in Lean;
- `native_decide` for the concrete certificates;
- the robust checker is not verified;
- no finite-horizon bounds;
- synthetic models only.

## 9. Conclusion

The project delivers a working, verified pipeline from network to machine-checked two-sided bounds on extremely small
hitting probabilities of infinite-state reaction networks. The mathematical ingredients are classical. Their combination
into a Lean-verified certificate format with falling-factorial tail checks is, to our knowledge, new, subject to the
unread 2026 literature. We assess the work as a solid formalisation and tooling contribution with modest
mathematical novelty, not a breakthrough.

## Reproduction

`lake build`, then `python3 scripts/run_all.py --lean` (see `REPRODUCIBILITY.md`).
