# Exact all-integer ReLU certificates: constructive reference result

**Scope:** a new Python *reference* analysis for exact, scalar-input,
finite-width integer ReLU networks. It is mathematically motivated and
differentially tested. **No new Lean kernel theorem or production security
guarantee is claimed for this analyzer.** Aristotle is independently developing
the Lean formalization from the attached \`formal/\` tree.

## Definition

A model is

\[
  f(x) = c + \sum_{j=1}^{m} a_j\,\max(0,w_j x+b_j),
  \quad x\in\mathbb{Z},\quad
  a_j,w_j,b_j,c\in\mathbb Z.
\]

All arithmetic uses mathematical integers. There is no floating-point
approximation, fixed-width overflow, stochastic execution, optimizer state, or
unspecified hardware behavior in this model. Signed linear neurons are
representable because \(\max(0,z)-\max(0,-z)=z\).

## Lemma 1: finite integer breakpoints (mathematical justification)

For each nonconstant ReLU branch \(z(x)=wx+b\), define:

- If \(w>0\), \(k=\lfloor -b/w\rfloor\). Then \(z(x)>0\) exactly when \(x\ge k+1\).
- If \(w<0\), \(k=\lceil -b/w\rceil-1\). Then \(z(x)>0\) exactly when \(x\le k\).
- If \(w=0\), the branch is constant and contributes no breakpoint.

Consequently the branch is either \(0\) or \(wx+b\) on both
\((-\infty,k]\cap\mathbb Z\) and \([k+1,\infty)\cap\mathbb Z\). For any finite
collection of models, sort the union of all branch cuts, and divide
\(\mathbb Z\) into the corresponding disjoint contiguous cells. Each model
is affine, \(f(x)=sx+t\), **on every entire cell**, not merely at its
representative input.

## Lemma 2: universal equivalence

For two models \(f,g\), on each cell the difference is
\(d(x)=f(x)-g(x)=ax+b\). If a cell is a singleton \(\{q\}\), equality there
is equivalent to \(aq+b=0\). On any nonsingleton integer interval (finite
or infinite), equality at every point is equivalent to \(a=b=0\), because
an affine function with two distinct integer zeros must have both
coefficients zero.

Thus \(\forall x\in\mathbb Z,\;f(x)=g(x)\) reduces to finitely many exact
checks. On failure the checker constructs a genuine integer witness:
one singleton point or one of two distinct points in an interval.
There is no heuristic sampling in the algorithm.

## Lemma 3: universally preserved correct cases

Fix a mathematical target \(t\). To check

\[
\forall x\in\mathbb Z,\quad f_{\rm old}(x)=t(x)
\implies f_{\rm new}(x)=t(x),
\]

partition by the breakpoints of **all three** models. On each cell,
\(f_{\rm old}-t=ax+b\).

1. If \(a=b=0\), every integer in the cell was previously correct; require
   \(f_{\rm new}-t\) to be identically zero on that cell.
2. If \(a=0\) and \(b\ne0\), none was correct; the implication is vacuous.
3. If \(a\ne0\), the old model can be correct only at the single rational
   root \(x=-b/a\). If that root is an integer in the cell, check the new
   prediction at that exact integer; otherwise the implication is vacuous.

This again gives a finite exact algorithm and a constructive lost-correctness
witness on failure. Its running time depends on the number of branches
and cells, not the magnitude of the integer input domain.

## Lemma 4: exact maximum error over a bounded interval

On each bounded cell intersection \([L,R]\cap\mathbb Z\),
\(f-t=ax+b\), so \(|ax+b|\) is convex. The maximum over the interval
occurs at \(L\) or \(R\). Taking the maximum across the finitely many
cell endpoints computes \(\max_{x\in[L,R]\cap\mathbb Z}|f(x)-t(x)|\)
without scanning every integer.

The statement is for **specified bounded intervals**. An unbounded tail
with a nonzero error slope has unbounded absolute error. A finite window,
even an enormous one, cannot imply correct performance at every possible
integer input.

## Concrete falsification of the original Lean finite gate

Under the original target \(t(x)=\max(0,2x+1)\), the update

\[
f_{\rm old}(x)=\max(0,3x-3)
\quad\to\quad
f_{\rm new}(x)=\max(0,3x-1)
\]

is *accepted* by the prior verified seven-input benchmark acceptance rule.
Nevertheless \(f_{\rm old}(4)=t(4)=9\) and \(f_{\rm new}(4)=11\).
The new analytic reference checker finds exactly this \(x=4\) witness and
rejects the update under the stronger all-integer no-forgetting condition.
At \(x=20\) its absolute error also worsens.

The reference gate \`layered_guard.py\` combines: (a) unchanged fixed-corpus
admissibility, (b) analytic all-integer no-forgetting, (c) nonincreasing
worst-case error over a configurable integer window. It can optionally
request a **separate original Lean verdict** for (a). The Python check
for (b)-(c) is not thereby converted into a Lean theorem.

The original two-generation sequence
\`(ReLU,0,0)→(ReLU,1,1)→(ReLU,2,1)\` passes these stronger reference filters
for the default \([-20,20]\) window and attains universal target equality
in the last generation.

## Research implications

This is evidence that the distinction between *provably improving a finite
benchmark* and *preserving every previously correct input* can be made
algorithmically precise for **one-dimensional piecewise-affine architectures**.
It does not prove improved general intelligence or that a strictly improving
proposal always exists; a stronger guard can obstruct otherwise acceptable
progress. It is not a scalable approach to arbitrary high-dimensional neural
networks without additional structure or more powerful verification.

### Reproduction and threat boundary

\`\`\`bash
cd research/proof-gated-self-improvement-v1
python -m unittest discover -s tests -v
\`\`\`

Key sources: \`universal_relu.py\`, \`layered_guard.py\`,
\`tests/test_universal_relu.py\`, \`tests/test_layered_guard.py\`.

The Python reference tests include random differential enumeration, hidden
unit permutation and cancellation, distant exact roots, negative weights
and signed zero thresholds, exact interval worst-case comparisons, and
adversarial counterexamples. An implementation bug, unexpected interpreter
semantics, malicious source replacement, or insecure deployment can still
invalidate real-world enforcement. **Before integrating as trusted policy,
port the lemmas and validator to Lean, verify model loading/byte semantics,
and pin the authority outside the proposer's write privileges.**
