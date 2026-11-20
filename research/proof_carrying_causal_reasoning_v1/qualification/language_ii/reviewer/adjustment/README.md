# Independent four-node adjustment replay

A reviewer checked all 64 binary DAGs consistent with the order a, b, c, d. Each graph contributes twelve ordered exposure/outcome pairs and four covariate subsets drawn from the other two nodes. The checked criterion asks whether adjustment identifies the two interventional outcome probabilities for every compatible Markov population with sufficient support. Each numerical population uses independent disturbances and strictly positive binary conditional tables with denominator 101.

For each of the 3,072 graph, query and covariate-set combinations, direct world sums evaluate both intervention arms and both standardized risks under two fixed table draws. Every one of the 1,646 graphical accepts matched the intervention in each numerical comparison. For every one of the 1,426 graphical rejects, at least one arm of one concrete population gave a different fraction. The script fails if either property changes. The seeds plus graph index reproduce the complete tables and fractions. These finite tests supplement the general published identification criterion. They test the graphical implementation after interpretation.

From the repository root, run the following command using Python 3.12.

```sh
python -m research.proof_carrying_causal_reasoning_v1.qualification.language_ii.reviewer.adjustment.replay
```

[Recorded counts](results.json) · [Numerical enumeration](replay.py)
